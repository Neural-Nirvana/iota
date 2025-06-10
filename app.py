# app.py – Integrated Tk‑GUI version with Markdown Rendering and Theme Support v1.4
"""
A terminal based AI agent that lets you interact with any device.
Changelog v1.4
---------------
* **Theme Support**: Added configurable themes (Retro, Minimal, GenZ)
* **Dynamic Styling**: Styles now change based on selected theme
* **Enhanced Preferences**: Theme selection in preferences dialog
* **Live Theme Switching**: Apply theme changes without restart
"""
from __future__ import annotations

import os
import platform
import queue
import re
import shlex
import subprocess
import sys
import threading
from datetime import datetime
from textwrap import dedent
from typing import Any, Dict

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
    from config import load_config, save_config
except ImportError:
    print("config.py missing – create one with create_default_config() first.")
    sys.exit(1)


class ThemeManager:
    """Manages different visual themes for the terminal."""
    
    THEMES = {
        "retro": {
            "name": "Retro Terminal",
            "description": "Classic green-on-black terminal vibes",
            "colors": {
                "background": "#000000",
                "foreground": "#00ff00",
                "comment": "#00aa00",
                "cyan": "#00ffff",
                "green": "#00ff00",
                "pink": "#ff00ff",
                "purple": "#aa00aa",
                "red": "#ff0000",
                "orange": "#ffaa00",
                "yellow": "#ffff00",
                "selection": "#333333",
                "code_bg": "#111111",
                "quote_bg": "#0a0a0a",
            }
        },
        "minimal": {
            "name": "Minimal Clean",
            "description": "Clean, professional black and white",
            "colors": {
                "background": "#1a1a1a",
                "foreground": "#e0e0e0",
                "comment": "#808080",
                "cyan": "#b0b0b0",
                "green": "#d0d0d0",
                "pink": "#c0c0c0",
                "purple": "#a0a0a0",
                "red": "#ff6b6b",
                "orange": "#ffa500",
                "yellow": "#ffeb3b",
                "selection": "#404040",
                "code_bg": "#2a2a2a",
                "quote_bg": "#252525",
            }
        },
        "genz": {
            "name": "GenZ Vibes",
            "description": "Bright, vibrant neon colors",
            "colors": {
                "background": "#0d1117",
                "foreground": "#f0f6fc",
                "comment": "#7c3aed",
                "cyan": "#00d4aa",
                "green": "#39ff14",
                "pink": "#ff007f",
                "purple": "#bf00ff",
                "red": "#ff073a",
                "orange": "#ff8c00",
                "yellow": "#ffff00",
                "selection": "#21262d",
                "code_bg": "#161b22",
                "quote_bg": "#0d1117",
            }
        },
        "dracula": {
            "name": "Dracula Classic",
            "description": "The classic Dracula theme",
            "colors": {
                "background": "#282a36",
                "foreground": "#f8f8f2",
                "comment": "#6272a4",
                "cyan": "#8be9fd",
                "green": "#50fa7b",
                "pink": "#ff79c6",
                "purple": "#bd93f9",
                "red": "#ff5555",
                "orange": "#ffb86c",
                "yellow": "#f1fa8c",
                "selection": "#44475a",
                "code_bg": "#44475a",
                "quote_bg": "#383a45",
            }
        }
    }
    
    @classmethod
    def get_theme_names(cls) -> list[str]:
        """Get list of available theme names."""
        return list(cls.THEMES.keys())
    
    @classmethod
    def get_theme_colors(cls, theme_name: str) -> Dict[str, str]:
        """Get color palette for a specific theme."""
        return cls.THEMES.get(theme_name, cls.THEMES["dracula"])["colors"]
    
    @classmethod
    def get_theme_info(cls, theme_name: str) -> Dict[str, str]:
        """Get theme name and description."""
        theme = cls.THEMES.get(theme_name, cls.THEMES["dracula"])
        return {
            "name": theme["name"],
            "description": theme["description"]
        }


