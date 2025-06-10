from textual.app import App, ComposeResult   # ← add this line
from textual_terminal import Terminal

class TerminalApp(App):
    def compose(self) -> ComposeResult:
        yield Terminal(command="htop", id="terminal_htop")
        yield Terminal(command="bash", id="terminal_bash")

    def on_ready(self) -> None:
        terminal_htop: Terminal = self.query_one("#terminal_htop")
        terminal_htop.start()

        terminal_bash: Terminal = self.query_one("#terminal_bash")
        terminal_bash.start()
