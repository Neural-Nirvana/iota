# app.py – Integrated Tk‑GUI version (no bridge needed) v1.1
"""
A terminal based AI agent that lets you interact with any device.
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
from tkinter import filedialog, messagebox, scrolledtext, simpledialog

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
        self.root.title("AIOS Neural Terminal🌟")
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
        #------------------- File Menu --------------------------------#
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Export Session", command=self._export)
        filemenu.add_separator()
        filemenu.add_command(label="Quit", command=self.root.quit, accelerator="Ctrl+Q")

        #------------------- Edit Menu --------------------------------#
        menubar.add_cascade(label="File", menu=filemenu)
        editmenu = tk.Menu(menubar, tearoff=0)
        editmenu.add_command(label="Preferences…", command=self._prefs_dialog)
        menubar.add_cascade(label="Edit", menu=editmenu)
        
        self.root.config(menu=menubar)


        self.root.bind("<Control-q>", lambda _e: self.root.quit())

        self.queue: queue.Queue[str] = queue.Queue()
        self.root.after(100, self._poll_queue)

        self._banner()
        if self.agent is None:
            self._append(
                "⚠ No API key configured. Open **Edit ▸ Preferences…** to set your "
                "provider, model and key, then click *Save & Restart Agent*.",
                tag="error",
            )
            # pop the dialog automatically on first launch
            self.root.after(100, self._prefs_dialog)

        # spinner state
        self._spinner_frames = ["|","/","-","\\"]  # braille dots
        self._spinner_job = None          # after() id
        self._spinner_index = 0
        self._spinner_mark = None         # text index where we drew it


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
        if prompt.startswith("$"):                     # ← shell mode
            cmd = prompt[1:].strip()
            self._append(f"$ {cmd}", tag="user")
            self._start_spinner("executing")
            threading.Thread(target=self._shell_task, args=(cmd,), daemon=True).start()
        else:                                          # ← AI mode
            self._append(f"▶ {prompt}", tag="user")
            self._start_spinner("thinking")
            threading.Thread(target=self._agent_task, args=(prompt,), daemon=True).start()
        return "break"

    # ───────────────────────── Shell helpers ───────────────────── #
    import subprocess, shlex

    def _run_shell(self, cmd: str):
        proc = self.subprocess.Popen(
            self.shlex.split(cmd),
            stdout=self.subprocess.PIPE,
            stderr=self.subprocess.PIPE,
            text=True,
        )
        out, err = proc.communicate()
        return out, err, proc.returncode

    def _shell_task(self, cmd: str):
        out, err, code = self._run_shell(cmd)
        if out:
            self.queue.put({"shell_out": out})
        if err or code:
            self.queue.put({"shell_err": err or f"exit {code}"})

    def _agent_task(self, prompt: str):
        """
        Run the agent and enqueue a payload that contains:
            • final answer
            • chain-of-thought (reasoning_content)
            • human-readable list of tool calls
        Works on Agno ≥1.3 and needs no version branching.
        """
        if self.agent is None:
            self.queue.put({"error": "Agent not initialised — add an API key in Preferences."})
            return

        try:
            resp = self.agent.run(
                prompt,
                show_full_reasoning=True,      # exposes .reasoning_content
                show_tool_calls=True,          # puts tool_calls inside messages
            )

            # ---------- collect tool calls ----------
            calls = []
            last_call = None

            # -------- _agent_task ----------
            for msg in resp.messages or []:
                if getattr(msg, "tool_calls", None):
                    for tc in msg.tool_calls:
                        calls.append({
                            "tool_name"   : tc["function"]["name"],
                            "tool_args"   : tc["function"]["arguments"],
                            "tool_output" : None,          # filled in later
                        })
                elif msg.role == "tool" and calls:
                    calls[-1]["tool_output"] = msg.content.strip()

            self.queue.put({
                "content"   : resp.content.strip(),
                "reasoning" : (resp.reasoning_content or "").strip(),
                "calls"     : calls,
            })

            # ---------- ship to the GUI ----------
            # self.queue.put({
            #     "content": resp.content.strip(),
            #     "reasoning": (resp.reasoning_content or "").strip(),
            #     "calls": calls,                       # list[str]
            # })

        except Exception as e:
            self.queue.put({"error": str(e)})

    # ───────────────────────── Spinner helpers ────────────────────── #
    def _start_spinner(self, label: str = "thinking"):
        """Insert an animated one-liner like  ⠋ thinking... and update it."""
        if self._spinner_job:          # already running
            return

        self.text.configure(state=tk.NORMAL)
        self._spinner_mark = self.text.index(tk.END)      # remember position
        self.text.insert(tk.END, f"{self._spinner_frames[0]} {label}...\n", "spin")
        self.text.tag_configure("spin", foreground="#bd93f9")
        self.text.configure(state=tk.DISABLED)
        self._spinner_job = self.root.after(100, self._spin_tick)

    def _spin_tick(self):
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_frames)
        frame = self._spinner_frames[self._spinner_index]

        self.text.configure(state=tk.NORMAL)
        # overwrite only the spinner glyph
        self.text.delete(self._spinner_mark, f"{self._spinner_mark}+1c")
        self.text.insert(self._spinner_mark, frame, "spin")
        self.text.see(tk.END)  
        self.text.configure(state=tk.DISABLED)

        self._spinner_job = self.root.after(100, self._spin_tick)
        print("tick", self._spinner_frames[self._spinner_index])

    def _stop_spinner(self):
        if self._spinner_job:
            self.root.after_cancel(self._spinner_job)
            self._spinner_job = None
            # remove the line entirely
            self.text.configure(state=tk.NORMAL)
            self.text.delete(self._spinner_mark, f"{self._spinner_mark} lineend")
            self.text.configure(state=tk.DISABLED)

    def _show_thinking(self, data: dict):
        """Pop-up window displaying reasoning + tool calls."""
        top = tk.Toplevel(self.root)
        top.title("AI Thinking")
        top.geometry("700x500")

        txt = scrolledtext.ScrolledText(top, wrap=tk.WORD, font=("Courier New", 11))
        txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        txt.configure(state=tk.NORMAL)

        # Chain-of-thought
        if data["reasoning"]:
            txt.insert(tk.END, "🧠 Reasoning steps\n", "header")
            txt.insert(tk.END, data["reasoning"].strip() + "\n\n")

        # Tool calls
        if data["calls"]:
            txt.insert(tk.END, "🔧 Tool calls\n", "header")
            for i, call in enumerate(data["calls"], 1):
                line = f"{i}. {call['tool_name']}({call['tool_args']})"
                if call["tool_output"]:
                    line += f" → {call['tool_output']}"
                txt.insert(tk.END, line + "\n")


        if not data["reasoning"] and not data["calls"]:
            txt.insert(tk.END, "(The model did not expose any intermediate steps.)")

        # simple styling
        txt.tag_configure("header", font=("Courier New", 11, "bold"), foreground="#bd93f9")
        txt.configure(state=tk.DISABLED)


    def _poll_queue(self):
        try:
            if self._spinner_job:
                self._stop_spinner()

            while True:
                item = self.queue.get_nowait()

                if "error" in item:
                    self._append(item["error"], tag="error")

                elif "shell_out" in item:
                    self._append(item["shell_out"].rstrip(), tag="info")

                elif "shell_err" in item:
                    self._append(item["shell_err"].rstrip(), tag="error")

                elif "content" in item:                     # ← real answers only
                    self._append(item["content"])
                    self.text.configure(state=tk.NORMAL)
                    btn = tk.Button(
                        self.text, text="▶ Show Thinking", relief=tk.FLAT,
                        cursor="hand2", font=("Courier New", 10, "underline"),
                        fg="#032133",
                        command=lambda data=item: self._show_thinking(data)
                    )
                    self.text.window_create(tk.END, window=btn)
                    self.text.insert(tk.END, "\n")
                    self.text.configure(state=tk.DISABLED)

                else:
                    self._append(str(item))

                self.queue.task_done()      # ensures the item is gone
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)



    # ───────────────────────── Preferences dialog ──────────────── #
    def _prefs_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Preferences")
        win.transient(self.root)
        win.grab_set()

        # provider
        tk.Label(win, text="Provider").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        provider_var = tk.StringVar(value=config.agent.provider)
        tk.OptionMenu(win, provider_var, "openai", "google", "openrouter", "together").grid(
            row=0, column=1, sticky="ew", padx=4, pady=4
        )

        # model
        tk.Label(win, text="Model").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        model_var = tk.StringVar(value=config.agent.model)
        tk.Entry(win, textvariable=model_var, width=24).grid(row=1, column=1, padx=4, pady=4)

        # api key
        tk.Label(win, text="API Key").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        key_var = tk.StringVar()
        tk.Entry(win, textvariable=key_var, show="•", width=30).grid(row=2, column=1, padx=4, pady=4)
        def _save():
            cfg = config
            cfg.agent.provider = provider_var.get()
            cfg.agent.model = model_var.get()
            key = key_var.get().strip()
            if key:
                setattr(cfg.agent, f"{provider_var.get()}_api_key", key)
            self.agent = build_agent(cfg)        # hot-swap
            self._append("\n— Preferences updated —\n", tag="info")
            win.destroy()

        tk.Button(win, text="Save & Restart Agent", command=_save).grid(
            row=3, column=0, columnspan=2, pady=8
        )
        win.columnconfigure(1, weight=1)

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

def build_agent(cfg, allow_missing_key: bool = False) -> Agent | None:
    provider = cfg.agent.provider.lower()
    model_id = cfg.agent.model
    temp = cfg.agent.temperature
    max_tok = cfg.agent.max_tokens

    def missing(msg: str):
        if allow_missing_key:
            return None
        messagebox.showerror("AI‑OS", msg)
        sys.exit(1)

    if provider == "openai":
        key = cfg.agent.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            return missing("OpenAI API key missing.")
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
            Run rhe shell commands yourself if they are not harmful.
            Confirm harmful shell commands along with their consequences if executed before running commands.
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

    # allow_missing_key=True so the app boots without secrets
    agent = build_agent(config, allow_missing_key=True)
    NeuralTerminalGUI(agent).run()
