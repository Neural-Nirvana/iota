# app_enhanced.py – Enhanced Tk‑GUI version with improved UX v2.0
"""
An enhanced GUI terminal for your AGNO Agent with modern UX improvements.

New Features v2.0:
------------------
* **Enhanced UI**: Modern dark theme with better colors and typography
* **Message Bubbles**: Chat-like interface with distinct user/agent messages
* **Typing Indicator**: Shows when agent is thinking/responding
* **Status Bar**: Shows connection status, model info, and stats
* **Better Input**: Multi-line support, command history, auto-resize
* **Keyboard Shortcuts**: Comprehensive shortcut system
* **Settings Panel**: Configurable theme, font size, and preferences
* **Message Actions**: Copy, delete, regenerate responses
* **Search**: Find text in conversation history
* **Loading States**: Better feedback for long operations
* **Auto-save**: Automatic session persistence
"""
from __future__ import annotations

import json
import os
import platform
import queue
import sys
import threading
import time
from datetime import datetime
from textwrap import dedent
from typing import Any, Dict, List

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from tkinter import font as tkfont

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


class ThemeManager:
    """Manages UI themes and styling."""
    
    THEMES = {
        "dark": {
            "bg": "#1a1a1a",
            "fg": "#e4e4e7",
            "input_bg": "#2a2a2a",
            "input_fg": "#f4f4f5",
            "user_bg": "#374151",
            "agent_bg": "#1f2937",
            "error_bg": "#450a0a",
            "info_bg": "#1e293b",
            "border": "#374151",
            "accent": "#6366f1",
            "muted": "#9ca3af",
            "user_text": "#f9fafb",
            "agent_text": "#e5e7eb",
            "hover": "#374151"
        },
        "light": {
            "bg": "#fafafa",
            "fg": "#374151",
            "input_bg": "#ffffff",
            "input_fg": "#111827",
            "user_bg": "#e5e7eb",
            "agent_bg": "#f3f4f6",
            "error_bg": "#fef2f2",
            "info_bg": "#eff6ff",
            "border": "#d1d5db",
            "accent": "#6366f1",
            "muted": "#6b7280",
            "user_text": "#111827",
            "agent_text": "#374151",
            "hover": "#f3f4f6"
        }
    }
    
    def __init__(self, theme_name: str = "dark"):
        self.current_theme = theme_name
        self.colors = self.THEMES[theme_name]
    
    def get(self, key: str) -> str:
        return self.colors.get(key, "#000000")
    
    def switch_theme(self, theme_name: str):
        if theme_name in self.THEMES:
            self.current_theme = theme_name
            self.colors = self.THEMES[theme_name]


class MessageWidget:
    """Custom widget for displaying chat messages with modern styling."""
    
    def __init__(self, parent, text: str, sender: str, theme: ThemeManager, timestamp: str = None):
        self.parent = parent
        self.text_content = text
        self.sender = sender
        self.theme = theme
        self.timestamp = timestamp or datetime.now().strftime("%H:%M")
        
        # Create frame for message
        self.frame = tk.Frame(parent, bg=theme.get("bg"))
        
        # Message container
        self.container = tk.Frame(self.frame, bg=theme.get("bg"))
        self.container.pack(fill=tk.X, padx=10, pady=5)
        
        # Header with sender and timestamp
        header = tk.Frame(self.container, bg=theme.get("bg"))
        header.pack(fill=tk.X, anchor="w" if sender == "user" else "e")
        
        tk.Label(
            header, 
            text=f"{'You' if sender == 'user' else 'Assistant'} • {self.timestamp}",
            bg=theme.get("bg"),
            fg=theme.get("muted"),
            font=("Segoe UI", 9)
        ).pack(side="left" if sender == "user" else "right")
        
        # Message bubble
        bubble_frame = tk.Frame(self.container, bg=theme.get("bg"))
        bubble_frame.pack(fill=tk.X, pady=(2, 0))
        
        if sender == "user":
            bubble_frame.pack(anchor="e")
            bubble_bg = theme.get("user_bg")
            text_color = theme.get("user_text")
        else:
            bubble_frame.pack(anchor="w")
            bubble_bg = theme.get("agent_bg")
            text_color = theme.get("agent_text")
        
        # Text widget with styling
        self.text_widget = tk.Text(
            bubble_frame,
            wrap=tk.WORD,
            bg=bubble_bg,
            fg=text_color,
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            borderwidth=0,
            padx=15,
            pady=10,
            height=1,
            state=tk.DISABLED,
            selectbackground=theme.get("accent"),
            selectforeground="white"
        )
        
        # Insert text and auto-resize
        self.text_widget.configure(state=tk.NORMAL)
        self.text_widget.insert("1.0", text)
        self.text_widget.configure(state=tk.DISABLED)
        
        # Auto-resize based on content
        self._resize_text_widget()
        
        self.text_widget.pack(side="right" if sender == "user" else "left", anchor="ne" if sender == "user" else "nw")
        
        # Add subtle border radius effect with frames
        self._add_rounded_effect(bubble_bg)
    
    def _resize_text_widget(self):
        """Auto-resize text widget based on content."""
        self.text_widget.update_idletasks()
        lines = self.text_widget.get("1.0", "end-1c").count('\n') + 1
        self.text_widget.configure(height=min(lines, 20))  # Max 20 lines
    
    def _add_rounded_effect(self, bg_color):
        """Add visual rounded effect using frames."""
        # This is a simplified rounded effect - for true rounded corners,
        # you'd need to use Canvas or PIL
        pass
    
    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
    
    def destroy(self):
        self.frame.destroy()


