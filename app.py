# app.py – Integrated Tk‑GUI version (no bridge needed) v1.2
"""
A terminal based AI agent that lets you interact with any device.
Changelog v1.2
---------------
* **Look & Feel**: Complete visual overhaul for an elegant, "riced" aesthetic.
* **Theme**: Implemented a cohesive, Dracula-inspired dark theme.
* **Fonts**: Prefers modern fonts like Fira Code and Consolas.
* **Design**: Flat, borderless widgets and improved spacing for a minimal look.
* **UX**: Replaced "Show Thinking" button with a subtle, clickable link.
* **UX**: Upgraded the loading spinner to use animated Braille characters.
* **Polish**: Themed all components, including menus and dialogs, for consistency.
* **Fix**: agent responses were `RunResponse` objects → convert to `str` before
  inserting into the Tk widget (prevented `TypeError`).
* Minor: safeguard in `_append` to coerce any non‑string to `str`.
"""
from __future__ import annotations

import os
import platform
import queue
import shlex
import subprocess
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


class Styles:
    """A collection of style constants for the GUI."""

    FONT_FAMILY = ("Fira Code", "Consolas", "Courier New")
    FONT_SIZE_NORMAL = 11
    FONT_SIZE_SMALL = 10
    FONT_NORMAL = (FONT_FAMILY, FONT_SIZE_NORMAL)
    FONT_BOLD = (FONT_FAMILY, FONT_SIZE_NORMAL, "bold")
    FONT_SMALL_LINK = (FONT_FAMILY, FONT_SIZE_SMALL, "underline")

    # Dracula-inspired theme
    COLOR_BACKGROUND = "#282a36"
    COLOR_FOREGROUND = "#f8f8f2"
    COLOR_COMMENT = "#6272a4"
    COLOR_CYAN = "#8be9fd"
    COLOR_GREEN = "#50fa7b"
    COLOR_PINK = "#ff79c6"
    COLOR_PURPLE = "#bd93f9"
    COLOR_RED = "#ff5555"
    COLOR_SELECTION = "#44475a"


