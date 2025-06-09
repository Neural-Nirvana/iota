#!/usr/bin/env python3
"""
Universal AI OS Launcher
Provides multiple ways to launch AI OS Enhanced:
1. Native terminal detection and launch
2. GUI terminal emulator (tkinter)
3. Web browser interface
4. Direct console mode
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path
import webbrowser
import time

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """Print the application banner"""
    banner = f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════════════════════╗
║                        🚀 AI OS Enhanced - Universal Launcher                ║
║                                                                              ║
║   Your AI assistant with multiple beautiful interface options               ║
╚══════════════════════════════════════════════════════════════════════════════╝{Colors.ENDC}

{Colors.BLUE}System: {Colors.ENDC}{platform.system()} {platform.release()}
{Colors.BLUE}Python: {Colors.ENDC}{sys.version.split()[0]}
{Colors.BLUE}Directory: {Colors.ENDC}{Path.cwd().name}
"""
    print(banner)

def check_requirements():
    """Check if required files exist"""
    issues = []
    
    if not Path('app.py').exists():
        issues.append("❌ app.py not found")
    
    if not Path('config.py').exists():
        issues.append("❌ config.py not found") 
    
    if not Path('requirements.txt').exists():
        issues.append("⚠️  requirements.txt not found")
    
    return issues

def detect_terminal_emulators():
    """Detect available terminal emulators"""
    terminals = []
    system = platform.system().lower()
    
    if system == 'darwin':  # macOS
        candidates = [
            ('/Applications/iTerm.app', 'iTerm2', '⭐ Best'),
            ('/Applications/Utilities/Terminal.app', 'Terminal', 'Built-in'),
            ('/Applications/Hyper.app', 'Hyper', 'Modern')
        ]
        
        for path, name, note in candidates:
            if Path(path).exists():
                terminals.append((name, note))
    
    elif system == 'linux':
        candidates = [
            ('alacritty', 'Alacritty', '⭐ GPU-accelerated'),
            ('kitty', 'Kitty', '⭐ Feature-rich'),
            ('gnome-terminal', 'GNOME Terminal', 'Common'),
            ('konsole', 'Konsole', 'KDE'),
            ('xfce4-terminal', 'XFCE Terminal', 'Lightweight')
        ]
        
        for cmd, name, note in candidates:
            if shutil.which(cmd):
                terminals.append((name, note))
    
    elif system == 'windows':
        candidates = [
            ('wt', 'Windows Terminal', '⭐ Modern'),
            ('powershell', 'PowerShell', 'Common'),
            ('cmd', 'Command Prompt', 'Basic')
        ]
        
        for cmd, name, note in candidates:
            if shutil.which(cmd):
                terminals.append((name, note))
    
    return terminals

def check_gui_support():
    """Check if GUI libraries are available"""
    gui_options = []
    
    # Check tkinter
    try:
        import tkinter
        gui_options.append(('tkinter', 'Tkinter GUI', '✅ Available'))
    except ImportError:
        gui_options.append(('tkinter', 'Tkinter GUI', '❌ Not available'))
    
    # Check web browser
    try:
        import webbrowser
        gui_options.append(('web', 'Web Browser', '✅ Available'))
    except ImportError:
        gui_options.append(('web', 'Web Browser', '❌ Not available'))
    
    return gui_options