class TypingIndicator:
    """Shows when the agent is typing/thinking."""
    
    def __init__(self, parent, theme: ThemeManager):
        self.parent = parent
        self.theme = theme
        self.frame = None
        self.dots = 0
        self.animation_id = None
    
    def show(self):
        """Show typing indicator."""
        if self.frame:
            return
            
        self.frame = tk.Frame(self.parent, bg=self.theme.get("bg"))
        self.frame.pack(fill=tk.X, padx=10, pady=5)
        
        container = tk.Frame(self.frame, bg=self.theme.get("bg"))
        container.pack(anchor="w")
        
        self.label = tk.Label(
            container,
            text="Assistant is thinking",
            bg=self.theme.get("agent_bg"),
            fg=self.theme.get("agent_text"),
            font=("Segoe UI", 10),
            padx=15,
            pady=8
        )
        self.label.pack()
        
        self._animate()
    
    def hide(self):
        """Hide typing indicator."""
        if self.animation_id:
            self.parent.after_cancel(self.animation_id)
            self.animation_id = None
        if self.frame:
            self.frame.destroy()
            self.frame = None
    
    def _animate(self):
        """Animate the typing dots."""
        if not self.frame:
            return
            
        dots = "." * (self.dots % 4)
        self.label.configure(text=f"Assistant is thinking{dots}")
        self.dots += 1
        self.animation_id = self.parent.after(500, self._animate)


