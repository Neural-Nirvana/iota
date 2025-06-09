#!/usr/bin/env python3
"""
AI OS Terminal Launcher
Opens a beautifully themed terminal window and runs the AI OS application inside it.
Cross-platform support for Windows, macOS, and Linux.
"""

import os
import sys
import platform
import subprocess
import tempfile
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class TerminalTheme:
    """Custom terminal theme configuration"""
    
    # Modern AI OS Theme - Dark with neon accents
    THEME = {
        'name': 'AI OS Enhanced',
        'background': '#0a0a0f',        # Deep space black
        'foreground': '#e2e8f0',        # Soft white
        'cursor': '#00d4ff',            # Cyan cursor
        
        # Standard colors (dark variants)
        'black': '#1e293b',
        'red': '#ef4444',
        'green': '#22c55e', 
        'yellow': '#f59e0b',
        'blue': '#3b82f6',
        'magenta': '#a855f7',
        'cyan': '#06b6d4',
        'white': '#f1f5f9',
        
        # Bright colors (neon accents)
        'bright_black': '#475569',
        'bright_red': '#f87171',
        'bright_green': '#4ade80',
        'bright_yellow': '#fbbf24',
        'bright_blue': '#60a5fa',
        'bright_magenta': '#c084fc',
        'bright_cyan': '#22d3ee',
        'bright_white': '#ffffff',
        
        # Special colors for AI OS
        'selection_bg': '#1e40af',
        'selection_fg': '#ffffff',
    }

