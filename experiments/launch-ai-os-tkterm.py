# launch_ai_os.py - Easy launcher for AI OS Enhanced
import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox

def check_dependencies():
    """Check and install required dependencies"""
    required_packages = [
        "tkterm",
        "rich", 
        "agno",
        # Add other required packages here
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Missing packages: {', '.join(missing_packages)}")
        print("Installing missing packages...")
        
        for package in missing_packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"✅ Installed {package}")
            except subprocess.CalledProcessError:
                print(f"❌ Failed to install {package}")
                return False
    
    return True

def check_config_files():
    """Check if required config files exist"""
    required_files = ["config.py", "app.py"]
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"Missing files: {', '.join(missing_files)}")
        return False
    
    return True

def create_desktop_shortcut():
    """Create desktop shortcut (Windows)"""
    if sys.platform == "win32":
        try:
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            path = os.path.join(desktop, "AI OS Enhanced.lnk")
            target = os.path.join(os.getcwd(), "launch_ai_os.py")
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(path)
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = f'"{target}"'
            shortcut.WorkingDirectory = os.getcwd()
            shortcut.IconLocation = target
            shortcut.save()
            
            print("✅ Desktop shortcut created")
        except ImportError:
            print("⚠️ winshell not available for desktop shortcut")
        except Exception as e:
            print(f"⚠️ Could not create desktop shortcut: {e}")

def show_launcher_gui():
    """Show a simple launcher GUI"""
    root = tk.Tk()
    root.title("AI OS Enhanced Launcher")
    root.geometry("500x400")
    root.configure(bg="#0f0f23")
    
    # Title
    title_label = tk.Label(
        root,
        text="🌟 AI OS Enhanced v2.0 🌟",
        bg="#0f0f23",
        fg="#00ff41",
        font=("Arial", 16, "bold")
    )
    title_label.pack(pady=20)
    
    # Subtitle
    subtitle_label = tk.Label(
        root,
        text="Neural Terminal Interface",
        bg="#0f0f23",
        fg="#00aaff",
        font=("Arial", 12)
    )
    subtitle_label.pack(pady=5)
    
    # Status frame
    status_frame = tk.Frame(root, bg="#0f0f23")
    status_frame.pack(pady=20, padx=20, fill="x")
    
    def update_status(message, color="#00ff41"):
        status_label.config(text=message, fg=color)
        root.update()
    
    status_label = tk.Label(
        status_frame,
        text="🔄 Checking dependencies...",
        bg="#0f0f23",
        fg="#ffb000",
        font=("Arial", 10)
    )
    status_label.pack()
    
    # Buttons frame
    buttons_frame = tk.Frame(root, bg="#0f0f23")
    buttons_frame.pack(pady=20)
    
    def launch_terminal():
        """Launch the terminal interface"""
        update_status("🚀 Launching AI OS Enhanced...", "#00aaff")
        try:
            # Import and run the GUI
            from tktermapp import main as gui_main
            root.destroy()
            gui_main()
        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to launch AI OS:\n{str(e)}")
            update_status(f"❌ Launch failed: {str(e)[:30]}", "#ff4444")
    
    def launch_cli():
        """Launch the CLI version"""
        update_status("🚀 Launching CLI version...", "#00aaff")
        try:
            from app import main as cli_main
            root.destroy()
            cli_main()
        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to launch CLI:\n{str(e)}")
            update_status(f"❌ Launch failed: {str(e)[:30]}", "#ff4444")
    
    def check_system():
        """Check system and dependencies"""
        update_status("🔍 Checking system...", "#ffb000")
        
        # Check dependencies
        if not check_dependencies():
            update_status("❌ Dependency check failed", "#ff4444")
            return
        
        # Check config files
        if not check_config_files():
            update_status("❌ Missing config files", "#ff4444")
            return
        
        update_status("✅ System ready", "#00ff41")
        
        # Enable launch buttons
        terminal_btn.config(state="normal")
        cli_btn.config(state="normal")
    
    # Create buttons (initially disabled)
    terminal_btn = tk.Button(
        buttons_frame,
        text="🖥️ Launch Terminal GUI",
        command=launch_terminal,
        bg="#1a1a3a",
        fg="#00ff41",
        font=("Arial", 12),
        padx=20,
        pady=10,
        state="disabled"
    )
    terminal_btn.pack(pady=5)
    
    cli_btn = tk.Button(
        buttons_frame,
        text="💻 Launch CLI Version", 
        command=launch_cli,
        bg="#1a1a3a",
        fg="#00aaff",
        font=("Arial", 12),
        padx=20,
        pady=10,
        state="disabled"
    )
    cli_btn.pack(pady=5)
    
    check_btn = tk.Button(
        buttons_frame,
        text="🔍 Check System",
        command=check_system,
        bg="#1a1a3a",
        fg="#ffb000",
        font=("Arial", 12),
        padx=20,
        pady=10
    )
    check_btn.pack(pady=5)
    
    # Info text
    info_text = """
🤖 Multi-Provider AI Support
🎨 6 Nostalgic Terminal Themes
⚡ Real-time Processing
🔧 System Integration

Choose your interface:
• Terminal GUI: Modern nostalgic look
• CLI: Traditional command line
"""
    
    info_label = tk.Label(
        root,
        text=info_text,
        bg="#0f0f23",
        fg="#888888",
        font=("Arial", 9),
        justify="left"
    )
    info_label.pack(pady=10)
    
    # Auto-check on startup
    root.after(1000, check_system)
    
    root.mainloop()

def main():
    """Main launcher function"""
    print("🌟 AI OS Enhanced Launcher 🌟")
    print("=" * 40)
    
    # Command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--gui":
            try:
                from ai_os_gui import main as gui_main
                gui_main()
            except Exception as e:
                print(f"❌ GUI launch failed: {e}")
        elif sys.argv[1] == "--cli":
            try:
                from app import main as cli_main
                cli_main()
            except Exception as e:
                print(f"❌ CLI launch failed: {e}")
        elif sys.argv[1] == "--check":
            print("🔍 Checking dependencies...")
            if check_dependencies():
                print("✅ All dependencies satisfied")
            else:
                print("❌ Missing dependencies")
            
            print("🔍 Checking config files...")
            if check_config_files():
                print("✅ All config files present")
            else:
                print("❌ Missing config files")
        else:
            print("Usage: python launch_ai_os.py [--gui|--cli|--check]")
    else:
        # Show launcher GUI
        show_launcher_gui()

if __name__ == "__main__":
    main()