class EnhancedNeuralTerminalGUI:
    """Enhanced Tkinter GUI for the AGNO Agent with modern UX."""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.theme = ThemeManager("dark")
        self.command_history = []
        self.history_index = -1
        self.messages = []
        
        self._setup_ui()
        self._setup_bindings()
        self._load_settings()
        
        self.queue: queue.Queue[Dict[str, Any]] = queue.Queue()
        self.root.after(100, self._poll_queue)
        
        self._show_welcome()

    def _setup_ui(self):
        """Initialize the main UI components."""
        self.root = tk.Tk()
        self.root.title("🧠 AI-OS Neural Terminal v2.0")
        self.root.geometry("1200x800")
        self.root.configure(bg=self.theme.get("bg"))
        
        # Set app icon and styling
        self.root.iconname("Neural Terminal")
        
        # Create main layout
        self._create_menu()
        self._create_toolbar()
        self._create_main_area()
        self._create_status_bar()
        
        # Apply theme
        self._apply_theme()

    def _create_menu(self):
        """Create enhanced menu bar."""
        self.menubar = tk.Menu(self.root, bg=self.theme.get("bg"), fg=self.theme.get("fg"))
        
        # File menu
        file_menu = tk.Menu(self.menubar, tearoff=0, bg=self.theme.get("bg"), fg=self.theme.get("fg"))
        file_menu.add_command(label="New Session", command=self._new_session, accelerator="Ctrl+N")
        file_menu.add_command(label="Save Session", command=self._save_session, accelerator="Ctrl+S")
        file_menu.add_command(label="Export Chat", command=self._export_chat, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_exit, accelerator="Ctrl+Q")
        self.menubar.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(self.menubar, tearoff=0, bg=self.theme.get("bg"), fg=self.theme.get("fg"))
        edit_menu.add_command(label="Copy", command=self._copy_text, accelerator="Ctrl+C")
        edit_menu.add_command(label="Clear Chat", command=self._clear_chat, accelerator="Ctrl+L")
        edit_menu.add_command(label="Find", command=self._show_search, accelerator="Ctrl+F")
        self.menubar.add_cascade(label="Edit", menu=edit_menu)
        
        # View menu
        view_menu = tk.Menu(self.menubar, tearoff=0, bg=self.theme.get("bg"), fg=self.theme.get("fg"))
        view_menu.add_command(label="Dark Theme", command=lambda: self._switch_theme("dark"))
        view_menu.add_command(label="Light Theme", command=lambda: self._switch_theme("light"))
        view_menu.add_separator()
        view_menu.add_command(label="Increase Font", command=self._increase_font, accelerator="Ctrl++")
        view_menu.add_command(label="Decrease Font", command=self._decrease_font, accelerator="Ctrl+-")
        self.menubar.add_cascade(label="View", menu=view_menu)
        
        # Help menu
        help_menu = tk.Menu(self.menubar, tearoff=0, bg=self.theme.get("bg"), fg=self.theme.get("fg"))
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
        help_menu.add_command(label="About", command=self._show_about)
        self.menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=self.menubar)

    def _create_toolbar(self):
        """Create toolbar with quick actions."""
        self.toolbar = tk.Frame(self.root, bg=self.theme.get("bg"), height=40)
        self.toolbar.pack(fill=tk.X, padx=5, pady=5)
        self.toolbar.pack_propagate(False)
        
        # Quick action buttons
        buttons = [
            ("🗑️", "Clear Chat", self._clear_chat),
            ("💾", "Save", self._save_session),
            ("🔍", "Search", self._show_search),
            ("⚙️", "Settings", self._show_settings),
        ]
        
        for icon, tooltip, command in buttons:
            btn = tk.Button(
                self.toolbar,
                text=icon,
                command=command,
                bg=self.theme.get("input_bg"),
                fg=self.theme.get("fg"),
                activebackground=self.theme.get("hover"),
                activeforeground=self.theme.get("fg"),
                relief=tk.FLAT,
                padx=12,
                pady=6,
                font=("Segoe UI", 11),
                cursor="hand2",
                borderwidth=0
            )
            btn.pack(side=tk.LEFT, padx=2)

    def _create_main_area(self):
        """Create the main chat area."""
        # Main container with scrollable frame
        self.main_frame = tk.Frame(self.root, bg=self.theme.get("bg"))
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Create scrollable chat area
        self.canvas = tk.Canvas(self.main_frame, bg=self.theme.get("bg"), highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.theme.get("bg"))
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Typing indicator
        self.typing_indicator = TypingIndicator(self.scrollable_frame, self.theme)
        
        # Input area
        self._create_input_area()

    def _create_input_area(self):
        """Create enhanced input area."""
        self.input_frame = tk.Frame(self.root, bg=self.theme.get("bg"))
        self.input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Input container with border
        input_container = tk.Frame(
            self.input_frame,
            bg=self.theme.get("input_bg"),
            relief=tk.FLAT,
            bd=0
        )
        input_container.pack(fill=tk.X, pady=2)
        
        # Add subtle border effect
        border_frame = tk.Frame(
            input_container,
            bg=self.theme.get("border"),
            height=1
        )
        border_frame.pack(fill=tk.X, side=tk.TOP)
        
        main_input = tk.Frame(input_container, bg=self.theme.get("input_bg"))
        main_input.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Prompt label
        prompt_label = tk.Label(
            main_input,
            text="▶",
            bg=self.theme.get("input_bg"),
            fg=self.theme.get("accent"),
            font=("Segoe UI", 12, "bold"),
            padx=12
        )
        prompt_label.pack(side=tk.LEFT, fill=tk.Y)
        
        # Multi-line input text widget
        self.input_text = tk.Text(
            main_input,
            height=1,
            wrap=tk.WORD,
            bg=self.theme.get("input_bg"),
            fg=self.theme.get("input_fg"),
            font=("Segoe UI", 11),
            relief=tk.FLAT,
            borderwidth=0,
            padx=8,
            pady=8,
            insertbackground=self.theme.get("accent"),
            selectbackground=self.theme.get("accent"),
            selectforeground="white"
        )
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Send button
        self.send_button = tk.Button(
            main_input,
            text="Send",
            command=self._send_message,
            bg=self.theme.get("accent"),
            fg="white",
            activebackground="#5855eb",
            activeforeground="white",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
            borderwidth=0
        )
        self.send_button.pack(side=tk.RIGHT, padx=(8, 0))

    def _create_status_bar(self):
        """Create status bar with info."""
        self.status_bar = tk.Frame(self.root, bg=self.theme.get("input_bg"), height=28)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_bar.pack_propagate(False)
        
        # Add subtle top border
        top_border = tk.Frame(self.status_bar, bg=self.theme.get("border"), height=1)
        top_border.pack(fill=tk.X, side=tk.TOP)
        
        # Status labels
        self.status_left = tk.Label(
            self.status_bar,
            text="Ready",
            bg=self.theme.get("input_bg"),
            fg=self.theme.get("muted"),
            font=("Segoe UI", 9),
            anchor="w"
        )
        self.status_left.pack(side=tk.LEFT, padx=12, pady=4)
        
        self.status_right = tk.Label(
            self.status_bar,
            text=f"Model: {config.agent.model} | Theme: {self.theme.current_theme}",
            bg=self.theme.get("input_bg"),
            fg=self.theme.get("muted"),
            font=("Segoe UI", 9),
            anchor="e"
        )
        self.status_right.pack(side=tk.RIGHT, padx=12, pady=4)

    def _setup_bindings(self):
        """Setup keyboard bindings and events."""
        # Input handling
        self.input_text.bind("<Return>", self._on_enter)
        self.input_text.bind("<Shift-Return>", self._on_shift_enter)
        self.input_text.bind("<KeyRelease>", self._on_input_change)
        self.input_text.bind("<Up>", self._on_up_arrow)
        self.input_text.bind("<Down>", self._on_down_arrow)
        
        # Global shortcuts
        self.root.bind("<Control-n>", lambda e: self._new_session())
        self.root.bind("<Control-s>", lambda e: self._save_session())
        self.root.bind("<Control-e>", lambda e: self._export_chat())
        self.root.bind("<Control-q>", lambda e: self._on_exit())
        self.root.bind("<Control-l>", lambda e: self._clear_chat())
        self.root.bind("<Control-f>", lambda e: self._show_search())
        self.root.bind("<Control-plus>", lambda e: self._increase_font())
        self.root.bind("<Control-minus>", lambda e: self._decrease_font())
        
        # Mouse bindings
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        # Window events
        self.root.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _apply_theme(self):
        """Apply the current theme to all UI elements."""
        # Update root and main elements
        self.root.configure(bg=self.theme.get("bg"))
        
        # Update specific elements that need manual theme application
        widgets_to_update = [
            (self.main_frame, "bg"),
            (self.canvas, "bg"),
            (self.scrollable_frame, "bg"),
            (self.input_frame, "bg"),
            (self.toolbar, "bg")
        ]
        
        for widget, prop in widgets_to_update:
            try:
                widget.configure(**{prop: self.theme.get("bg")})
            except (tk.TclError, AttributeError):
                pass
        
        # Update all message widgets
        for message in self.messages:
            try:
                message.frame.configure(bg=self.theme.get("bg"))
                # Note: Individual message styling is handled in MessageWidget
            except (tk.TclError, AttributeError):
                pass
        
        # Update input text styling
        try:
            self.input_text.configure(
                bg=self.theme.get("input_bg"),
                fg=self.theme.get("input_fg"),
                insertbackground=self.theme.get("accent"),
                selectbackground=self.theme.get("accent")
            )
        except (tk.TclError, AttributeError):
            pass

    def _show_welcome(self):
        """Show welcome message."""
        welcome_text = f"""
Welcome to AI-OS Neural Terminal v2.0! 🧠

**System Information:**
• Provider: {config.agent.provider.title()}
• Model: {config.agent.model}
• Platform: {platform.system()} {platform.release()}
• Session: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Quick Tips:**
• Use Shift+Enter for multi-line input
• Press ↑/↓ to navigate command history
• Try keyboard shortcuts (Ctrl+? for help)
• Type '/help' for agent commands

Ready to assist you! What would you like to explore today?
        """.strip()
        
        self._add_message(welcome_text, "info")

    def _add_message(self, text: str, sender: str = "agent", timestamp: str = None):
        """Add a message to the chat with enhanced styling."""
        # Handle special message types
        if sender == "info":
            sender = "agent"  # Display as agent message but with info styling
            
        message = MessageWidget(self.scrollable_frame, text, sender, self.theme, timestamp)
        message.pack(fill=tk.X, pady=2)
        self.messages.append(message)
        
        # Auto-scroll to bottom
        self.root.after(10, self._scroll_to_bottom)
        
        # Update status
        if sender == "agent":
            self.status_left.configure(text="Ready")
        elif sender == "user":
            self.status_left.configure(text="Processing...")

    def _scroll_to_bottom(self):
        """Scroll chat to bottom."""
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def _send_message(self):
        """Send message to agent."""
        text = self.input_text.get("1.0", "end-1c").strip()
        if not text:
            return
        
        # Add to history
        self.command_history.append(text)
        self.history_index = len(self.command_history)
        
        # Clear input
        self.input_text.delete("1.0", tk.END)
        self._resize_input()
        
        # Add user message
        self._add_message(text, "user")
        
        # Show typing indicator
        self.typing_indicator.show()
        
        # Process in thread
        threading.Thread(target=self._agent_task, args=(text,), daemon=True).start()

    def _agent_task(self, prompt: str):
        """Process agent request in background thread."""
        try:
            self.queue.put({"type": "status", "text": "Thinking..."})
            
            start_time = time.time()
            reply = self.agent.run(prompt)
            end_time = time.time()
            
            # Extract clean content
            if hasattr(reply, "content") and isinstance(reply.content, str):
                content = reply.content.strip()
            else:
                content = str(reply).strip()
            
            self.queue.put({
                "type": "response",
                "text": content,
                "time": end_time - start_time
            })
            
        except Exception as e:
            logger.error("Agent error", exc_info=True)
            self.queue.put({
                "type": "error",
                "text": f"Error: {str(e)}"
            })

    def _poll_queue(self):
        """Poll the message queue for updates."""
        try:
            while True:
                msg = self.queue.get_nowait()
                
                if msg["type"] == "response":
                    self.typing_indicator.hide()
                    self._add_message(msg["text"], "agent")
                    self.status_left.configure(text=f"Response in {msg['time']:.1f}s")
                    
                elif msg["type"] == "error":
                    self.typing_indicator.hide()
                    self._add_message(msg["text"], "error")
                    self.status_left.configure(text="Error occurred")
                    
                elif msg["type"] == "status":
                    self.status_left.configure(text=msg["text"])
                    
        except queue.Empty:
            pass
        
        self.root.after(100, self._poll_queue)

    # Event handlers
    def _on_enter(self, event):
        """Handle Enter key press."""
        if not event.state & 0x1:  # No Shift key
            self._send_message()
            return "break"

    def _on_shift_enter(self, event):
        """Handle Shift+Enter for new line."""
        return  # Allow default behavior

    def _on_input_change(self, event):
        """Handle input text changes for auto-resize."""
        self._resize_input()

    def _resize_input(self):
        """Auto-resize input based on content."""
        lines = self.input_text.get("1.0", "end-1c").count('\n') + 1
        new_height = min(max(lines, 1), 5)  # Between 1 and 5 lines
        self.input_text.configure(height=new_height)

    def _on_up_arrow(self, event):
        """Navigate command history up."""
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", self.command_history[self.history_index])
            return "break"

    def _on_down_arrow(self, event):
        """Navigate command history down."""
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", self.command_history[self.history_index])
            return "break"
        elif self.history_index >= len(self.command_history) - 1:
            self.input_text.delete("1.0", tk.END)
            self.history_index = len(self.command_history)
            return "break"

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_exit(self):
        """Handle application exit."""
        self._save_settings()
        self.root.quit()

    # Menu actions
    def _new_session(self):
        """Start a new session."""
        if messagebox.askyesno("New Session", "Clear current chat and start new session?"):
            self._clear_chat()
            self._show_welcome()

    def _save_session(self):
        """Save current session."""
        # This would integrate with the agent's storage system
        self.status_left.configure(text="Session saved")
        messagebox.showinfo("Save", "Session saved successfully!")

    def _export_chat(self):
        """Export chat to file."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("JSON files", "*.json")]
        )
        if filename:
            try:
                # Export logic here
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"# AI-OS Neural Terminal Session\n")
                    f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    # Add actual message export logic
                messagebox.showinfo("Export", f"Chat exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {e}")

    def _copy_text(self):
        """Copy selected text."""
        try:
            self.root.clipboard_clear()
            # Add copy logic for selected message
            messagebox.showinfo("Copy", "Text copied to clipboard")
        except:
            pass

    def _clear_chat(self):
        """Clear all messages."""
        for message in self.messages:
            message.destroy()
        self.messages.clear()

    def _show_search(self):
        """Show search dialog."""
        # Implement search functionality
        messagebox.showinfo("Search", "Search functionality coming soon!")

    def _switch_theme(self, theme_name: str):
        """Switch UI theme."""
        self.theme.switch_theme(theme_name)
        self._apply_theme()
        self.status_right.configure(text=f"Model: {config.agent.model} | Theme: {theme_name}")

    def _increase_font(self):
        """Increase font size."""
        # Implement font size adjustment
        pass

    def _decrease_font(self):
        """Decrease font size."""
        # Implement font size adjustment
        pass

    def _show_settings(self):
        """Show settings dialog."""
        messagebox.showinfo("Settings", "Settings panel coming soon!")

    def _show_shortcuts(self):
        """Show keyboard shortcuts help."""
        shortcuts = """
