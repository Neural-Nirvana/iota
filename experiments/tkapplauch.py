# app.py – Integrated Tk‑GUI version (no bridge needed) v1.1
"""
A single‑file GUI terminal for your AGNO Agent.
Changelog v1.1
---------------
* **Fix**: agent responses were `RunResponse` objects → convert to `str` before
  inserting into the Tk widget (prevented `TypeError`).
* Minor: safeguard in `_append` to coerce any non‑string to `str`.
"""
from __future__ import annotations

import os
import platform
import queue
import sys
import threading
from datetime import datetime
from textwrap import dedent
from typing import Any

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.openai import OpenAIChat
from agno.models.openrouter import OpenRouter
from agno.models.together import Together
from agno.storage.sqlite import SqliteStorage
from agno.tools.file import FileTools
from agno.tools.python import PythonTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.shell import ShellTools
from agno.utils.log import logger

try:
    from config import load_config
except ImportError:
    print("config.py missing – create one with create_default_config() first.")
    sys.exit(1)


class NeuralTerminalGUI:
    """Tkinter wrapper for the Agent."""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.root = tk.Tk()
        self.root.title("🌟 AI‑OS Neural Terminal")
        self.root.geometry("1000x700")

        self.text = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, font=("Courier New", 11))
        self.text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))
        self.text.configure(state=tk.DISABLED)

        bottom = tk.Frame(self.root)
        bottom.pack(fill=tk.X, padx=8, pady=(4, 8))
        tk.Label(bottom, text="▶", font=("Courier New", 12, "bold")).pack(side=tk.LEFT)
        self.entry = tk.Entry(bottom, font=("Courier New", 11))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.focus()

        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Export Session", command=self._export)
        filemenu.add_separator()
        filemenu.add_command(label="Quit", command=self.root.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)
        self.root.bind("<Control-q>", lambda _e: self.root.quit())

        self.queue: queue.Queue[str] = queue.Queue()
        self.root.after(100, self._poll_queue)

        self._banner()

    # ───────────────────────── Internal helpers ───────────────────────── #

    def _banner(self):
        info = (
            f"Provider: {config.agent.provider.title()}  |  Model: {config.agent.model}\n"
            f"System: {platform.system()} {platform.release()}\n"
            f"Session start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "Type help for commands."
        )
        self._append(info, tag="info")

    def _append(self, text: Any, tag: str | None = None):
        if not isinstance(text, str):
            text = str(text)
        self.text.configure(state=tk.NORMAL)
        if tag:
            self.text.tag_configure(
                tag,
                foreground={"user": "#ff79c6", "error": "#ff5555", "info": "#8be9fd"}.get(tag, "#f8f8f2"),
            )
        self.text.insert(tk.END, text + "\n", tag)
        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)

    def _on_enter(self, _ev=None):
        prompt = self.entry.get().strip()
        if not prompt:
            return
        self.entry.delete(0, tk.END)
        self._append(f"▶ {prompt}", tag="user")
        threading.Thread(target=self._agent_task, args=(prompt,), daemon=True).start()

    def _agent_task(self, prompt: str):
        """Run the agent in a thread and enqueue **clean** content only."""
        try:
            reply = self.agent.run(prompt)
            # AGNO returns a RunResponse – we only want the user‑facing text.
            if hasattr(reply, "content") and isinstance(reply.content, str):
                clean = reply.content.strip()
            else:
                clean = str(reply).strip()
            self.queue.put(clean)
        except Exception as e:
            logger.error("Agent error", exc_info=True)
            self.queue.put(f"Error: {e}")

    def _poll_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                self._append(msg)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _export(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.text.get("1.0", tk.END))
        messagebox.showinfo("Export", f"Session saved to {path}")

    def run(self):
        self.root.mainloop()


# ───────────────────────── Agent factory ─────────────────────────── #

def build_agent(cfg) -> Agent:
    provider = cfg.agent.provider.lower()
    model_id = cfg.agent.model
    temp = cfg.agent.temperature
    max_tok = cfg.agent.max_tokens

    def missing(msg: str):
        messagebox.showerror("AI‑OS", msg)
        sys.exit(1)

    if provider == "openai":
        key = cfg.agent.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            missing("OpenAI API key missing.")
        model = OpenAIChat(id=model_id, api_key=key, temperature=temp, max_tokens=max_tok)
    elif provider == "google":
        key = cfg.agent.google_api_key or os.getenv("GOOGLE_API_KEY")
        if not key:
            missing("Google API key missing.")
        model = Gemini(id=model_id, api_key=key, temperature=temp)
    elif provider == "openrouter":
        key = getattr(cfg.agent, "openrouter_api_key", None) or os.getenv("OPENROUTER_API_KEY")
        if not key:
            missing("OpenRouter API key missing.")
        model = OpenRouter(id=model_id, api_key=key, temperature=temp, max_tokens=max_tok)
    elif provider == "together":
        key = getattr(cfg.agent, "together_api_key", None) or os.getenv("TOGETHER_API_KEY")
        if not key:
            missing("Together AI API key missing.")
        model = Together(id=model_id, api_key=key, temperature=temp, max_tokens=max_tok)
    else:
        missing(f"Unknown provider: {provider}")

    return Agent(
        model=model,
        tools=[ReasoningTools(add_instructions=True), ShellTools(), FileTools(), PythonTools()],
        instructions=dedent(
            f"""
            You are a System‑Intelligence Assistant running inside a GUI terminal.
            System: {platform.system()} {platform.release()}
            Provider: {provider} | Model: {model_id}
            Be concise, helpful, and warn before dangerous commands.
            """
        ),
        add_datetime_to_instructions=True,
        stream_intermediate_steps=True,
        show_tool_calls=True,
        markdown=True,
        storage=SqliteStorage(table_name="gui_sessions", db_file=cfg.storage.db_file),
        add_history_to_messages=True,
        num_history_runs=3,
    )


if __name__ == "__main__":
    config = load_config()
    os.makedirs("logs", exist_ok=True)
    os.makedirs("exports", exist_ok=True)

    agent = build_agent(config)
    NeuralTerminalGUI(agent).run()