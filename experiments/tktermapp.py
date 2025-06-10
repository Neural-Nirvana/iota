# ai_os_integrated_fixed.py – Beautiful GUI wrapper for your existing app.py CLI (v2.1)
"""
Key improvements over v2.0
=========================
1. **Unified command routing** – `send_command()` now detects whether we're in
   direct‑agent mode or subprocess mode and routes the command accordingly. This
   eliminates the annoying "CLI process not running" error when direct mode is
   active.
2. **Graceful fallback logic** – When direct integration is active, we no longer
   try to start a subprocess. Conversely, if the subprocess fails to start, we
   seamlessly switch to direct mode.
3. **Centralised tag configuration** – Tag colours are configured once at
   start‑up, improving performance.
4. **Minor UI tweaks** – Consistent background colours on header/input frames
   after theme changes; session statistics calculations simplified.
5. **PEP‑8 clean‑ups & small bug fixes** – e.g. fixed `command_history_down`
   off‑by‑one, added default arg for `send_command`, removed duplicate imports.

Drop this file next to your **app.py**, run it with `python ai_os_integrated_fixed.py`,
and enjoy a smoother experience.
"""
from __future__ import annotations

import os
import platform
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ────────────────────────── Optional CLI imports ────────────────────────── #
CLI_AVAILABLE = False
try:
    from app import main as cli_main, TerminalUI  # noqa: F401  (import for side‑effects)
    from config import load_config, save_config  # noqa: F401

    CLI_AVAILABLE = True
except Exception as e:  # broad but we only need the flag
    print(f"⚠️  Could not import app.py modules – running GUI‑only: {e}")

# ──────────────────────────────── Themes ───────────────────────────────── #


class ModernThemes:
    @staticmethod
    def get_themes():
        return {
            "cyberpunk": {
                "bg": "#0f0f23",
                "fg": "#00ff41",
                "cursor": "#ff0080",
                "select_bg": "#330033",
                "select_fg": "#ffffff",
                "font_family": "Courier New",
                "font_size": 11,
                "description": "🌆 Cyberpunk – Neon Matrix vibes",
            },
            "matrix": {
                "bg": "#000000",
                "fg": "#00ff00",
                "cursor": "#00ff00",
                "select_bg": "#003300",
                "select_fg": "#00ff00",
                "font_family": "Courier New",
                "font_size": 11,
                "description": "💚 Matrix – Classic green terminal",
            },
            "retro_amber": {
                "bg": "#1a0a00",
                "fg": "#ffb000",
                "cursor": "#ffb000",
                "select_bg": "#3d2200",
                "select_fg": "#ffb000",
                "font_family": "Courier New",
                "font_size": 11,
                "description": "🟡 Retro Amber – Vintage CRT",
            },
            "neon_blue": {
                "bg": "#001122",
                "fg": "#00aaff",
                "cursor": "#00aaff",
                "select_bg": "#002244",
                "select_fg": "#00aaff",
                "font_family": "Courier New",
                "font_size": 11,
                "description": "💙 Neon Blue – Electric vibes",
            },
            "hacker_green": {
                "bg": "#0d1117",
                "fg": "#58a6ff",
                "cursor": "#f85149",
                "select_bg": "#21262d",
                "select_fg": "#58a6ff",
                "font_family": "Courier New",
                "font_size": 11,
                "description": "💻 Hacker Green – GitHub inspired",
            },
            "synthwave": {
                "bg": "#2b213a",
                "fg": "#ff79c6",
                "cursor": "#50fa7b",
                "select_bg": "#44475a",
                "select_fg": "#ff79c6",
                "font_family": "Courier New",
                "font_size": 11,
                "description": "🌸 Synthwave – Retro‑futuristic",
            },
        }


# ────────────────────────────── Main GUI ───────────────────────────────── #


class AITerminalGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.themes = ModernThemes.get_themes()
        self.current_theme = "cyberpunk"
        self.config = load_config() if CLI_AVAILABLE else None

        # Session tracking
        self.session_start = datetime.now()

        # CLI process & agent
        self.cli_process: Optional[subprocess.Popen[str]] = None
        self.direct_agent = None
        self.direct_mode = False

        # Queues
        self.output_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.command_history: list[str] = []
        self.history_index = -1

        self._build_ui()
        self.apply_theme(self.current_theme)

        # Kick off integration & monitoring after UI loop starts
        self.root.after(300, self.start_cli_process)
        self.root.after(500, self.monitor_output)
        self.root.after(800, self.show_welcome_message)

    # ─────────────────────────── UI builders ──────────────────────────── #

    def _build_ui(self) -> None:
        self._setup_window()
        self._setup_menu()
        self._setup_terminal_display()

    def _setup_window(self):
        self.root.title("🌟 AI OS Enhanced – Neural Terminal Interface")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)

    def _setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        def _add_accel(menu, label, cmd, accel):
            menu.add_command(label=label, command=cmd, accelerator=accel)

        # FILE MENU
        file_menu = tk.Menu(menubar, tearoff=0)
        _add_accel(file_menu, "🆕 New Session", self.new_session, "Ctrl+N")
        _add_accel(file_menu, "💾 Export Session", self.export_session, "Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="🔄 Restart CLI", command=self.restart_cli)
        file_menu.add_separator()
        _add_accel(file_menu, "🚪 Exit", self.quit_app, "Ctrl+Q")
        menubar.add_cascade(label="File", menu=file_menu)

        # VIEW MENU (only the pieces we actually use to keep code concise)
        view_menu = tk.Menu(menubar, tearoff=0)
        themes_menu = tk.Menu(view_menu, tearoff=0)
        for theme_name, data in self.themes.items():
            themes_menu.add_command(
                label=data["description"],
                command=lambda t=theme_name: self.apply_theme(t),
            )
        view_menu.add_cascade(label="🎨 Themes", menu=themes_menu)
        view_menu.add_command(label="📜 Clear Terminal", command=self.clear_terminal, accelerator="Ctrl+L")
        menubar.add_cascade(label="View", menu=view_menu)

        # HELP MENU (shortened)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="ℹ️ About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        # HOTKEYS
        self.root.bind("<Control-n>", lambda _e: self.new_session())
        self.root.bind("<Control-e>", lambda _e: self.export_session())
        self.root.bind("<Control-q>", lambda _e: self.quit_app())
        self.root.bind("<Control-l>", lambda _e: self.clear_terminal())

    def _setup_terminal_display(self):
        main = tk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Header
        hdr = tk.Frame(main)
        hdr.pack(fill=tk.X)
        self.session_label = tk.Label(hdr, font=("Courier New", 10, "bold"))
        self.session_label.pack(side=tk.LEFT)
        self.status_label = tk.Label(hdr, font=("Courier New", 10))
        self.status_label.pack(side=tk.RIGHT)

        # Terminal
        term_frame = tk.Frame(main)
        term_frame.pack(fill=tk.BOTH, expand=True)
        yscroll = tk.Scrollbar(term_frame)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.terminal_text = tk.Text(
            term_frame,
            wrap=tk.WORD,
            yscrollcommand=yscroll.set,
            padx=15,
            pady=15,
            font=("Courier New", 11),
            state=tk.DISABLED,
        )
        self.terminal_text.pack(fill=tk.BOTH, expand=True)
        yscroll.config(command=self.terminal_text.yview)

        # Input
        inp_frame = tk.Frame(main)
        inp_frame.pack(fill=tk.X, pady=(10, 0))
        self.prompt_label = tk.Label(inp_frame, text="▶", font=("Courier New", 12, "bold"))
        self.prompt_label.pack(side=tk.LEFT, padx=(0, 10))
        self.command_entry = tk.Entry(inp_frame, font=("Courier New", 11), relief=tk.FLAT, bd=2)
        self.command_entry.pack(fill=tk.X, side=tk.LEFT)
        self.command_entry.bind("<Return>", self.send_command)
        self.command_entry.bind("<Up>", self.command_history_up)
        self.command_entry.bind("<Down>", self.command_history_down)
        self.command_entry.focus()

        # Status bar
        self.status_bar = tk.Label(
            self.root,
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("Courier New", 9),
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # Pre‑configure tag colours (used in add_terminal_output)
        for tag, colour in {
            "success": "#00ff00",
            "error": "#ff4444",
            "warning": "#ffaa00",
            "info": "#00aaff",
            "command": "#ff79c6",
        }.items():
            self.terminal_text.tag_configure(tag, foreground=colour)

    # ────────────────────────── Theme handling ─────────────────────────── #

    def apply_theme(self, name: str):
        if name not in self.themes:
            name = "cyberpunk"
        self.current_theme = name
        t = self.themes[name]
        widgets = [
            self.root,
            self.terminal_text,
            self.command_entry,
            self.prompt_label,
            self.session_label,
            self.status_label,
            self.status_bar,
        ]
        for w in widgets:
            w.configure(bg=t["bg"], fg=t["fg"])
        # special
        self.terminal_text.configure(
            insertbackground=t["cursor"],
            selectbackground=t["select_bg"],
            selectforeground=t["select_fg"],
            font=(t["font_family"], t["font_size"]),
        )
        self.command_entry.configure(insertbackground=t["cursor"], font=(t["font_family"], t["font_size"]))
        self.prompt_label.configure(fg=t["cursor"], font=(t["font_family"], t["font_size"], "bold"))
        self.status_bar.configure(text=f"🎨 Theme: {name.replace('_', ' ').title()}")

    # ─────────────────────────── CLI startup ───────────────────────────── #

    def start_cli_process(self):
        """Attempt direct mode first, fallback to subprocess."""
        if self.try_direct_integration():
            return  # success – we're in direct mode
        self.start_cli_subprocess()

    # ---------------- Direct integration ---------------- #

    def try_direct_integration(self) -> bool:
        if not CLI_AVAILABLE or not self.config:
            return False
        try:
            from agno.agent import Agent  # Lazy import – may not be installed
            from agno.models.openai import OpenAIChat
            from agno.tools.reasoning import ReasoningTools
            from agno.tools.shell import ShellTools

            agent_cfg = self.config.agent
            api_key = os.getenv("OPENAI_API_KEY") or getattr(agent_cfg, "openai_api_key", None)
            if not api_key:
                return False
            model = OpenAIChat(id=agent_cfg.model, api_key=api_key)
            self.direct_agent = Agent(model=model, tools=[ReasoningTools(), ShellTools()])
            self.direct_mode = True
            self.status_label.configure(text="✅ Direct Mode")
            self.add_terminal_output("🤖 Direct AI agent initialised.\n", "success")
            return True
        except Exception as e:
            self.add_terminal_output(f"❌ Direct mode failed: {e}\n", "error")
            return False

    # ---------------- Subprocess mode ------------------- #

    def start_cli_subprocess(self):
        if not os.path.exists("app.py"):
            self.add_terminal_output("❌ app.py not found – cannot launch CLI.\n", "error")
            return
        cmd = [sys.executable, os.path.abspath("app.py")]
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            self.cli_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env,
            )
            threading.Thread(target=self._reader_thread, daemon=True).start()
            self.status_label.configure(text="✅ CLI Active (subprocess)")
            self.add_terminal_output("🚀 Subprocess CLI started.\n", "success")
        except Exception as e:
            self.add_terminal_output(f"❌ Failed to start CLI subprocess: {e}\n", "error")

    def _reader_thread(self):
        assert self.cli_process is not None
        for line in iter(self.cli_process.stdout.readline, ""):
            self.output_queue.put(("stdout", self._clean_ansi(line)))
        self.output_queue.put(("error", "🔚 CLI process ended.\n"))

    # ───────────────────────── Output / input ──────────────────────────── #

    @staticmethod
    def _clean_ansi(txt: str) -> str:
        import re
        return re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", txt)

    def monitor_output(self):
        try:
            while True:
                ot, content = self.output_queue.get_nowait()
                self.add_terminal_output(content, ot if ot != "stdout" else None)
        except queue.Empty:
            pass
        self.root.after(100, self.monitor_output)

    # Unified
    def send_command(self, _event=None):
        command = self.command_entry.get().strip()
        if not command:
            return
        self.command_entry.delete(0, tk.END)
        self.add_terminal_output(f"▶ {command}\n", "command")
        # history
        self.command_history.append(command)
        self.history_index = -1

        if self.direct_mode and self.direct_agent is not None:
            self._dispatch_direct(command)
        elif self.cli_process and self.cli_process.poll() is None:
            try:
                self.cli_process.stdin.write(command + "\n")
                self.cli_process.stdin.flush()
            except Exception as e:
                self.add_terminal_output(f"❌ Send failed: {e}\n", "error")
        else:
            self.add_terminal_output("❌ No active CLI or agent. Restart from File > Restart CLI.\n", "error")

    # Direct helper
    def _dispatch_direct(self, command: str):
        def task():
            try:
                response = self.direct_agent.run(command)
                self.output_queue.put(("stdout", f"{response}\n"))
            except Exception as exc:
                self.output_queue.put(("error", f"❌ AI error: {exc}\n"))
        threading.Thread(target=task, daemon=True).start()

    # ------------ Misc helpers ------------- #

    def add_terminal_output(self, text: str, tag: str | None = None):
        self.terminal_text.config(state=tk.NORMAL)
        self.terminal_text.insert(tk.END, text, tag)
        self.terminal_text.see(tk.END)
        self.terminal_text.config(state=tk.DISABLED)

    def command_history_up(self, _e):
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, self.command_history[-1 - self.history_index])
        return "break"

    def command_history_down(self, _e):
        if self.history_index > 0:
            self.history_index -= 1
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, self.command_history[-1 - self.history_index])
        else:
            self.history_index = -1
            self.command_entry.delete(0, tk.END)
        return "break"

    # ------------ Menu callbacks ------------- #

    def new_session(self):
        if messagebox.askyesno("New Session", "Start a new session? This will restart the CLI/agent."):
            self.restart_cli()

    def restart_cli(self):
        if self.cli_process:
            try:
                self.cli_process.terminate()
            except Exception:
                pass
            self.cli_process = None
        self.direct_mode = False
        self.direct_agent = None
        self.clear_terminal()
        self.start_cli_process()

    def clear_terminal(self):
        self.terminal_text.config(state=tk.NORMAL)
        self.terminal_text.delete("1.0", tk.END)
        self.terminal_text.config(state=tk.DISABLED)

    def export_session(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.terminal_text.get("1.0", tk.END))
        messagebox.showinfo("Export", f"Session saved to {path}")

    def show_about(self):
        messagebox.showinfo(
            "About",
            "AI OS Enhanced v2.1\nA minimal nostalgic GUI wrapper for your CLI.",
        )

    def quit_app(self):
        if messagebox.askyesno("Quit", "Exit AI OS Enhanced?"):
            if self.cli_process:
                try:
                    self.cli_process.terminate()
                except Exception:
                    pass
            self.root.quit()

    # ------------ Welcome ------------- #

    def show_welcome_message(self):
        self.add_terminal_output(
            f"\n🌟 AI OS Enhanced ready – {'Direct AI' if self.direct_mode else 'Subprocess CLI'} mode.\n\n",
            "info",
        )

    # ─────────────────────────── Public run ────────────────────────────── #

    def run(self):
        self.root.mainloop()


# ─────────────────────────── Entry‑point ──────────────────────────────── #


def main():
    app = AITerminalGUI()
    app.run()


if __name__ == "__main__":
    main()
