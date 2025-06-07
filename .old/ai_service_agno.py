"""
Proper Agno Tools Implementation for Goal-Oriented IoT Control
This implements real AI agents with proper tools following Agno patterns
"""

import os
import json
import subprocess
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Agno imports
from agno.agent import Agent
from agno.models.together import Together
from agno.tools import Toolkit

# Custom IoT Tools following Agno patterns
class SystemTools(Toolkit):
    """System information and monitoring tools"""
    
    def get_system_info(self) -> str:
        """Get comprehensive system information"""
        try:
            result = subprocess.run("uname -a && uptime", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"System Information:\n{result.stdout}"
            else:
                return f"Error getting system info: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_disk_usage(self) -> str:
        """Check disk usage and available space"""
        try:
            result = subprocess.run("df -h", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"Disk Usage:\n{result.stdout}"
            else:
                return f"Error getting disk usage: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_memory_info(self) -> str:
        """Check memory usage and availability"""
        try:
            result = subprocess.run("free -h", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"Memory Information:\n{result.stdout}"
            else:
                return f"Error getting memory info: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_process_list(self) -> str:
        """Get list of running processes"""
        try:
            result = subprocess.run("ps aux | head -20", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"Running Processes:\n{result.stdout}"
            else:
                return f"Error getting process list: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_cpu_info(self) -> str:
        """Get CPU information and usage"""
        try:
            result = subprocess.run("lscpu | head -15", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"CPU Information:\n{result.stdout}"
            else:
                return f"Error getting CPU info: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

class FileSystemTools(Toolkit):
    """File system operations and directory listing tools"""
    
    def list_directory(self, path: str = ".") -> str:
        """List contents of a directory with detailed information"""
        try:
            result = subprocess.run(f"ls -la {path}", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"Directory listing for {path}:\n{result.stdout}"
            else:
                return f"Error listing directory: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_current_directory(self) -> str:
        """Get the current working directory"""
        try:
            result = subprocess.run("pwd", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"Current directory: {result.stdout.strip()}"
            else:
                return f"Error getting current directory: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def find_files(self, pattern: str, path: str = ".") -> str:
        """Find files matching a pattern"""
        try:
            result = subprocess.run(f"find {path} -name '{pattern}' -type f | head -20", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"Files matching '{pattern}':\n{result.stdout}"
            else:
                return f"Error finding files: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_file_info(self, filename: str) -> str:
        """Get detailed information about a file"""
        try:
            result = subprocess.run(f"ls -la {filename} && file {filename}", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"File information for {filename}:\n{result.stdout}"
            else:
                return f"Error getting file info: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

class NetworkTools(Toolkit):
    """Network configuration and connectivity tools"""
    
    def get_network_interfaces(self) -> str:
        """Get network interface configuration"""
        try:
            result = subprocess.run("ip addr show", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"Network Interfaces:\n{result.stdout}"
            else:
                return f"Error getting network interfaces: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def check_connectivity(self, host: str = "8.8.8.8") -> str:
        """Check network connectivity by pinging a host"""
        try:
            result = subprocess.run(f"ping -c 3 {host}", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"Connectivity test to {host}:\n{result.stdout}"
            else:
                return f"Connectivity test failed: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_network_connections(self) -> str:
        """Get active network connections"""
        try:
            result = subprocess.run("netstat -tuln | head -15", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"Active Network Connections:\n{result.stdout}"
            else:
                return f"Error getting connections: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

class DeviceTools(Toolkit):
    """Hardware device detection and management tools"""
    
    def __init__(self, device_manager=None):
        super().__init__()
        self.device_manager = device_manager
    
    def scan_usb_devices(self) -> str:
        """Scan for USB devices"""
        try:
            result = subprocess.run("lsusb", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"USB Devices:\n{result.stdout}"
            else:
                return f"Error scanning USB devices: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def scan_pci_devices(self) -> str:
        """Scan for PCI devices"""
        try:
            result = subprocess.run("lspci | head -15", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"PCI Devices:\n{result.stdout}"
            else:
                return f"Error scanning PCI devices: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def scan_serial_ports(self) -> str:
        """Scan for available serial ports/IoT devices"""
        try:
            if self.device_manager:
                devices = self.device_manager.scan_devices()
                if devices:
                    result = "Available Serial Ports/IoT Devices:\n"
                    for device in devices:
                        result += f"- {device['port']}: {device['description']}\n"
                    return result
                else:
                    return "No serial ports/IoT devices found"
            else:
                return "Device manager not available"
        except Exception as e:
            return f"Error scanning serial ports: {str(e)}"
    
    def connect_to_device(self, port: str) -> str:
        """Connect to a specific IoT device"""
        try:
            if self.device_manager:
                success, message = self.device_manager.connect_device(port)
                if success:
                    return f"Successfully connected to {port}: {message}"
                else:
                    return f"Failed to connect to {port}: {message}"
            else:
                return "Device manager not available"
        except Exception as e:
            return f"Error connecting to device: {str(e)}"
    
    def get_block_devices(self) -> str:
        """Get information about block devices"""
        try:
            result = subprocess.run("lsblk", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"Block Devices:\n{result.stdout}"
            else:
                return f"Error getting block devices: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

class TerminalTools(Toolkit):
    """Direct terminal command execution tools"""
    
    def __init__(self, terminal_manager=None):
        super().__init__()
        self.terminal_manager = terminal_manager
    
    def execute_safe_command(self, command: str) -> str:
        """Execute a safe terminal command"""
        # List of safe commands
        safe_commands = [
            "ls", "pwd", "whoami", "date", "uptime", "free", "df", "ps", 
            "lsusb", "lspci", "lsblk", "ip", "netstat", "ping", "find", 
            "grep", "cat", "head", "tail", "wc", "sort", "uniq", "which",
            "uname", "lscpu", "file", "stat", "du", "mount"
        ]
        
        # Check if command starts with a safe command
        cmd_start = command.split()[0] if command.split() else ""
        
        if cmd_start not in safe_commands:
            return f"Command '{cmd_start}' is not in the safe commands list. Safe commands: {', '.join(safe_commands)}"
        
        try:
            if self.terminal_manager:
                result = self.terminal_manager.execute_command(command)
                output = f"Command: {command}\n"
                if result['stdout']:
                    output += f"Output:\n{result['stdout']}\n"
                if result['stderr']:
                    output += f"Errors:\n{result['stderr']}\n"
                output += f"Exit Code: {result['return_code']}"
                return output
            else:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
                output = f"Command: {command}\n"
                if result.stdout:
                    output += f"Output:\n{result.stdout}\n"
                if result.stderr:
                    output += f"Errors:\n{result.stderr}\n"
                output += f"Exit Code: {result.returncode}"
                return output
        except Exception as e:
            return f"Error executing command: {str(e)}"

class WorkflowTools(Toolkit):
    """Tools for managing the AI workflow and user permissions"""
    
    def __init__(self, socketio=None):
        super().__init__()
        self.socketio = socketio
        self.pending_permissions = {}
    
    def request_permission(self, command: str, explanation: str, risk_level: str = "low") -> str:
        """Request permission from user to execute a command"""
        permission_id = f"perm_{int(datetime.now().timestamp())}"
        
        permission_data = {
            "permission_id": permission_id,
            "command": command,
            "explanation": explanation,
            "risk_level": risk_level,
            "timestamp": datetime.now().isoformat()
        }
        
        self.pending_permissions[permission_id] = permission_data
        
        if self.socketio:
            self.socketio.emit('ai_permission_request', permission_data)
        
        return f"Permission requested for command: {command} (ID: {permission_id})"
    
    def check_permission_status(self, permission_id: str) -> str:
        """Check the status of a permission request"""
        if permission_id in self.pending_permissions:
            return f"Permission {permission_id} is still pending"
        else:
            return f"Permission {permission_id} not found or already processed"

# Main Agno AI Service with proper tool integration
class AgnoAIService:
    """Real AI service using Agno framework with proper tools"""
    
    def __init__(self, device_manager=None, terminal_manager=None, socketio=None, together_api_key=None):
        self.device_manager = device_manager
        self.terminal_manager = terminal_manager
        self.socketio = socketio
        
        # Set up Together AI
        if together_api_key:
            os.environ['TOGETHER_API_KEY'] = together_api_key
        
        # Initialize tools
        self.system_tools = SystemTools()
        self.filesystem_tools = FileSystemTools()
        self.network_tools = NetworkTools()
        self.device_tools = DeviceTools(device_manager)
        self.terminal_tools = TerminalTools(terminal_manager)
        self.workflow_tools = WorkflowTools(socketio)
        
        # Initialize AI agents
        self._setup_agents()
    
    def _setup_agents(self):
        """Set up specialized AI agents with proper tools"""
        
        # System Information Agent
        self.system_agent = Agent(
            name="System Information Specialist",
            model=Together(id="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
            tools=[self.system_tools, self.workflow_tools],
            instructions=[
                "You are a system information specialist.",
                "Use the available tools to gather system information when users ask.",
                "Always request permission before executing commands that might affect the system.",
                "Provide clear, helpful explanations of what you're doing.",
                "Focus on system monitoring, resource usage, and status checks."
            ],
            show_tool_calls=True,
            markdown=True
        )
        
        # File System Agent
        self.filesystem_agent = Agent(
            name="File System Navigator",
            model=Together(id="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
            tools=[self.filesystem_tools, self.workflow_tools],
            instructions=[
                "You are a file system navigation expert.",
                "Help users explore directories, find files, and get file information.",
                "Use the appropriate tools to list directories, find files, and get file details.",
                "Always explain what you're looking for and what you found.",
                "Be helpful in organizing and understanding file structures."
            ],
            show_tool_calls=True,
            markdown=True
        )
        
        # Network Specialist Agent
        self.network_agent = Agent(
            name="Network Specialist",
            model=Together(id="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
            tools=[self.network_tools, self.workflow_tools],
            instructions=[
                "You are a network connectivity and configuration specialist.",
                "Help users check network status, interfaces, and connectivity.",
                "Use network tools to diagnose connection issues.",
                "Explain network configurations in user-friendly terms.",
                "Test connectivity and report results clearly."
            ],
            show_tool_calls=True,
            markdown=True
        )
        
        # Device Management Agent
        self.device_agent = Agent(
            name="Device Manager",
            model=Together(id="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
            tools=[self.device_tools, self.workflow_tools],
            instructions=[
                "You are a hardware device management specialist.",
                "Help users discover, connect to, and manage IoT devices and hardware.",
                "Scan for USB, PCI, serial ports, and other connected devices.",
                "Assist with device connections and troubleshooting.",
                "Provide detailed information about detected hardware."
            ],
            show_tool_calls=True,
            markdown=True
        )
        
        # Terminal Command Agent
        self.terminal_agent = Agent(
            name="Terminal Command Specialist",
            model=Together(id="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
            tools=[self.terminal_tools, self.workflow_tools],
            instructions=[
                "You are a terminal command execution specialist.",
                "Execute safe terminal commands to help users achieve their goals.",
                "Always request permission before executing commands.",
                "Only use safe, read-only commands unless explicitly authorized.",
                "Explain what each command does and what the output means.",
                "Focus on information gathering and system exploration."
            ],
            show_tool_calls=True,
            markdown=True
        )
        
        # Main Coordinator Agent
        self.coordinator = Agent(
            name="IoT Control Coordinator",
            team=[self.system_agent, self.filesystem_agent, self.network_agent, self.device_agent, self.terminal_agent],
            model=Together(id="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
            instructions=[
                "You are the main coordinator for IoT control and system management.",
                "Route user requests to the appropriate specialist agent.",
                "Coordinate between agents to achieve complex goals.",
                "Always prioritize user safety and system security.",
                "Provide comprehensive responses by leveraging specialist expertise.",
                "Follow this workflow:",
                "1. Understand the user's goal",
                "2. Determine which specialist(s) can help",
                "3. Route the request appropriately", 
                "4. Coordinate responses if multiple agents are needed",
                "5. Provide a clear summary of what was accomplished"
            ],
            show_tool_calls=True,
            markdown=True
        )
    
    async def process_user_goal(self, goal: str, context: Dict = None) -> Dict[str, Any]:
        """Process user goal using proper AI agents and tools"""
        try:
            # Add context about available tools and current system state
            enhanced_prompt = f"""
            User Goal: {goal}
            
            Context: {json.dumps(context or {}, indent=2)}
            
            Please help the user achieve their goal by:
            1. Understanding what they want to accomplish
            2. Using the appropriate tools to gather information or perform actions
            3. Requesting permission for any potentially risky operations
            4. Providing clear explanations of what you're doing
            5. Reporting results in a helpful format
            
            Available specialist agents:
            - System Information: For system status, resource usage, processes
            - File System: For directory listings, file operations, finding files
            - Network: For connectivity, interface status, network diagnostics
            - Device Management: For IoT devices, USB, PCI, hardware detection
            - Terminal Commands: For direct command execution when needed
            
            Choose the right approach and use the tools to help the user.
            """
            
            # Use the coordinator to process the request
            response = self.coordinator.run(enhanced_prompt)
            
            return {
                "status": "success",
                "response": response.content if hasattr(response, 'content') else str(response),
                "agent_used": "coordinator",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "message": f"AI processing failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def handle_permission_response(self, permission_id: str, granted: bool, modified_command: str = None):
        """Handle user response to permission request"""
        if permission_id in self.workflow_tools.pending_permissions:
            permission_data = self.workflow_tools.pending_permissions[permission_id]
            
            if granted:
                command = modified_command or permission_data["command"]
                # Execute the approved command
                result = self.terminal_tools.execute_safe_command(command)
                
                # Remove from pending
                del self.workflow_tools.pending_permissions[permission_id]
                
                return {
                    "status": "executed",
                    "result": result,
                    "command": command
                }
            else:
                # Remove from pending
                del self.workflow_tools.pending_permissions[permission_id]
                
                return {
                    "status": "denied",
                    "message": "User denied permission to execute command"
                }
        else:
            return {
                "status": "error",
                "message": "Permission request not found"
            }
    
    def get_available_tools(self) -> Dict[str, List[str]]:
        """Get list of available tools for each agent"""
        return {
            "system_tools": ["get_system_info", "get_disk_usage", "get_memory_info", "get_process_list", "get_cpu_info"],
            "filesystem_tools": ["list_directory", "get_current_directory", "find_files", "get_file_info"],
            "network_tools": ["get_network_interfaces", "check_connectivity", "get_network_connections"],
            "device_tools": ["scan_usb_devices", "scan_pci_devices", "scan_serial_ports", "connect_to_device", "get_block_devices"],
            "terminal_tools": ["execute_safe_command"],
            "workflow_tools": ["request_permission", "check_permission_status"]
        }

# Example usage
async def test_agno_service():
    """Test the Agno AI service with real tools"""
    # This would be integrated into your Flask app
    ai_service = AgnoAIService(together_api_key=os.getenv('TOGETHER_API_KEY'))
    
    # Test different goal types
    test_goals = [
        "Show me the current directory contents",
        "Check system disk usage",
        "Scan for connected USB devices",
        "Test network connectivity",
        "List running processes"
    ]
    
    for goal in test_goals:
        print(f"\n=== Testing Goal: {goal} ===")
        result = await ai_service.process_user_goal(goal)
        print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_agno_service())