class Styles:
    """A collection of style constants for the GUI - now theme-aware."""

    FONT_FAMILY = ("Fira Code", "Consolas", "Courier New")
    FONT_SIZE_NORMAL = 11
    FONT_SIZE_SMALL = 10
    FONT_SIZE_LARGE = 14
    FONT_SIZE_XLARGE = 16
    FONT_NORMAL = (FONT_FAMILY, FONT_SIZE_NORMAL)
    FONT_BOLD = (FONT_FAMILY, FONT_SIZE_NORMAL, "bold")
    FONT_ITALIC = (FONT_FAMILY, FONT_SIZE_NORMAL, "italic")
    FONT_BOLD_ITALIC = (FONT_FAMILY, FONT_SIZE_NORMAL, "bold", "italic")
    FONT_SMALL_LINK = (FONT_FAMILY, FONT_SIZE_SMALL, "underline")
    FONT_CODE = ("Courier New", FONT_SIZE_NORMAL)
    FONT_H1 = (FONT_FAMILY, FONT_SIZE_XLARGE, "bold")
    FONT_H2 = (FONT_FAMILY, FONT_SIZE_LARGE, "bold")
    FONT_H3 = (FONT_FAMILY, FONT_SIZE_NORMAL, "bold")

    def __init__(self, theme_name: str = "dracula"):
        """Initialize styles with a specific theme."""
        self.update_theme(theme_name)
    
    def update_theme(self, theme_name: str):
        """Update color scheme based on theme."""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        self.COLOR_BACKGROUND = colors["background"]
        self.COLOR_FOREGROUND = colors["foreground"]
        self.COLOR_COMMENT = colors["comment"]
        self.COLOR_CYAN = colors["cyan"]
        self.COLOR_GREEN = colors["green"]
        self.COLOR_PINK = colors["pink"]
        self.COLOR_PURPLE = colors["purple"]
        self.COLOR_RED = colors["red"]
        self.COLOR_ORANGE = colors["orange"]
        self.COLOR_YELLOW = colors["yellow"]
        self.COLOR_SELECTION = colors["selection"]
        self.COLOR_CODE_BG = colors["code_bg"]
        self.COLOR_QUOTE_BG = colors["quote_bg"]


