import os
import json
import asyncio
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

# Agno imports for AI agents
from agno.agent import Agent
from agno.models.together import Together
from agno.tools.reasoning import ReasoningTools
from agno.tools.thinking import ThinkingTools
from agno.tools import Toolkit

# Custom IoT Tools for Agno agents
class IoTDeviceTools(Toolkit):
    """Custom tools for IoT device management"""
    
    def __init__(self, device_manager, terminal_manager):
        super().__init__()
        self.device_manager = device_manager
        self.terminal_manager = terminal_manager
    
    def scan_devices(self) -> str:
        """Scan for available IoT devices"""
        try:
            devices = self.device_manager.scan_devices()
            result = f"Found {len(devices)} devices:\n"
            for device in devices:
                result += f"- {device['port']}: {device['description']}\n"
            return result
        except Exception as e:
            return f"Error scanning devices: {str(e)}"
    
    def connect_device(self, port: str, baudrate: int = 115200) -> str:
        """Connect to a specific IoT device"""
        try:
            success, message = self.device_manager.connect_device(port, baudrate)
            return f"Connection to {port}: {'Success' if success else 'Failed'} - {message}"
        except Exception as e:
            return f"Error connecting to {port}: {str(e)}"
    
    def disconnect_device(self, port: str) -> str:
        """Disconnect from a specific IoT device"""
        try:
            success = self.device_manager.disconnect_device(port)
            return f"Disconnection from {port}: {'Success' if success else 'Failed'}"
        except Exception as e:
            return f"Error disconnecting from {port}: {str(e)}"
    
    def send_device_command(self, port: str, command: str) -> str:
        """Send command to connected IoT device"""
        try:
            success, message = self.device_manager.send_command(port, command)
            return f"Command '{command}' to {port}: {'Sent' if success else 'Failed'} - {message}"
        except Exception as e:
            return f"Error sending command to {port}: {str(e)}"
    
    def execute_terminal_command(self, command: str) -> str:
        """Execute system terminal command"""
        try:
            result = self.terminal_manager.execute_command(command)
            output = f"Command: {result['command']}\n"
            if result['stdout']:
                output += f"Output: {result['stdout']}\n"
            if result['stderr']:
                output += f"Error: {result['stderr']}\n"
            output += f"Return Code: {result['return_code']}"
            return output
        except Exception as e:
            return f"Error executing command: {str(e)}"
    
    def list_connected_devices(self) -> str:
        """List all currently connected devices"""
        try:
            connected = list(self.device_manager.serial_connections.keys())
            if connected:
                return f"Connected devices: {', '.join(connected)}"
            else:
                return "No devices currently connected"
        except Exception as e:
            return f"Error listing connected devices: {str(e)}"

class TerminalTools(Toolkit):
    """Terminal-specific tools for system operations"""
    
    def __init__(self, terminal_manager):
        super().__init__()
        self.terminal_manager = terminal_manager
    
    def run_command(self, command: str) -> str:
        """Execute a terminal command and return results"""
        try:
            result = self.terminal_manager.execute_command(command)
            return json.dumps({
                'command': result['command'],
                'output': result['stdout'],
                'error': result['stderr'],
                'success': result['return_code'] == 0
            })
        except Exception as e:
            return f"Command execution failed: {str(e)}"
    
    def check_system_status(self) -> str:
        """Check system health and status"""
        commands = ['df -h', 'free -h', 'ps aux | head -10', 'uptime']
        status = "System Status Report:\n"
        
        for cmd in commands:
            try:
                result = self.terminal_manager.execute_command(cmd)
                status += f"\n{cmd}:\n{result['stdout']}\n"
            except Exception as e:
                status += f"\n{cmd}: Error - {str(e)}\n"
        
        return status

class FirmwareTools(Toolkit):
    """Tools for firmware management and flashing"""
    
    def __init__(self, device_manager):
        super().__init__()
        self.device_manager = device_manager
    
    def flash_firmware(self, port: str, firmware_path: str, protocol: str = "esptool") -> str:
        """Flash firmware to IoT device"""
        try:
            if protocol == "esptool":
                # ESP32/ESP8266 flashing
                command = f"esptool.py --port {port} write_flash 0x0 {firmware_path}"
            elif protocol == "avrdude":
                # Arduino flashing
                command = f"avrdude -p atmega328p -c arduino -P {port} -U flash:w:{firmware_path}"
            elif protocol == "stlink":
                # STM32 flashing
                command = f"st-flash write {firmware_path} 0x8000000"
            else:
                return f"Unsupported flashing protocol: {protocol}"
            
            # Execute flashing command
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                return f"Firmware flashed successfully to {port}"
            else:
                return f"Firmware flashing failed: {result.stderr}"
                
        except Exception as e:
            return f"Error during firmware flashing: {str(e)}"
    
    def verify_firmware(self, port: str) -> str:
        """Verify firmware on device"""
        try:
            # Send version command to device
            success, message = self.device_manager.send_command(port, "AT+VERSION")
            if success:
                return f"Firmware verification for {port}: {message}"
            else:
                return f"Failed to verify firmware on {port}: {message}"
        except Exception as e:
            return f"Error verifying firmware: {str(e)}"