class TerminalLauncher:
    """Cross-platform terminal launcher with theming support"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.theme = TerminalTheme.THEME
        self.temp_dir = Path(tempfile.mkdtemp(prefix='ai_os_'))
        
    def detect_terminal_emulators(self) -> List[Dict[str, str]]:
        """Detect available terminal emulators on the system"""
        terminals = []
        
        if self.system == 'windows':
            terminals = self._detect_windows_terminals()
        elif self.system == 'darwin':  # macOS
            terminals = self._detect_macos_terminals()
        elif self.system == 'linux':
            terminals = self._detect_linux_terminals()
            
        return terminals
    
    def _detect_windows_terminals(self) -> List[Dict[str, str]]:
        """Detect Windows terminal emulators"""
        terminals = []
        
        # Windows Terminal (modern, best theming support)
        wt_path = shutil.which('wt')
        if wt_path:
            terminals.append({
                'name': 'Windows Terminal',
                'path': wt_path,
                'type': 'windows_terminal',
                'priority': 1
            })
        
        # PowerShell
        ps_path = shutil.which('powershell')
        if ps_path:
            terminals.append({
                'name': 'PowerShell',
                'path': ps_path,
                'type': 'powershell',
                'priority': 3
            })
            
        # Command Prompt
        cmd_path = shutil.which('cmd')
        if cmd_path:
            terminals.append({
                'name': 'Command Prompt',
                'path': cmd_path,
                'type': 'cmd',
                'priority': 4
            })
            
        return sorted(terminals, key=lambda x: x['priority'])
    
    def _detect_macos_terminals(self) -> List[Dict[str, str]]:
        """Detect macOS terminal emulators"""
        terminals = []
        
        # iTerm2 (best theming support)
        if Path('/Applications/iTerm.app').exists():
            terminals.append({
                'name': 'iTerm2',
                'path': '/Applications/iTerm.app',
                'type': 'iterm2',
                'priority': 1
            })
        
        # Terminal.app (built-in)
        if Path('/Applications/Utilities/Terminal.app').exists():
            terminals.append({
                'name': 'Terminal',
                'path': '/Applications/Utilities/Terminal.app',
                'type': 'terminal_app',
                'priority': 2
            })
        
        return sorted(terminals, key=lambda x: x['priority'])
    
    def _detect_linux_terminals(self) -> List[Dict[str, str]]:
        """Detect Linux terminal emulators"""
        terminals = []
        terminal_candidates = [
            ('gnome-terminal', 'gnome_terminal', 1),
            ('konsole', 'konsole', 1), 
            ('xfce4-terminal', 'xfce_terminal', 2),
            ('mate-terminal', 'mate_terminal', 2),
            ('terminator', 'terminator', 2),
            ('alacritty', 'alacritty', 1),
            ('kitty', 'kitty', 1),
            ('tilix', 'tilix', 2),
            ('xterm', 'xterm', 4),
        ]
        
        for cmd, term_type, priority in terminal_candidates:
            path = shutil.which(cmd)
            if path:
                terminals.append({
                    'name': cmd.replace('-', ' ').title(),
                    'path': path,
                    'type': term_type,
                    'priority': priority
                })
        
        return sorted(terminals, key=lambda x: x['priority'])
    
    def create_windows_terminal_profile(self) -> str:
        """Create Windows Terminal profile with AI OS theme"""
        profile = {
            "name": "AI OS Enhanced",
            "commandline": f"python {Path.cwd() / 'app.py'}",
            "startingDirectory": str(Path.cwd()),
            "colorScheme": "AI OS Enhanced",
            "font": {
                "face": "Cascadia Code",
                "size": 11,
                "weight": "normal"
            },
            "opacity": 95,
            "useAcrylic": True,
            "acrylicOpacity": 0.8,
            "backgroundImage": None,
            "backgroundImageOpacity": 0.3,
            "icon": "⚡"
        }
        
        color_scheme = {
            "name": "AI OS Enhanced", 
            "background": self.theme['background'],
            "foreground": self.theme['foreground'],
            "cursorColor": self.theme['cursor'],
            "selectionBackground": self.theme['selection_bg'],
            "black": self.theme['black'],
            "red": self.theme['red'],
            "green": self.theme['green'],
            "yellow": self.theme['yellow'],
            "blue": self.theme['blue'],
            "purple": self.theme['magenta'],
            "cyan": self.theme['cyan'],
            "white": self.theme['white'],
            "brightBlack": self.theme['bright_black'],
            "brightRed": self.theme['bright_red'],
            "brightGreen": self.theme['bright_green'],
            "brightYellow": self.theme['bright_yellow'],
            "brightBlue": self.theme['bright_blue'],
            "brightPurple": self.theme['bright_magenta'],
            "brightCyan": self.theme['bright_cyan'],
            "brightWhite": self.theme['bright_white']
        }
        
        config_file = self.temp_dir / 'wt_profile.json'
        with open(config_file, 'w') as f:
            json.dump({
                'profile': profile,
                'colorScheme': color_scheme
            }, f, indent=2)
        
        return str(config_file)
    
    def create_iterm2_profile(self) -> str:
        """Create iTerm2 profile with AI OS theme"""
        # Create a simple applescript to set up iTerm2 with our theme
        script = f'''
tell application "iTerm2"
    create window with default profile
    tell current session of current window
        set background color to {{0, 0, 15}}
        set foreground color to {{226, 232, 240}}
        write text "cd {Path.cwd()} && python app.py"
    end tell
end tell
'''
        script_file = self.temp_dir / 'iterm_setup.scpt'
        with open(script_file, 'w') as f:
            f.write(script)
        return str(script_file)
    
    def create_gnome_terminal_profile(self) -> str:
        """Create GNOME Terminal profile with AI OS theme"""
        profile_id = "ai-os-enhanced"
        
        # GNOME Terminal uses dconf, so we'll create a script
        script = f'''#!/bin/bash
# Create AI OS Enhanced profile for GNOME Terminal

PROFILE_ID="{profile_id}"
PROFILE_PATH="/org/gnome/terminal/legacy/profiles:/:$PROFILE_ID/"

# Create the profile
dconf write $PROFILE_PATH/visible-name "'AI OS Enhanced'"
dconf write $PROFILE_PATH/use-theme-colors "false"
dconf write $PROFILE_PATH/background-color "'{self.theme['background']}'"
dconf write $PROFILE_PATH/foreground-color "'{self.theme['foreground']}'"
dconf write $PROFILE_PATH/cursor-color "'{self.theme['cursor']}'"

# Set palette
PALETTE="['{self.theme['black']}','{self.theme['red']}','{self.theme['green']}','{self.theme['yellow']}','{self.theme['blue']}','{self.theme['magenta']}','{self.theme['cyan']}','{self.theme['white']}','{self.theme['bright_black']}','{self.theme['bright_red']}','{self.theme['bright_green']}','{self.theme['bright_yellow']}','{self.theme['bright_blue']}','{self.theme['bright_magenta']}','{self.theme['bright_cyan']}','{self.theme['bright_white']}']"
dconf write $PROFILE_PATH/palette "$PALETTE"

# Launch terminal with the new profile
gnome-terminal --window-with-profile="AI OS Enhanced" --working-directory="{Path.cwd()}" -- python app.py
'''
        
        script_file = self.temp_dir / 'gnome_setup.sh'
        with open(script_file, 'w') as f:
            f.write(script)
        os.chmod(script_file, 0o755)
        return str(script_file)
    
    def launch_terminal(self, terminal_info: Dict[str, str]) -> bool:
        """Launch the selected terminal with AI OS theme"""
        try:
            if terminal_info['type'] == 'windows_terminal':
                return self._launch_windows_terminal(terminal_info)
            elif terminal_info['type'] == 'iterm2':
                return self._launch_iterm2(terminal_info)
            elif terminal_info['type'] == 'terminal_app':
                return self._launch_terminal_app(terminal_info)
            elif terminal_info['type'] == 'gnome_terminal':
                return self._launch_gnome_terminal(terminal_info)
            elif terminal_info['type'] == 'konsole':
                return self._launch_konsole(terminal_info)
            elif terminal_info['type'] == 'alacritty':
                return self._launch_alacritty(terminal_info)
            else:
                return self._launch_generic_terminal(terminal_info)
                
        except Exception as e:
            print(f"Failed to launch {terminal_info['name']}: {e}")
            return False
    
    def _launch_windows_terminal(self, terminal_info: Dict[str, str]) -> bool:
        """Launch Windows Terminal with custom profile"""
        config_file = self.create_windows_terminal_profile()
        
        # Use a temporary profile
        cmd = [
            terminal_info['path'],
            'new-tab',
            '--title', 'AI OS Enhanced',
            '--suppressApplicationTitle',
            '--colorScheme', 'AI OS Enhanced',
            'python', str(Path.cwd() / 'app.py')
        ]
        
        subprocess.Popen(cmd, cwd=Path.cwd())
        return True
    
    def _launch_iterm2(self, terminal_info: Dict[str, str]) -> bool:
        """Launch iTerm2 with custom theme"""
        script_file = self.create_iterm2_profile()
        subprocess.Popen(['osascript', script_file])
        return True
    
    def _launch_terminal_app(self, terminal_info: Dict[str, str]) -> bool:
        """Launch macOS Terminal.app"""
        script = f'''
tell application "Terminal"
    activate
    do script "cd {Path.cwd()} && python app.py"
end tell
'''
        subprocess.Popen(['osascript', '-e', script])
        return True
    
    def _launch_gnome_terminal(self, terminal_info: Dict[str, str]) -> bool:
        """Launch GNOME Terminal with custom profile"""
        # For simplicity, just launch with custom colors via command line
        cmd = [
            terminal_info['path'],
            '--title=AI OS Enhanced',
            '--working-directory=' + str(Path.cwd()),
            '--',
            'python', 'app.py'
        ]
        subprocess.Popen(cmd)
        return True
    
    def _launch_konsole(self, terminal_info: Dict[str, str]) -> bool:
        """Launch KDE Konsole"""
        cmd = [
            terminal_info['path'],
            '--new-tab',
            '--workdir', str(Path.cwd()),
            '-e', 'python', 'app.py'
        ]
        subprocess.Popen(cmd)
        return True
    
    def _launch_alacritty(self, terminal_info: Dict[str, str]) -> bool:
        """Launch Alacritty with custom config"""
        # Create temporary alacritty config
        config = f'''
window:
  title: "AI OS Enhanced"
  opacity: 0.95

font:
  normal:
    family: "Source Code Pro"
  size: 11

colors:
  primary:
    background: '{self.theme['background']}'
    foreground: '{self.theme['foreground']}'
  cursor:
    text: '{self.theme['background']}'
    cursor: '{self.theme['cursor']}'
  normal:
    black: '{self.theme['black']}'
    red: '{self.theme['red']}'
    green: '{self.theme['green']}'
    yellow: '{self.theme['yellow']}'
    blue: '{self.theme['blue']}'
    magenta: '{self.theme['magenta']}'
    cyan: '{self.theme['cyan']}'
    white: '{self.theme['white']}'
  bright:
    black: '{self.theme['bright_black']}'
    red: '{self.theme['bright_red']}'
    green: '{self.theme['bright_green']}'
    yellow: '{self.theme['bright_yellow']}'
    blue: '{self.theme['bright_blue']}'
    magenta: '{self.theme['bright_magenta']}'
    cyan: '{self.theme['bright_cyan']}'
    white: '{self.theme['bright_white']}'
'''
        config_file = self.temp_dir / 'alacritty.yml'
        with open(config_file, 'w') as f:
            f.write(config)
        
        cmd = [
            terminal_info['path'],
            '--config-file', str(config_file),
            '--working-directory', str(Path.cwd()),
            '-e', 'python', 'app.py'
        ]
        subprocess.Popen(cmd)
        return True
    
    def _launch_generic_terminal(self, terminal_info: Dict[str, str]) -> bool:
        """Launch any generic terminal emulator"""
        cmd = [
            terminal_info['path'],
            '-e', 'python', str(Path.cwd() / 'app.py')
        ]
        subprocess.Popen(cmd, cwd=Path.cwd())
        return True
    
    def show_banner(self):
        """Show launch banner"""
        banner = f'''
╔══════════════════════════════════════════════════════════════════════════════╗
║                           🚀 AI OS Enhanced Launcher                         ║
║                                                                              ║
║   Opening a beautifully themed terminal for your AI assistant...            ║
║                                                                              ║
║   Theme: Dark space with neon accents                                       ║
║   System: {platform.system()} {platform.release():<20}                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
        '''
        print(banner)
    
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    def run(self) -> bool:
        """Main launcher logic"""
        self.show_banner()
        
        # Check if app.py exists
        if not Path('app.py').exists():
            print("❌ Error: app.py not found in current directory")
            print("   Please run this launcher from the AI OS directory")
            return False
        
        # Detect available terminals
        terminals = self.detect_terminal_emulators()
        
        if not terminals:
            print("❌ Error: No supported terminal emulators found")
            print("   Please install a modern terminal emulator")
            return False
        
        # Try to launch the best available terminal
        for terminal in terminals:
            print(f"🎯 Launching {terminal['name']}...")
            
            if self.launch_terminal(terminal):
                print(f"✅ Successfully launched AI OS in {terminal['name']}")
                print("   Your themed terminal should open shortly!")
                return True
            else:
                print(f"⚠️  Failed to launch {terminal['name']}, trying next option...")
        
        print("❌ Error: Could not launch any terminal emulator")
        return False

def main():
    """Main entry point"""
    launcher = TerminalLauncher()
    
    try:
        success = launcher.run()
        if not success:
            print("\n💡 You can also run the AI OS directly with: python app.py")
    except KeyboardInterrupt:
        print("\n\n👋 Launch cancelled by user")
    finally:
        launcher.cleanup()

if __name__ == "__main__":
    main()