class NeuralTerminalGUI:
    """Tkinter wrapper for the Agent with a refined look and feel."""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.root = tk.Tk()
        self.root.title("AIOS Neural Terminal 🌟")
        self.root.geometry("1000x700")
        self.root.configure(bg=Styles.COLOR_BACKGROUND)

        # Main text area
        self.text = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            font=Styles.FONT_NORMAL,
            bg=Styles.COLOR_BACKGROUND,
            fg=Styles.COLOR_FOREGROUND,
            selectbackground=Styles.COLOR_SELECTION,
            selectforeground=Styles.COLOR_FOREGROUND,
            insertbackground=Styles.COLOR_FOREGROUND,  # Cursor color
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        self.text.pack(fill=tk.BOTH, expand=True)
        self.text.configure(state=tk.DISABLED)

        # Bottom input frame
        bottom = tk.Frame(self.root, bg=Styles.COLOR_BACKGROUND)
        bottom.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Input prompt symbol
        tk.Label(
            bottom, text="▶", font=Styles.FONT_BOLD, fg=Styles.COLOR_PINK, bg=Styles.COLOR_BACKGROUND
        ).pack(side=tk.LEFT, padx=(0, 5))

        # Input entry field
        self.entry = tk.Entry(
            bottom,
            font=Styles.FONT_NORMAL,
            bg=Styles.COLOR_BACKGROUND,
            fg=Styles.COLOR_FOREGROUND,
            insertbackground=Styles.COLOR_FOREGROUND,
            relief=tk.FLAT,
            highlightthickness=0,
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.focus()

        self._setup_menubar()
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
        self._spinner_frames = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
        self._spinner_job = None
        self._spinner_index = 0
        self._spinner_mark = None

    def _setup_menubar(self):
        menubar = tk.Menu(
            self.root,
            bg=Styles.COLOR_BACKGROUND,
            fg=Styles.COLOR_FOREGROUND,
            activebackground=Styles.COLOR_SELECTION,
            activeforeground=Styles.COLOR_FOREGROUND,
            relief=tk.FLAT,
            borderwidth=0,
        )
        self.root.config(menu=menubar)

        # File Menu
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Export Session", command=self._export)
        filemenu.add_separator(background=Styles.COLOR_SELECTION)
        filemenu.add_command(label="Quit", command=self.root.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=filemenu)

        # Edit Menu
        editmenu = tk.Menu(menubar, tearoff=0)
        editmenu.add_command(label="Preferences…", command=self._prefs_dialog)
        menubar.add_cascade(label="Edit", menu=editmenu)

        # Apply styles to submenus
        for menu in (filemenu, editmenu):
            menu.config(
                bg=Styles.COLOR_BACKGROUND,
                fg=Styles.COLOR_FOREGROUND,
                activebackground=Styles.COLOR_SELECTION,
                activeforeground=Styles.COLOR_PINK,  # Highlight selection
                relief=tk.FLAT,
            )

    # ───────────────────────── Internal helpers ───────────────────────── #

    def _banner(self):
        info = (
            f"Provider: {config.agent.provider.title()}  |  Model: {config.agent.model}\n"
            f"System: {platform.system()} {platform.release()}\n"
            f"Session start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "Type 'help' for commands or '$' to run shell commands (e.g., $ ls -l)."
        )
        self._append(info, tag="info")

    def _append(self, text: Any, tag: str | None = None):
        if not isinstance(text, str):
            text = str(text)
        self.text.configure(state=tk.NORMAL)
        if tag:
            tag_colors = {
                "user": Styles.COLOR_PINK,
                "error": Styles.COLOR_RED,
                "info": Styles.COLOR_COMMENT,
                "spin": Styles.COLOR_PURPLE,
                "shell_out": Styles.COLOR_GREEN,
                "agent_response": Styles.COLOR_FOREGROUND,
            }
            self.text.tag_configure(tag, foreground=tag_colors.get(tag, Styles.COLOR_FOREGROUND))
        self.text.insert(tk.END, text + "\n", tag)
        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)

    def _on_enter(self, _ev=None):
        prompt = self.entry.get().strip()
        if not prompt:
            return
        self.entry.delete(0, tk.END)
        if prompt.startswith("$"):  # ← shell mode
            cmd = prompt[1:].strip()
            self._append(f"$ {cmd}", tag="user")
            self._start_spinner("executing")
            threading.Thread(target=self._shell_task, args=(cmd,), daemon=True).start()
        else:  # ← AI mode
            self._append(f"▶ {prompt}", tag="user")
            self._start_spinner("thinking")
            threading.Thread(target=self._agent_task, args=(prompt,), daemon=True).start()
        return "break"

    # ───────────────────────── Background Tasks ───────────────────── #

    def _run_shell(self, cmd: str) -> tuple[str, str, int]:
        try:
            proc = subprocess.Popen(
                shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            out, err = proc.communicate()
            return out, err, proc.returncode
        except FileNotFoundError:
            return "", f"Command not found: {cmd.split()[0]}", 127
        except Exception as e:
            return "", str(e), 1

    def _shell_task(self, cmd: str):
        out, err, code = self._run_shell(cmd)
        if out:
            self.queue.put({"shell_out": out})
        if err:
            self.queue.put({"shell_err": err})
        elif code != 0 and not out:
            self.queue.put({"shell_err": f"Command exited with code {code}"})

    def _agent_task(self, prompt: str):
        """Run the agent and enqueue a payload with the final answer and intermediate steps."""
        if self.agent is None:
            self.queue.put({"error": "Agent not initialised — add an API key in Preferences."})
            return

        try:
            resp = self.agent.run(
                prompt, show_full_reasoning=True, show_tool_calls=True
            )

            calls = []
            for msg in resp.messages or []:
                if getattr(msg, "tool_calls", None):
                    for tc in msg.tool_calls:
                        calls.append(
                            {
                                "tool_name": tc["function"]["name"],
                                "tool_args": tc["function"]["arguments"],
                                "tool_output": None,  # filled in next
                            }
                        )
                elif msg.role == "tool" and calls and calls[-1]["tool_output"] is None:
                    calls[-1]["tool_output"] = msg.content.strip()

            self.queue.put(
                {
                    "content": str(resp.content).strip(),  # Ensure content is string
                    "reasoning": (resp.reasoning_content or "").strip(),
                    "calls": calls,
                }
            )
        except Exception as e:
            self.queue.put({"error": f"An unexpected error occurred: {e}"})

    # ───────────────────────── Spinner helpers ────────────────────── #
    def _start_spinner(self, label: str = "thinking"):
        if self._spinner_job:
            return

        self.text.configure(state=tk.NORMAL)
        # Add a newline if text area isn't empty, for spacing
        if self.text.get("1.0", tk.END).strip():
            self.text.insert(tk.END, "\n")
        self._spinner_mark = self.text.index(f"{tk.END}-2c")  # remember position
        self.text.insert(tk.END, f"{self._spinner_frames[0]} {label}...\n", "spin")
        self.text.tag_configure("spin", foreground=Styles.COLOR_PURPLE)
        self.text.configure(state=tk.DISABLED)
        self._spinner_job = self.root.after(100, self._spin_tick)

    def _spin_tick(self):
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_frames)
        frame = self._spinner_frames[self._spinner_index]
        self.text.configure(state=tk.NORMAL)
        self.text.delete(self._spinner_mark, f"{self._spinner_mark}+1c")
        self.text.insert(self._spinner_mark, frame, "spin")
        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)
        self._spinner_job = self.root.after(100, self._spin_tick)

    def _stop_spinner(self):
        if self._spinner_job:
            self.root.after_cancel(self._spinner_job)
            self._spinner_job = None
            self.text.configure(state=tk.NORMAL)
            # Find the start of the spinner line and delete the whole line
            start_of_line = self.text.search(self._spinner_frames[0], self._spinner_mark, backwards=True)
            if start_of_line:
                self.text.delete(f"{start_of_line} linestart", f"{start_of_line} lineend+1c")
            self.text.configure(state=tk.DISABLED)

    # ───────────────────────── UI Event Handlers ────────────────────── #

    def _show_thinking(self, data: dict):
        """Pop-up window displaying reasoning + tool calls."""
        top = tk.Toplevel(self.root)
        top.title("AI Thinking")
        top.geometry("700x500")
        top.configure(bg=Styles.COLOR_BACKGROUND)

        txt = scrolledtext.ScrolledText(
            top,
            wrap=tk.WORD,
            font=Styles.FONT_NORMAL,
            bg=Styles.COLOR_BACKGROUND,
            fg=Styles.COLOR_FOREGROUND,
            selectbackground=Styles.COLOR_SELECTION,
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        txt.pack(fill=tk.BOTH, expand=True)
        txt.configure(state=tk.NORMAL)

        # Chain-of-thought
        if data["reasoning"]:
            txt.insert(tk.END, "🧠 Reasoning\n", "header")
            txt.insert(tk.END, data["reasoning"].strip() + "\n\n")

        # Tool calls with syntax highlighting
        if data["calls"]:
            txt.insert(tk.END, "🔧 Tool Calls\n", "header")
            for i, call in enumerate(data["calls"], 1):
                txt.insert(tk.END, f"{i}. ", "info")
                txt.insert(tk.END, f"{call['tool_name']}", "tool_name")
                txt.insert(tk.END, f"({call['tool_args']})", "foreground")
                if call["tool_output"]:
                    output_short = (call["tool_output"][:100] + '...') if len(call["tool_output"]) > 100 else call["tool_output"]
                    txt.insert(tk.END, f" → {output_short}", "tool_output")
                txt.insert(tk.END, "\n")

        if not data["reasoning"] and not data["calls"]:
            txt.insert(tk.END, "(The model did not expose any intermediate steps.)", "info")

        # Configure styles
        txt.tag_configure("header", font=Styles.FONT_BOLD, foreground=Styles.COLOR_PURPLE)
        txt.tag_configure("tool_name", foreground=Styles.COLOR_GREEN)
        txt.tag_configure("tool_output", foreground=Styles.COLOR_COMMENT)
        txt.tag_configure("info", foreground=Styles.COLOR_COMMENT)
        txt.tag_configure("foreground", foreground=Styles.COLOR_FOREGROUND)
        txt.configure(state=tk.DISABLED)

    def _poll_queue(self):
        try:
            while True:
                item = self.queue.get_nowait()
                self._stop_spinner()

                if "error" in item:
                    self._append(f"Error: {item['error']}", tag="error")
                elif "shell_out" in item:
                    self._append(item["shell_out"].rstrip(), tag="shell_out")
                elif "shell_err" in item:
                    self._append(item["shell_err"].rstrip(), tag="error")
                elif "content" in item:
                    self._append(item["content"], tag="agent_response")
                    self.text.configure(state=tk.NORMAL)

                    # Create a clickable label instead of a button
                    link = tk.Label(
                        self.text,
                        text="Show Thinking",
                        font=Styles.FONT_SMALL_LINK,
                        fg=Styles.COLOR_PURPLE,
                        bg=Styles.COLOR_BACKGROUND,
                        cursor="hand2",
                    )
                    link.bind("<Button-1>", lambda e, data=item: self._show_thinking(data))
                    link.bind("<Enter>", lambda e: e.widget.config(fg=Styles.COLOR_PINK))
                    link.bind("<Leave>", lambda e: e.widget.config(fg=Styles.COLOR_PURPLE))

                    self.text.insert(tk.END, "  ")
                    self.text.window_create(tk.END, window=link)
                    self.text.insert(tk.END, "\n\n")  # More space after response
                    self.text.configure(state=tk.DISABLED)
                else:
                    self._append(str(item))  # Fallback

                self.queue.task_done()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_queue)

    def _prefs_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Preferences")
        win.transient(self.root)
        win.grab_set()
        win.configure(bg=Styles.COLOR_BACKGROUND, padx=20, pady=15)
        win.resizable(False, False)

        # --- Styles for widgets ---
        label_style = {"bg": Styles.COLOR_BACKGROUND, "fg": Styles.COLOR_FOREGROUND, "font": Styles.FONT_NORMAL}
        entry_style = {
            "bg": Styles.COLOR_SELECTION, "fg": Styles.COLOR_FOREGROUND, "font": Styles.FONT_NORMAL,
            "relief": tk.FLAT, "highlightthickness": 0, "insertbackground": Styles.COLOR_FOREGROUND,
        }

        # --- Provider ---
        tk.Label(win, text="Provider", **label_style).grid(row=0, column=0, sticky="w", pady=(0, 5))
        provider_var = tk.StringVar(value=config.agent.provider)
        provider_menu = tk.OptionMenu(win, provider_var, "openai", "google", "openrouter", "together")
        provider_menu.config(
            bg=Styles.COLOR_SELECTION, fg=Styles.COLOR_FOREGROUND, activebackground=Styles.COLOR_SELECTION,
            activeforeground=Styles.COLOR_FOREGROUND, relief=tk.FLAT, highlightthickness=0, width=25,
            direction="below", borderwidth=0,
        )
        provider_menu["menu"].config(
            bg=Styles.COLOR_BACKGROUND, fg=Styles.COLOR_FOREGROUND,
            activebackground=Styles.COLOR_SELECTION, activeforeground=Styles.COLOR_PINK, relief=tk.FLAT,
        )
        provider_menu.grid(row=0, column=1, sticky="ew", pady=(0, 10))

        # --- Model ---
        tk.Label(win, text="Model", **label_style).grid(row=1, column=0, sticky="w", pady=(0, 5))
        model_var = tk.StringVar(value=config.agent.model)
        tk.Entry(win, textvariable=model_var, width=30, **entry_style).grid(row=1, column=1, pady=(0, 10))

        # --- API Key ---
        tk.Label(win, text="API Key", **label_style).grid(row=2, column=0, sticky="w", pady=(0, 5))
        key_var = tk.StringVar()
        tk.Entry(win, textvariable=key_var, show="•", width=30, **entry_style).grid(row=2, column=1, pady=(0, 15))

        def _save():
            cfg = config
            cfg.agent.provider = provider_var.get()
            cfg.agent.model = model_var.get()
            key = key_var.get().strip()
            if key:
                setattr(cfg.agent, f"{provider_var.get()}_api_key", key)
            self.agent = build_agent(cfg)  # hot-swap
            self._append("\n— Preferences updated & agent restarted —\n", tag="info")
            win.destroy()

        # --- Save Button ---
        save_button = tk.Button(
            win, text="Save & Restart Agent", command=_save, relief=tk.FLAT,
            bg=Styles.COLOR_PURPLE, fg=Styles.COLOR_FOREGROUND,
            activebackground=Styles.COLOR_PINK, activeforeground=Styles.COLOR_FOREGROUND,
            font=Styles.FONT_NORMAL, padx=10, pady=5, borderwidth=0,
        )
        save_button.grid(row=3, column=0, columnspan=2, pady=8)
        win.columnconfigure(1, weight=1)

    def _export(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", tk.END))
            messagebox.showinfo("Export Successful", f"Session saved to {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not save file:\n{e}")

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
        messagebox.showerror("Configuration Error", msg)
        sys.exit(1)

    model_map = {
        "openai": (OpenAIChat, cfg.agent.openai_api_key or os.getenv("OPENAI_API_KEY")),
        "google": (Gemini, cfg.agent.google_api_key or os.getenv("GOOGLE_API_KEY")),
        "openrouter": (OpenRouter, getattr(cfg.agent, "openrouter_api_key", None) or os.getenv("OPENROUTER_API_KEY")),
        "together": (Together, getattr(cfg.agent, "together_api_key", None) or os.getenv("TOGETHER_API_KEY")),
    }

    if provider not in model_map:
        missing(f"Unknown provider: {provider}")

    model_class, key = model_map[provider]
    if not key:
        return missing(f"{provider.title()} API key missing.")

    model_kwargs = {"id": model_id, "api_key": key, "temperature": temp}
    if provider in ("openai", "openrouter", "together"):
        model_kwargs["max_tokens"] = max_tok

    model = model_class(**model_kwargs)

    return Agent(
        model=model,
        tools=[ReasoningTools(add_instructions=True), ShellTools(), FileTools(), PythonTools()],
        instructions=dedent(
            f"""
            You are a System‑Intelligence Assistant running inside a GUI terminal.
            System: {platform.system()} {platform.release()} | Provider: {provider} | Model: {model_id}
            - Be concise, helpful, and use markdown for formatting.
            - You can execute shell commands. For risky commands (e.g., rm, sudo), always ask for confirmation first.
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

    # allow_missing_key=True so the app can boot to show the preferences dialog
    agent = build_agent(config, allow_missing_key=True)
    NeuralTerminalGUI(agent).run()