def launch_option_1_terminal():
    """Option 1: Try to launch in native terminal"""
    print(f"\n{Colors.CYAN}🚀 Launching AI OS in native terminal...{Colors.ENDC}")
    
    terminals = detect_terminal_emulators()
    if terminals:
        print(f"{Colors.GREEN}✅ Found terminal emulators:{Colors.ENDC}")
        for name, note in terminals[:3]:  # Show first 3
            print(f"   • {name} ({note})")
        
        try:
            subprocess.run([sys.executable, 'enhanced_launcher.py', '--auto'], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                subprocess.run([sys.executable, 'launcher.py'], check=True)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(f"{Colors.WARNING}⚠️  Terminal launcher not available{Colors.ENDC}")
                return False
    else:
        print(f"{Colors.WARNING}⚠️  No suitable terminal emulators detected{Colors.ENDC}")
        return False

def launch_option_2_gui():
    """Option 2: Launch GUI terminal emulator"""
    print(f"\n{Colors.CYAN}🖥️  Launching AI OS GUI terminal...{Colors.ENDC}")
    
    try:
        import tkinter
        subprocess.run([sys.executable, 'gui_terminal.py'], check=True)
        return True
    except ImportError:
        print(f"{Colors.FAIL}❌ Tkinter not available{Colors.ENDC}")
        return False
    except FileNotFoundError:
        print(f"{Colors.WARNING}⚠️  GUI terminal launcher not found{Colors.ENDC}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}❌ GUI launch failed: {e}{Colors.ENDC}")
        return False

def launch_option_3_web():
    """Option 3: Launch web interface"""
    print(f"\n{Colors.CYAN}🌐 Starting AI OS web interface...{Colors.ENDC}")
    
    try:
        # Start web server in background
        web_process = subprocess.Popen([sys.executable, 'web_server.py'])
        
        # Wait a moment for server to start
        time.sleep(2)
        
        # Try to open browser
        try:
            webbrowser.open('http://localhost:8080')
            print(f"{Colors.GREEN}✅ Web interface opened in browser{Colors.ENDC}")
            print(f"{Colors.BLUE}🌍 URL: http://localhost:8080{Colors.ENDC}")
            
            input(f"\n{Colors.WARNING}Press Enter to stop the web server...{Colors.ENDC}")
            web_process.terminate()
            return True
            
        except Exception as e:
            print(f"{Colors.WARNING}⚠️  Could not open browser: {e}{Colors.ENDC}")
            print(f"{Colors.BLUE}🌍 Manually open: http://localhost:8080{Colors.ENDC}")
            
            input(f"\n{Colors.WARNING}Press Enter to stop the web server...{Colors.ENDC}")
            web_process.terminate()
            return True
            
    except FileNotFoundError:
        print(f"{Colors.WARNING}⚠️  Web server launcher not found{Colors.ENDC}")
        
        # Try to serve the HTML file directly
        html_file = Path('web_terminal.html')
        if html_file.exists():
            try:
                webbrowser.open(f'file://{html_file.absolute()}')
                print(f"{Colors.GREEN}✅ Opened local HTML file{Colors.ENDC}")
                return True
            except Exception as e:
                print(f"{Colors.FAIL}❌ Could not open HTML file: {e}{Colors.ENDC}")
        
        return False
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}❌ Web server failed: {e}{Colors.ENDC}")
        return False

def launch_option_4_console():
    """Option 4: Launch in current console"""
    print(f"\n{Colors.CYAN}💻 Launching AI OS in current console...{Colors.ENDC}")
    
    try:
        subprocess.run([sys.executable, 'app.py'], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}❌ Console launch failed: {e}{Colors.ENDC}")
        return False
    except FileNotFoundError:
        print(f"{Colors.FAIL}❌ app.py not found{Colors.ENDC}")
        return False

def show_diagnostics():
    """Show system diagnostics"""
    print(f"\n{Colors.BLUE}🔍 System Diagnostics{Colors.ENDC}")
    print("=" * 50)
    
    # Check requirements
    issues = check_requirements()
    if issues:
        print(f"\n{Colors.WARNING}⚠️  Issues found:{Colors.ENDC}")
        for issue in issues:
            print(f"   {issue}")
    else:
        print(f"\n{Colors.GREEN}✅ All required files present{Colors.ENDC}")
    
    # Check terminals
    terminals = detect_terminal_emulators()
    print(f"\n{Colors.BLUE}🖥️  Available terminals:{Colors.ENDC}")
    if terminals:
        for name, note in terminals:
            print(f"   • {name} ({note})")
    else:
        print(f"   {Colors.WARNING}No terminal emulators detected{Colors.ENDC}")
    
    # Check GUI support
    gui_options = check_gui_support()
    print(f"\n{Colors.BLUE}🖼️  GUI options:{Colors.ENDC}")
    for _, name, status in gui_options:
        print(f"   • {name} {status}")
    
    # Check Python packages
    print(f"\n{Colors.BLUE}📦 Python packages:{Colors.ENDC}")
    packages = ['tkinter', 'webbrowser', 'subprocess', 'pathlib']
    for package in packages:
        try:
            __import__(package)
            print(f"   • {package} {Colors.GREEN}✅ Available{Colors.ENDC}")
        except ImportError:
            print(f"   • {package} {Colors.FAIL}❌ Missing{Colors.ENDC}")