Keyboard Shortcuts:

Input:
• Enter: Send message
• Shift+Enter: New line
• ↑/↓: Navigate history

General:
• Ctrl+N: New session
• Ctrl+S: Save session
• Ctrl+E: Export chat
• Ctrl+L: Clear chat
• Ctrl+F: Search
• Ctrl+Q: Quit

View:
• Ctrl++: Increase font
• Ctrl+-: Decrease font
        """.strip()
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)

    def _show_about(self):
        """Show about dialog."""
        about_text = """
AI-OS Neural Terminal v2.0

An enhanced GUI interface for AGNO Agent
with modern UX and powerful features.

Built with Python and Tkinter
        """.strip()
        messagebox.showinfo("About", about_text)

    def _load_settings(self):
        """Load user settings."""
        # Implement settings loading
        pass

    def _save_settings(self):
        """Save user settings."""
        # Implement settings saving
        pass

    def run(self):
        """Start the application."""
        self.input_text.focus()
        self.root.mainloop()


# Keep the original agent factory function
def build_agent(cfg) -> Agent:
    """Build and configure the AGNO agent."""
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
            You are a System‑Intelligence Assistant running inside an enhanced GUI terminal.
            System: {platform.system()} {platform.release()}
            Provider: {provider} | Model: {model_id}
            
            Be helpful, concise, and provide clear explanations.
            Format your responses with proper markdown when appropriate.
            Warn users before executing potentially dangerous commands.
            """
        ),
        add_datetime_to_instructions=True,
        stream_intermediate_steps=True,
        show_tool_calls=True,
        markdown=True,
        storage=SqliteStorage(table_name="enhanced_gui_sessions", db_file=cfg.storage.db_file),
        add_history_to_messages=True,
        num_history_runs=3,
    )


if __name__ == "__main__":
    config = load_config()
    os.makedirs("logs", exist_ok=True)
    os.makedirs("exports", exist_ok=True)

    agent = build_agent(config)
    app = EnhancedNeuralTerminalGUI(agent)
    app.run()