@dataclass
class AIResponse:
    """Structured AI response"""
    success: bool
    response: str
    reasoning: Optional[str] = None
    actions_taken: List[str] = None
    confidence: float = 0.0
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.actions_taken is None:
            self.actions_taken = []

class AgnoAIService:
    """Advanced AI service using Agno framework with Together AI and reasoning tools"""
    
    def __init__(self, device_manager, terminal_manager, together_api_key: str):
        self.device_manager = device_manager
        self.terminal_manager = terminal_manager
        self.together_api_key = together_api_key
        
        # Set environment variable for Together AI
        os.environ['TOGETHER_API_KEY'] = together_api_key
        
        # Initialize custom tools
        self.iot_tools = IoTDeviceTools(device_manager, terminal_manager)
        self.terminal_tools = TerminalTools(terminal_manager)
        self.firmware_tools = FirmwareTools(device_manager)
        
        # Initialize AI agents
        self._setup_agents()
    
    def _setup_agents(self):
        """Setup specialized AI agents for different tasks"""
        
        # Main IoT Control Agent with reasoning capabilities
        self.iot_agent = Agent(
            name="IoT Control Agent",
            model=Together(id="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
            tools=[
                ThinkingTools(add_instructions=True),
                ReasoningTools(add_instructions=True),
                self.iot_tools,
                self.firmware_tools
            ],
            instructions=[
                "You are an expert IoT device control agent.",
                "Always think through problems step by step using the thinking tools.",
                "Use reasoning tools to analyze results of your actions.",
                "Prioritize device safety and proper connection protocols.",
                "Provide clear explanations of what you're doing and why.",
                "If a command might be dangerous, explain the risks first."
            ],
            reasoning=True,  # Enable built-in reasoning
            show_tool_calls=True,
            markdown=True
        )
        
        # Terminal/System Agent for system operations
        self.terminal_agent = Agent(
            name="Terminal Agent",
            model=Together(id="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
            tools=[
                ThinkingTools(add_instructions=True),
                self.terminal_tools
            ],
            instructions=[
                "You are a system administration expert.",
                "Execute terminal commands safely and efficiently.",
                "Always explain what commands do before running them.",
                "Avoid potentially harmful commands without explicit confirmation.",
                "Provide context for command outputs."
            ],
            show_tool_calls=True,
            markdown=True
        )
        
        # Diagnostic Agent for troubleshooting
        self.diagnostic_agent = Agent(
            name="Diagnostic Agent",
            model=Together(id="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
            tools=[
                ThinkingTools(add_instructions=True),
                ReasoningTools(add_instructions=True),
                self.iot_tools,
                self.terminal_tools
            ],
            instructions=[
                "You are a diagnostic expert for IoT systems.",
                "Systematically troubleshoot device and system issues.",
                "Use step-by-step reasoning to identify problems.",
                "Suggest multiple solutions when possible.",
                "Explain the root cause of issues clearly."
            ],
            reasoning=True,
            show_tool_calls=True,
            markdown=True
        )
        
        # Multi-agent coordinator
        self.coordinator_agent = Agent(
            name="Coordinator",
            team=[self.iot_agent, self.terminal_agent, self.diagnostic_agent],
            model=Together(id="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
            instructions=[
                "Coordinate between different specialist agents.",
                "Route tasks to the most appropriate agent.",
                "Synthesize results from multiple agents when needed.",
                "Ensure consistent and comprehensive responses."
            ],
            show_tool_calls=True,
            markdown=True
        )
    
    async def process_natural_language(self, 
                                     text: str, 
                                     context: Dict[str, Any] = None,
                                     use_reasoning: bool = True,
                                     agent_type: str = "auto") -> AIResponse:
        """
        Process natural language input with step-by-step reasoning
        
        Args:
            text: User input in natural language
            context: Additional context information
            use_reasoning: Whether to use step-by-step reasoning
            agent_type: Which agent to use ("iot", "terminal", "diagnostic", "auto")
        """
        try:
            # Determine which agent to use
            agent = self._select_agent(text, agent_type)
            
            # Add context to the prompt if provided
            enhanced_prompt = self._enhance_prompt(text, context)
            
            # Get response from agent with reasoning
            if use_reasoning:
                response = agent.run(
                    enhanced_prompt,
                    stream=False,
                    show_full_reasoning=True
                )
            else:
                response = agent.run(enhanced_prompt, stream=False)
            
            # Extract reasoning if available
            reasoning = None
            if hasattr(response, 'reasoning') and response.reasoning:
                reasoning = response.reasoning
            
            # Parse actions taken from tool calls
            actions_taken = self._extract_actions(response)
            
            return AIResponse(
                success=True,
                response=response.content if hasattr(response, 'content') else str(response),
                reasoning=reasoning,
                actions_taken=actions_taken,
                confidence=0.9  # High confidence for Agno responses
            )
            
        except Exception as e:
            return AIResponse(
                success=False,
                response=f"AI processing failed: {str(e)}",
                confidence=0.0
            )
    
    def _select_agent(self, text: str, agent_type: str) -> Agent:
        """Select the most appropriate agent based on the input"""
        if agent_type == "iot":
            return self.iot_agent
        elif agent_type == "terminal":
            return self.terminal_agent
        elif agent_type == "diagnostic":
            return self.diagnostic_agent
        elif agent_type == "auto":
            # Auto-select based on keywords
            text_lower = text.lower()
            
            if any(keyword in text_lower for keyword in ['connect', 'device', 'port', 'flash', 'firmware', 'iot']):
                return self.iot_agent
            elif any(keyword in text_lower for keyword in ['command', 'terminal', 'system', 'execute', 'run']):
                return self.terminal_agent
            elif any(keyword in text_lower for keyword in ['debug', 'troubleshoot', 'problem', 'error', 'fix', 'diagnose']):
                return self.diagnostic_agent
            else:
                return self.coordinator_agent
        else:
            return self.coordinator_agent
    
    def _enhance_prompt(self, text: str, context: Dict[str, Any] = None) -> str:
        """Enhance the prompt with context information"""
        enhanced = text
        
        if context:
            enhanced += "\n\nContext:\n"
            for key, value in context.items():
                enhanced += f"- {key}: {value}\n"
        
        # Add current system state
        enhanced += f"\n\nCurrent Time: {datetime.now().isoformat()}\n"
        
        # Add connected devices info
        try:
            connected_devices = list(self.device_manager.serial_connections.keys())
            if connected_devices:
                enhanced += f"Connected Devices: {', '.join(connected_devices)}\n"
            else:
                enhanced += "Connected Devices: None\n"
        except:
            pass
        
        return enhanced
    
    def _extract_actions(self, response) -> List[str]:
        """Extract actions taken from agent response"""
        actions = []
        
        # Try to extract tool calls if available
        try:
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    action = f"Used tool: {tool_call.get('function', {}).get('name', 'unknown')}"
                    actions.append(action)
            
            # Look for common action patterns in the response text
            response_text = str(response).lower()
            
            if 'connected to' in response_text:
                actions.append("Device connection established")
            if 'command sent' in response_text:
                actions.append("Command executed")
            if 'firmware flashed' in response_text:
                actions.append("Firmware update completed")
            if 'scan' in response_text and 'device' in response_text:
                actions.append("Device scan performed")
                
        except Exception as e:
            actions.append(f"Action extraction failed: {str(e)}")
        
        return actions
    
    async def get_device_recommendations(self, device_context: Dict[str, Any]) -> AIResponse:
        """Get AI recommendations for device management"""
        prompt = f"""
        Analyze the current IoT device context and provide recommendations:
        
        Device Context: {json.dumps(device_context, indent=2)}
        
        Please provide:
        1. Device status analysis
        2. Optimization recommendations
        3. Potential issues to watch for
        4. Suggested maintenance actions
        """
        
        return await self.process_natural_language(
            prompt, 
            context=device_context,
            agent_type="diagnostic"
        )
    
    async def explain_command(self, command: str) -> AIResponse:
        """Explain what a command does before execution"""
        prompt = f"""
        Explain this command in detail:
        Command: {command}
        
        Please provide:
        1. What this command does
        2. Potential risks or side effects
        3. Expected output
        4. Whether it's safe to run
        5. Any prerequisites needed
        """
        
        return await self.process_natural_language(
            prompt,
            agent_type="terminal"
        )
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all AI agents"""
        return {
            "iot_agent": {
                "name": self.iot_agent.name,
                "model": str(self.iot_agent.model),
                "tools": len(self.iot_agent.tools) if self.iot_agent.tools else 0
            },
            "terminal_agent": {
                "name": self.terminal_agent.name,
                "model": str(self.terminal_agent.model),
                "tools": len(self.terminal_agent.tools) if self.terminal_agent.tools else 0
            },
            "diagnostic_agent": {
                "name": self.diagnostic_agent.name,
                "model": str(self.diagnostic_agent.model),
                "tools": len(self.diagnostic_agent.tools) if self.diagnostic_agent.tools else 0
            },
            "coordinator": {
                "name": self.coordinator_agent.name,
                "team_size": len(self.coordinator_agent.team) if self.coordinator_agent.team else 0
            }
        }

# Example usage and testing
async def test_ai_service():
    """Test the AI service functionality"""
    # This would be called from your main application
    # ai_service = AgnoAIService(device_manager, terminal_manager, "your-together-api-key")
    
    # Test natural language processing
    # response = await ai_service.process_natural_language("scan for IoT devices and connect to the first one found")
    # print(f"AI Response: {response.response}")
    # print(f"Actions Taken: {response.actions_taken}")
    # if response.reasoning:
    #     print(f"Reasoning: {response.reasoning}")
    
    pass

if __name__ == "__main__":
    # Run tests
    asyncio.run(test_ai_service())