def show_menu():
    """Show the main menu"""
    menu_options = [
        ("1", "🚀 Native Terminal", "Launch in best available terminal emulator"),
        ("2", "🖥️  GUI Terminal", "Launch tkinter-based terminal emulator"),
        ("3", "🌐 Web Interface", "Launch web-based terminal interface"),
        ("4", "💻 Console Mode", "Run directly in current console"),
        ("", "", ""),
        ("d", "🔍 Diagnostics", "Show system information and troubleshooting"),
        ("h", "❓ Help", "Show detailed help information"),
        ("q", "👋 Quit", "Exit the launcher")
    ]
    
    print(f"\n{Colors.BOLD}Choose your AI OS interface:{Colors.ENDC}")
    print("─" * 50)
    
    for key, name, desc in menu_options:
        if key:
            print(f"{Colors.GREEN}{key:>2}{Colors.ENDC}. {Colors.CYAN}{name:<15}{Colors.ENDC} {desc}")
        else:
            print()

def show_help():
    """Show detailed help information"""
    help_text = f"""
{Colors.BOLD}AI OS Enhanced - Interface Options{Colors.ENDC}

{Colors.CYAN}🚀 Native Terminal{Colors.ENDC}
   Automatically detects the best terminal emulator on your system and launches
   AI OS with beautiful theming. Supports Windows Terminal, iTerm2, Alacritty,
   and many others.

{Colors.CYAN}🖥️  GUI Terminal{Colors.ENDC}
   Custom tkinter-based terminal emulator with built-in theming, scrollback,
   and direct integration with the AI OS process. Works on any system with
   Python and tkinter.

{Colors.CYAN}🌐 Web Interface{Colors.ENDC}
   Browser-based terminal interface with modern web technologies. Includes
   theme switching, real-time communication, and responsive design.

{Colors.CYAN}💻 Console Mode{Colors.ENDC}
   Runs AI OS directly in the current terminal/console. No additional UI,
   but works everywhere Python runs.

{Colors.BOLD}Troubleshooting:{Colors.ENDC}
- If no terminals are detected, try GUI or Web interface
- If tkinter is missing, use Web or Console mode
- Use Diagnostics to check for missing components
- Ensure app.py and config.py are in the current directory

{Colors.BOLD}System Requirements:{Colors.ENDC}
- Python 3.7+
- Required files: app.py, config.py
- Optional: tkinter (for GUI), modern terminal emulator
"""
    print(help_text)

def main():
    """Main launcher logic"""
    clear_screen()
    print_banner()
    
    # Quick check for critical issues
    issues = check_requirements()
    if 'app.py not found' in str(issues):
        print(f"{Colors.FAIL}❌ Critical Error: app.py not found{Colors.ENDC}")
        print(f"{Colors.WARNING}Please run this launcher from the AI OS directory{Colors.ENDC}")
        sys.exit(1)
    
    while True:
        show_menu()
        
        try:
            choice = input(f"\n{Colors.BOLD}Select option (1-4, d, h, q): {Colors.ENDC}").strip().lower()
            
            if choice == 'q' or choice == 'quit':
                print(f"\n{Colors.CYAN}👋 Thanks for using AI OS Enhanced!{Colors.ENDC}")
                break
            
            elif choice == '1':
                if launch_option_1_terminal():
                    break
                input(f"\n{Colors.WARNING}Press Enter to return to menu...{Colors.ENDC}")
            
            elif choice == '2':
                if launch_option_2_gui():
                    break
                input(f"\n{Colors.WARNING}Press Enter to return to menu...{Colors.ENDC}")
            
            elif choice == '3':
                if launch_option_3_web():
                    break
                input(f"\n{Colors.WARNING}Press Enter to return to menu...{Colors.ENDC}")
            
            elif choice == '4':
                if launch_option_4_console():
                    break
                input(f"\n{Colors.WARNING}Press Enter to return to menu...{Colors.ENDC}")
            
            elif choice == 'd' or choice == 'diagnostics':
                show_diagnostics()
                input(f"\n{Colors.WARNING}Press Enter to return to menu...{Colors.ENDC}")
            
            elif choice == 'h' or choice == 'help':
                show_help()
                input(f"\n{Colors.WARNING}Press Enter to return to menu...{Colors.ENDC}")
            
            else:
                print(f"{Colors.WARNING}⚠️  Invalid option. Please try again.{Colors.ENDC}")
                time.sleep(1)
        
        except KeyboardInterrupt:
            print(f"\n\n{Colors.CYAN}👋 Goodbye!{Colors.ENDC}")
            break
        except Exception as e:
            print(f"{Colors.FAIL}❌ Unexpected error: {e}{Colors.ENDC}")
            input(f"\n{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")

if __name__ == "__main__":
    main()