class MarkdownRenderer:
    """Renders markdown text in a tkinter Text widget with proper formatting."""
    
    def __init__(self, text_widget, styles):
        self.text = text_widget
        self.styles = styles
        self._setup_tags()
    
    def _setup_tags(self):
        """Configure text tags for different markdown elements."""
        # Headers
        self.text.tag_configure("h1", font=self.styles.FONT_H1, foreground=self.styles.COLOR_PINK, spacing1=10, spacing3=5)
        self.text.tag_configure("h2", font=self.styles.FONT_H2, foreground=self.styles.COLOR_PURPLE, spacing1=8, spacing3=4)
        self.text.tag_configure("h3", font=self.styles.FONT_H3, foreground=self.styles.COLOR_CYAN, spacing1=6, spacing3=3)
        
        # Text styles
        self.text.tag_configure("bold", font=self.styles.FONT_BOLD, foreground=self.styles.COLOR_FOREGROUND)
        self.text.tag_configure("italic", font=self.styles.FONT_ITALIC, foreground=self.styles.COLOR_FOREGROUND)
        self.text.tag_configure("bold_italic", font=self.styles.FONT_BOLD_ITALIC, foreground=self.styles.COLOR_FOREGROUND)
        
        # Code
        self.text.tag_configure("code", font=self.styles.FONT_CODE, foreground=self.styles.COLOR_ORANGE, 
                               background=self.styles.COLOR_CODE_BG, borderwidth=1, relief="solid")
        self.text.tag_configure("code_block", font=self.styles.FONT_CODE, foreground=self.styles.COLOR_GREEN,
                               background=self.styles.COLOR_CODE_BG, lmargin1=20, lmargin2=20, 
                               spacing1=5, spacing3=5, borderwidth=1, relief="solid")
        
        # Lists
        self.text.tag_configure("list_item", lmargin1=20, lmargin2=40, spacing1=2)
        self.text.tag_configure("bullet", foreground=self.styles.COLOR_PINK, font=self.styles.FONT_BOLD)
        
        # Quotes
        self.text.tag_configure("quote", lmargin1=20, lmargin2=20, foreground=self.styles.COLOR_COMMENT,
                               background=self.styles.COLOR_QUOTE_BG, font=self.styles.FONT_ITALIC, 
                               spacing1=5, spacing3=5, borderwidth=1, relief="solid")
        
        # Links
        self.text.tag_configure("link", foreground=self.styles.COLOR_CYAN, underline=True)
        
        # Default
        self.text.tag_configure("normal", foreground=self.styles.COLOR_FOREGROUND, font=self.styles.FONT_NORMAL)
    
    def update_theme(self, styles):
        """Update markdown renderer with new theme styles."""
        self.styles = styles
        self._setup_tags()
    
    def render(self, markdown_text: str):
        """Parse and render markdown text in the text widget."""
        lines = markdown_text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Skip empty lines
            if not line.strip():
                self.text.insert(tk.END, "\n")
                i += 1
                continue
            
            # Code blocks
            if line.strip().startswith('```'):
                i = self._render_code_block(lines, i)
                continue
            
            # Headers
            if line.startswith('#'):
                self._render_header(line)
                i += 1
                continue
            
            # Blockquotes
            if line.strip().startswith('>'):
                i = self._render_blockquote(lines, i)
                continue
            
            # Lists
            if re.match(r'^\s*[-*+]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
                i = self._render_list(lines, i)
                continue
            
            # Regular paragraph
            self._render_paragraph(line)
            i += 1
        
        self.text.insert(tk.END, "\n")
    
    def _render_header(self, line: str):
        """Render header line."""
        match = re.match(r'^(#{1,3})\s*(.*)', line)
        if match:
            level = len(match.group(1))
            text = match.group(2)
            tag = f"h{level}"
            self.text.insert(tk.END, text + "\n", tag)
    
    def _render_code_block(self, lines: list, start_idx: int) -> int:
        """Render code block and return next line index."""
        # Find the closing ```
        end_idx = start_idx + 1
        while end_idx < len(lines) and not lines[end_idx].strip().startswith('```'):
            end_idx += 1
        
        # Extract code content
        code_lines = lines[start_idx + 1:end_idx]
        code_text = '\n'.join(code_lines)
        
        if code_text.strip():
            self.text.insert(tk.END, code_text + "\n", "code_block")
        
        return end_idx + 1
    
    def _render_blockquote(self, lines: list, start_idx: int) -> int:
        """Render blockquote and return next line index."""
        quote_lines = []
        i = start_idx
        
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith('>'):
                # Remove the > and any following space
                quote_text = re.sub(r'^\s*>\s?', '', line)
                quote_lines.append(quote_text)
                i += 1
            elif not line.strip():  # Empty line continues the quote
                quote_lines.append('')
                i += 1
            else:
                break
        
        quote_text = '\n'.join(quote_lines)
        if quote_text.strip():
            self.text.insert(tk.END, quote_text + "\n", "quote")
        
        return i
    
    def _render_list(self, lines: list, start_idx: int) -> int:
        """Render list and return next line index."""
        i = start_idx
        
        while i < len(lines):
            line = lines[i]
            
            # Bullet list
            bullet_match = re.match(r'^(\s*)([-*+])\s+(.*)', line)
            if bullet_match:
                indent = bullet_match.group(1)
                bullet = bullet_match.group(2)
                text = bullet_match.group(3)
                
                self.text.insert(tk.END, indent + "• ", "bullet")
                self._render_inline_formatting(text)
                self.text.insert(tk.END, "\n", "list_item")
                i += 1
                continue
            
            # Numbered list
            number_match = re.match(r'^(\s*)(\d+)\.\s+(.*)', line)
            if number_match:
                indent = number_match.group(1)
                number = number_match.group(2)
                text = number_match.group(3)
                
                self.text.insert(tk.END, f"{indent}{number}. ", "bullet")
                self._render_inline_formatting(text)
                self.text.insert(tk.END, "\n", "list_item")
                i += 1
                continue
            
            # Check if this is a continuation or end of list
            if not line.strip():
                i += 1
                continue
            else:
                break
        
        return i
    
    def _render_paragraph(self, line: str):
        """Render a regular paragraph with inline formatting."""
        self._render_inline_formatting(line)
        self.text.insert(tk.END, "\n", "normal")
    
    def _render_inline_formatting(self, text: str):
        """Parse and render inline formatting like bold, italic, code, links."""
        # Regular expressions for inline formatting
        patterns = [
            (r'\*\*\*(.*?)\*\*\*', 'bold_italic'),  # Bold italic
            (r'___(.*?)___', 'bold_italic'),
            (r'\*\*(.*?)\*\*', 'bold'),  # Bold
            (r'__(.*?)__', 'bold'),
            (r'\*(.*?)\*', 'italic'),  # Italic
            (r'_(.*?)_', 'italic'),
            (r'`(.*?)`', 'code'),  # Inline code
            (r'\[([^\]]+)\]\(([^)]+)\)', 'link'),  # Links
        ]
        
        # Find all matches with their positions
        matches = []
        for pattern, tag in patterns:
            for match in re.finditer(pattern, text):
                matches.append((match.start(), match.end(), match, tag))
        
        # Sort matches by position
        matches.sort(key=lambda x: x[0])
        
        # Render text with formatting
        last_end = 0
        for start, end, match, tag in matches:
            # Add text before this match
            if start > last_end:
                self.text.insert(tk.END, text[last_end:start], "normal")
            
            # Add formatted text
            if tag == 'link':
                link_text = match.group(1)
                link_url = match.group(2)
                self.text.insert(tk.END, f"{link_text} ({link_url})", tag)
            else:
                formatted_text = match.group(1)
                self.text.insert(tk.END, formatted_text, tag)
            
            last_end = end
        
        # Add remaining text
        if last_end < len(text):
            self.text.insert(tk.END, text[last_end:], "normal")


class NeuralTerminalGUI:
    """Tkinter wrapper for the Agent with a refined look and feel."""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.config = load_config()
        
        # Initialize styles with current theme
        self.styles = Styles(self.config.ui.theme)
        
        self.root = tk.Tk()
        self.root.title("AIOS Neural Terminal 🌟")
        self.root.geometry("1000x700")
        self.root.configure(bg=self.styles.COLOR_BACKGROUND)

        # Main text area
        self.text = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            font=self.styles.FONT_NORMAL,
            bg=self.styles.COLOR_BACKGROUND,
            fg=self.styles.COLOR_FOREGROUND,
            selectbackground=self.styles.COLOR_SELECTION,
            selectforeground=self.styles.COLOR_FOREGROUND,
            insertbackground=self.styles.COLOR_FOREGROUND,  # Cursor color
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        self.text.pack(fill=tk.BOTH, expand=True)
        self.text.configure(state=tk.DISABLED)

        # Initialize markdown renderer
        self.markdown_renderer = MarkdownRenderer(self.text, self.styles)

        # Bottom input frame
        bottom = tk.Frame(self.root, bg=self.styles.COLOR_BACKGROUND)
        bottom.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Input prompt symbol
        self.prompt_label = tk.Label(
            bottom, text="▶", font=self.styles.FONT_BOLD, 
            fg=self.styles.COLOR_PINK, bg=self.styles.COLOR_BACKGROUND
        )
        self.prompt_label.pack(side=tk.LEFT, padx=(0, 5))

        # Input entry field
        self.entry = tk.Entry(
            bottom,
            font=self.styles.FONT_NORMAL,
            bg=self.styles.COLOR_BACKGROUND,
            fg=self.styles.COLOR_FOREGROUND,
            insertbackground=self.styles.COLOR_FOREGROUND,
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
            self._append_markdown(
                "⚠ **No API key configured.** Open **Edit ▸ Preferences…** to set your "
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

    def _apply_theme(self, theme_name: str):
        """Apply a new theme to the entire interface."""
        self.styles.update_theme(theme_name)
        
        # Update root window
        self.root.configure(bg=self.styles.COLOR_BACKGROUND)
        
        # Update main text area
        self.text.configure(
            bg=self.styles.COLOR_BACKGROUND,
            fg=self.styles.COLOR_FOREGROUND,
            selectbackground=self.styles.COLOR_SELECTION,
            selectforeground=self.styles.COLOR_FOREGROUND,
            insertbackground=self.styles.COLOR_FOREGROUND,
        )
        
        # Update prompt label
        self.prompt_label.configure(
            fg=self.styles.COLOR_PINK,
            bg=self.styles.COLOR_BACKGROUND
        )
        
        # Update entry field
        self.entry.configure(
            bg=self.styles.COLOR_BACKGROUND,
            fg=self.styles.COLOR_FOREGROUND,
            insertbackground=self.styles.COLOR_FOREGROUND,
        )
        
        # Update markdown renderer
        self.markdown_renderer.update_theme(self.styles)
        
        # Update bottom frame background
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame):
                widget.configure(bg=self.styles.COLOR_BACKGROUND)

    def _setup_menubar(self):
        menubar = tk.Menu(
            self.root,
            bg=self.styles.COLOR_BACKGROUND,
            fg=self.styles.COLOR_FOREGROUND,
            activebackground=self.styles.COLOR_SELECTION,
            activeforeground=self.styles.COLOR_FOREGROUND,
            relief=tk.FLAT,
            borderwidth=0,
        )
        self.root.config(menu=menubar)

        # File Menu
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Export Session", command=self._export)
        filemenu.add_separator(background=self.styles.COLOR_SELECTION)
        filemenu.add_command(label="Quit", command=self.root.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=filemenu)

        # Edit Menu
        editmenu = tk.Menu(menubar, tearoff=0)
        editmenu.add_command(label="Preferences…", command=self._prefs_dialog)
        editmenu.add_separator(background=self.styles.COLOR_SELECTION)
        
        # Theme submenu
        thememenu = tk.Menu(editmenu, tearoff=0)
        for theme_key in ThemeManager.get_theme_names():
            theme_info = ThemeManager.get_theme_info(theme_key)
            thememenu.add_command(
                label=f"{theme_info['name']} - {theme_info['description']}", 
                command=lambda t=theme_key: self._change_theme(t)
            )
        editmenu.add_cascade(label="Themes", menu=thememenu)
        
        menubar.add_cascade(label="Edit", menu=editmenu)

        # Apply styles to submenus
        for menu in (filemenu, editmenu, thememenu):
            menu.config(
                bg=self.styles.COLOR_BACKGROUND,
                fg=self.styles.COLOR_FOREGROUND,
                activebackground=self.styles.COLOR_SELECTION,
                activeforeground=self.styles.COLOR_PINK,  # Highlight selection
                relief=tk.FLAT,
            )

    def _change_theme(self, theme_name: str):
        """Change the current theme and save to config."""
        self.config.ui.theme = theme_name
        save_config(self.config)
        self._apply_theme(theme_name)
        
        theme_info = ThemeManager.get_theme_info(theme_name)
        self._append_markdown(f"\n🎨 **Theme changed to {theme_info['name']}** — {theme_info['description']}\n", tag="info")

    # ───────────────────────── Internal helpers ───────────────────────── #

    def _banner(self):
        theme_info = ThemeManager.get_theme_info(self.config.ui.theme)
        info = (
            f"**Provider:** {self.config.agent.provider.title()}  |  **Model:** {self.config.agent.model}\n"
            f"**Theme:** {theme_info['name']}  |  **System:** {platform.system()} {platform.release()}\n"
            f"**Session start:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "Type `help` for commands or `$` to run shell commands (e.g., `$ ls -l`)."
        )
        self._append_markdown(info, tag="info")

    def _append(self, text: Any, tag: str | None = None):
        """Append plain text without markdown parsing."""
        if not isinstance(text, str):
            text = str(text)
        self.text.configure(state=tk.NORMAL)
        if tag:
            tag_colors = {
                "user": self.styles.COLOR_PINK,
                "error": self.styles.COLOR_RED,
                "info": self.styles.COLOR_COMMENT,
                "spin": self.styles.COLOR_PURPLE,
                "shell_out": self.styles.COLOR_GREEN,
                "agent_response": self.styles.COLOR_FOREGROUND,
            }
            self.text.tag_configure(tag, foreground=tag_colors.get(tag, self.styles.COLOR_FOREGROUND))
        self.text.insert(tk.END, text + "\n", tag)
        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)

    def _append_markdown(self, text: Any, tag: str | None = None):
        """Append text with markdown parsing and rendering."""
        if not isinstance(text, str):
            text = str(text)
        self.text.configure(state=tk.NORMAL)
        
        # For special tags like error, info, etc., apply the tag to the entire text
        if tag and tag in ["user", "error", "info", "spin", "shell_out"]:
            tag_colors = {
                "user": self.styles.COLOR_PINK,
                "error": self.styles.COLOR_RED,
                "info": self.styles.COLOR_COMMENT,
                "spin": self.styles.COLOR_PURPLE,
                "shell_out": self.styles.COLOR_GREEN,
            }
            self.text.tag_configure(tag, foreground=tag_colors.get(tag, self.styles.COLOR_FOREGROUND))
            self.text.insert(tk.END, text + "\n", tag)
        else:
            # Parse and render markdown
            self.markdown_renderer.render(text)
        
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
        self.text.tag_configure("spin", foreground=self.styles.COLOR_PURPLE)
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
        top.configure(bg=self.styles.COLOR_BACKGROUND)

        txt = scrolledtext.ScrolledText(
            top,
            wrap=tk.WORD,
            font=self.styles.FONT_NORMAL,
            bg=self.styles.COLOR_BACKGROUND,
            fg=self.styles.COLOR_FOREGROUND,
            selectbackground=self.styles.COLOR_SELECTION,
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        txt.pack(fill=tk.BOTH, expand=True)
        txt.configure(state=tk.NORMAL)

        # Create markdown renderer for thinking window
        thinking_renderer = MarkdownRenderer(txt, self.styles)

        # Chain-of-thought
        if data["reasoning"]:
            thinking_renderer.render("# 🧠 Reasoning\n\n" + data["reasoning"].strip() + "\n\n")

        # Tool calls with syntax highlighting
        if data["calls"]:
            thinking_renderer.render("# 🔧 Tool Calls\n\n")
            for i, call in enumerate(data["calls"], 1):
                tool_info = f"{i}. **{call['tool_name']}**`({call['tool_args']})`"
                if call["tool_output"]:
                    output_short = (call["tool_output"][:100] + '...') if len(call["tool_output"]) > 100 else call["tool_output"]
                    tool_info += f"\n   → `{output_short}`"
                thinking_renderer.render(tool_info + "\n\n")

        if not data["reasoning"] and not data["calls"]:
            thinking_renderer.render("*(The model did not expose any intermediate steps.)*")

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
                    # Use markdown rendering for agent responses

                    self._append_markdown(item["content"])
                    self.text.configure(state=tk.NORMAL)

                    # Create a clickable label instead of a button
                    link = tk.Label(
                        self.text,
                        text="Show Thinking",
                        font=self.styles.FONT_SMALL_LINK,
                        fg=self.styles.COLOR_PURPLE,
                        bg=self.styles.COLOR_BACKGROUND,
                        cursor="hand2",
                    )
                    link.bind("<Button-1>", lambda e, data=item: self._show_thinking(data))
                    link.bind("<Enter>", lambda e: e.widget.config(fg=self.styles.COLOR_PINK))
                    link.bind("<Leave>", lambda e: e.widget.config(fg=self.styles.COLOR_PURPLE))

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
        win.configure(bg=self.styles.COLOR_BACKGROUND, padx=20, pady=15)
        win.resizable(False, False)

        # --- Styles for widgets ---
        label_style = {"bg": self.styles.COLOR_BACKGROUND, "fg": self.styles.COLOR_FOREGROUND, "font": self.styles.FONT_NORMAL}
        entry_style = {
            "bg": self.styles.COLOR_SELECTION, "fg": self.styles.COLOR_FOREGROUND, "font": self.styles.FONT_NORMAL,
            "relief": tk.FLAT, "highlightthickness": 0, "insertbackground": self.styles.COLOR_FOREGROUND,
        }

        # --- Provider ---
        tk.Label(win, text="Provider", **label_style).grid(row=0, column=0, sticky="w", pady=(0, 5))
        provider_var = tk.StringVar(value=self.config.agent.provider)
        provider_menu = tk.OptionMenu(win, provider_var, "openai", "google", "openrouter", "together")
        provider_menu.config(
            bg=self.styles.COLOR_SELECTION, fg=self.styles.COLOR_FOREGROUND, activebackground=self.styles.COLOR_SELECTION,
            activeforeground=self.styles.COLOR_FOREGROUND, relief=tk.FLAT, highlightthickness=0, width=25,
            direction="below", borderwidth=0,
        )
        provider_menu["menu"].config(
            bg=self.styles.COLOR_BACKGROUND, fg=self.styles.COLOR_FOREGROUND,
            activebackground=self.styles.COLOR_SELECTION, activeforeground=self.styles.COLOR_PINK, relief=tk.FLAT,
        )
        provider_menu.grid(row=0, column=1, sticky="ew", pady=(0, 10))

        # --- Model ---
        tk.Label(win, text="Model", **label_style).grid(row=1, column=0, sticky="w", pady=(0, 5))
        model_var = tk.StringVar(value=self.config.agent.model)
        tk.Entry(win, textvariable=model_var, width=30, **entry_style).grid(row=1, column=1, pady=(0, 10))

        # --- API Key ---
        tk.Label(win, text="API Key", **label_style).grid(row=2, column=0, sticky="w", pady=(0, 5))
        key_var = tk.StringVar()
        tk.Entry(win, textvariable=key_var, show="•", width=30, **entry_style).grid(row=2, column=1, pady=(0, 10))

        # --- Theme Selection ---
        tk.Label(win, text="Theme", **label_style).grid(row=3, column=0, sticky="w", pady=(0, 5))
        theme_var = tk.StringVar(value=self.config.ui.theme)
        
        # Create theme dropdown with descriptive names
        theme_options = []
        theme_mapping = {}
        for theme_key in ThemeManager.get_theme_names():
            theme_info = ThemeManager.get_theme_info(theme_key)
            display_name = f"{theme_info['name']}"
            theme_options.append(display_name)
            theme_mapping[display_name] = theme_key
        
        current_theme_info = ThemeManager.get_theme_info(self.config.ui.theme)
        current_display_name = current_theme_info['name']
        theme_var.set(current_display_name)
        
        theme_menu = tk.OptionMenu(win, theme_var, *theme_options)
        theme_menu.config(
            bg=self.styles.COLOR_SELECTION, fg=self.styles.COLOR_FOREGROUND, 
            activebackground=self.styles.COLOR_SELECTION, activeforeground=self.styles.COLOR_FOREGROUND, 
            relief=tk.FLAT, highlightthickness=0, width=25, direction="below", borderwidth=0,
        )
        theme_menu["menu"].config(
            bg=self.styles.COLOR_BACKGROUND, fg=self.styles.COLOR_FOREGROUND,
            activebackground=self.styles.COLOR_SELECTION, activeforeground=self.styles.COLOR_PINK, relief=tk.FLAT,
        )
        theme_menu.grid(row=3, column=1, sticky="ew", pady=(0, 15))

        def _save():
            cfg = self.config
            cfg.agent.provider = provider_var.get()
            cfg.agent.model = model_var.get()
            key = key_var.get().strip()
            if key:
                setattr(cfg.agent, f"{provider_var.get()}_api_key", key)
            
            # Handle theme change
            selected_theme_display = theme_var.get()
            selected_theme_key = theme_mapping.get(selected_theme_display, "dracula")
            if cfg.ui.theme != selected_theme_key:
                cfg.ui.theme = selected_theme_key
                self._apply_theme(selected_theme_key)
            
            save_config(cfg)
            self.agent = build_agent(cfg)  # hot-swap
            self._append_markdown("\n— **Preferences updated & agent restarted** —\n", tag="info")
            win.destroy()

        # --- Save Button ---
        save_button = tk.Button(
            win, text="Save & Restart Agent", command=_save, relief=tk.FLAT,
            bg=self.styles.COLOR_PURPLE, fg=self.styles.COLOR_FOREGROUND,
            activebackground=self.styles.COLOR_PINK, activeforeground=self.styles.COLOR_FOREGROUND,
            font=self.styles.FONT_NORMAL, padx=10, pady=5, borderwidth=0,
        )
        save_button.grid(row=4, column=0, columnspan=2, pady=8)
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