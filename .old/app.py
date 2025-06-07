import os
import json
import subprocess
import threading
import time
import asyncio
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import serial
import serial.tools.list_ports
import psutil

# Import the real Agno AI service
from ai_service_agno import AgnoAIService

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
socketio = SocketIO(app, cors_allowed_origins="*")

# Enhanced workflow state management
@dataclass
class WorkflowState:
    """Tracks the state of an AI goal-oriented workflow"""
    workflow_id: str
    goal: str
    current_step: str = "thinking"
    steps_completed: List[str] = field(default_factory=list)
    commands_executed: List[Dict] = field(default_factory=list)
    reasoning_history: List[str] = field(default_factory=list)
    is_goal_achieved: bool = False
    is_active: bool = True
    start_time: datetime = field(default_factory=datetime.now)
    max_attempts: int = 3
    current_attempt: int = 1
    agent_responses: List[str] = field(default_factory=list)

# Global workflow tracking
active_workflows: Dict[str, WorkflowState] = {}

class IoTDeviceManager:
    """Enhanced IoT device manager"""
    
    def __init__(self):
        self.devices = {}
        self.serial_connections = {}
    
    def scan_devices(self):
        """Scan for available IoT devices"""
        ports = serial.tools.list_ports.comports()
        available_devices = []
        
        for port in ports:
            device_info = {
                'port': port.device,
                'description': port.description,
                'hwid': port.hwid,
                'manufacturer': getattr(port, 'manufacturer', 'Unknown'),
                'status': 'connected' if port.device in self.serial_connections else 'disconnected'
            }
            available_devices.append(device_info)
        
        return available_devices
    
    def connect_device(self, port, baudrate=115200):
        """Connect to a device via serial"""
        try:
            if port in self.serial_connections:
                self.disconnect_device(port)
            
            connection = serial.Serial(port, baudrate, timeout=1)
            self.serial_connections[port] = connection
            return True, f"Connected to {port}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def disconnect_device(self, port):
        """Disconnect from a device"""
        if port in self.serial_connections:
            self.serial_connections[port].close()
            del self.serial_connections[port]
            return True
        return False
    
    def send_command(self, port, command):
        """Send command to device"""
        if port in self.serial_connections:
            try:
                connection = self.serial_connections[port]
                connection.write(f"{command}\n".encode())
                return True, "Command sent"
            except Exception as e:
                return False, str(e)
        return False, "Device not connected"

class EnhancedTerminalManager:
    """Enhanced terminal manager with AI workflow integration"""
    
    def __init__(self):
        self.processes = {}
        self.command_queue = []
    
    def execute_command(self, command, session_id='default', ai_injected=False, workflow_id=None):
        """Execute a terminal command with enhanced tracking"""
        try:
            # Execute command and capture output
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = {
                'command': command,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode,
                'timestamp': datetime.now().isoformat(),
                'ai_injected': ai_injected,
                'workflow_id': workflow_id,
                'session_id': session_id
            }
            
            # Track in workflow if applicable
            if workflow_id and workflow_id in active_workflows:
                active_workflows[workflow_id].commands_executed.append(output)
            
            return output
        except subprocess.TimeoutExpired:
            return {
                'command': command,
                'stdout': '',
                'stderr': 'Command timed out after 30 seconds',
                'return_code': -1,
                'timestamp': datetime.now().isoformat(),
                'ai_injected': ai_injected,
                'workflow_id': workflow_id
            }
        except Exception as e:
            return {
                'command': command,
                'stdout': '',
                'stderr': str(e),
                'return_code': -1,
                'timestamp': datetime.now().isoformat(),
                'ai_injected': ai_injected,
                'workflow_id': workflow_id
            }

# Initialize managers
device_manager = IoTDeviceManager()
terminal_manager = EnhancedTerminalManager()

# Initialize the real Agno AI service
together_api_key = os.getenv('TOGETHER_API_KEY')
if not together_api_key:
    print("⚠️  Warning: TOGETHER_API_KEY not found. Please set your Together AI API key.")
    print("   export TOGETHER_API_KEY='your-key-here'")

ai_service = AgnoAIService(
    device_manager=device_manager,
    terminal_manager=terminal_manager,
    socketio=socketio,
    together_api_key=together_api_key
)

# Flask routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/devices/scan')
def scan_devices():
    devices = device_manager.scan_devices()
    return jsonify(devices)

@app.route('/api/devices/connect', methods=['POST'])
def connect_device():
    data = request.get_json()
    port = data.get('port')
    success, message = device_manager.connect_device(port)
    return jsonify({'success': success, 'message': message})

@app.route('/api/system/info')
def system_info():
    info = {
        'cpu_percent': psutil.cpu_percent(),
        'memory_percent': psutil.virtual_memory().percent,
        'timestamp': datetime.now().isoformat()
    }
    return jsonify(info)

@app.route('/api/ai/tools')
def get_available_tools():
    """Get list of available AI tools"""
    tools = ai_service.get_available_tools()
    return jsonify(tools)

@app.route('/api/ai/status')
def ai_status():
    """Get AI service status"""
    status = {
        "status": "active" if together_api_key else "limited",
        "service": "Agno + Together AI" if together_api_key else "Fallback mode",
        "tools_available": len(ai_service.get_available_tools()),
        "agents": {
            "system_agent": "System Information Specialist",
            "filesystem_agent": "File System Navigator", 
            "network_agent": "Network Specialist",
            "device_agent": "Device Manager",
            "terminal_agent": "Terminal Command Specialist",
            "coordinator": "IoT Control Coordinator"
        }
    }
    return jsonify(status)

# Enhanced WebSocket events for real AI workflow
@socketio.on('connect')
def handle_connect():
    emit('status', {'message': 'Connected to Real AI-Enhanced IoT Control System'})

@socketio.on('ai_goal_request')
def handle_goal_request(data):
    """Handle new goal request - starts the real AI workflow"""
    goal = data.get('goal', '')
    context = data.get('context', {})
    workflow_id = str(data.get('context', {}).get('workflow_id', int(time.time())))
    
    # Create workflow state
    workflow = WorkflowState(
        workflow_id=workflow_id,
        goal=goal
    )
    active_workflows[workflow_id] = workflow
    
    # Emit thinking phase
    emit('ai_thinking', {
        "thought": f"Let me analyze your request: '{goal}'",
        "reasoning": "I'm determining which tools and agents can best help you achieve this goal.",
        "workflow_id": workflow_id
    })
    
    # Process with real AI
    try:
        # Create event loop for async processing
        def run_ai_processing():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Add workflow context
                enhanced_context = context.copy()
                enhanced_context.update({
                    "workflow_id": workflow_id,
                    "connected_devices": list(device_manager.serial_connections.keys()),
                    "user_goal": goal
                })
                
                # Process with real AI
                result = loop.run_until_complete(
                    ai_service.process_user_goal(goal, enhanced_context)
                )
                
                # Update workflow
                workflow.agent_responses.append(result.get("response", ""))
                workflow.steps_completed.append("ai_processing")
                
                # Emit AI response
                socketio.emit('ai_response', {
                    'interpretation': {
                        'command': 'ai_processing_complete',
                        'original_text': goal,
                        'confidence': 0.9,
                        'ai_response': result.get("response", ""),
                        'parameters': {}
                    },
                    'status': 'success' if result.get("status") == "success" else 'error',
                    'message': result.get("response", ""),
                    'reasoning': f"Used {result.get('agent_used', 'AI agent')} to process your request",
                    'actions_taken': ["AI agent analysis", "Tool execution"],
                    'workflow_id': workflow_id
                })
                
                # Check if goal is achieved
                if result.get("status") == "success":
                    workflow.is_goal_achieved = True
                    workflow.is_active = False
                    
                    socketio.emit('ai_goal_update', {
                        "status": "achieved",
                        "message": "Successfully processed your request using AI tools",
                        "workflow_id": workflow_id
                    })
                    
                    socketio.emit('ai_workflow_complete', {
                        'status': 'achieved',
                        'summary': f"Successfully completed: {goal}",
                        'steps_taken': len(workflow.steps_completed),
                        'ai_responses': len(workflow.agent_responses)
                    })
                else:
                    socketio.emit('ai_goal_update', {
                        "status": "failed",
                        "message": result.get("message", "AI processing encountered an error"),
                        "workflow_id": workflow_id
                    })
                    
            except Exception as e:
                socketio.emit('ai_workflow_complete', {
                    'status': 'failed',
                    'summary': f'AI processing failed: {str(e)}',
                    'steps_taken': len(workflow.steps_completed) if workflow else 0
                })
            finally:
                loop.close()
        
        # Run AI processing in background thread
        ai_thread = threading.Thread(target=run_ai_processing)
        ai_thread.daemon = True
        ai_thread.start()
        
        emit('ai_workflow_started', {
            "status": "processing", 
            "workflow_id": workflow_id,
            "message": "Real AI agents are processing your request..."
        })
        
    except Exception as e:
        emit('ai_workflow_complete', {
            'status': 'failed',
            'summary': f'Workflow startup failed: {str(e)}',
            'steps_taken': 0
        })

@socketio.on('ai_permission_response')
def handle_permission_response(data):
    """Handle user's permission response for AI tool execution"""
    permission_id = data.get('permission_id')
    allowed = data.get('allowed', False)
    modified_command = data.get('modified_command')
    
    try:
        result = ai_service.handle_permission_response(
            permission_id=permission_id,
            granted=allowed,
            modified_command=modified_command
        )
        
        emit('ai_permission_result', result)
        
        # If command was executed, show in terminal
        if result.get('status') == 'executed':
            emit('terminal_output', {
                'command': result.get('command'),
                'stdout': result.get('result', ''),
                'stderr': '',
                'return_code': 0,
                'ai_injected': True,
                'timestamp': datetime.now().isoformat()
            })
            
            # Update goal status
            emit('ai_goal_update', {
                "status": "progress",
                "message": f"Command executed: {result.get('command')}",
                "workflow_id": data.get('workflow_id')
            })
        
    except Exception as e:
        emit('ai_permission_result', {
            'status': 'error',
            'message': f'Permission processing failed: {str(e)}'
        })

@socketio.on('terminal_command')
def handle_terminal_command(data):
    """Handle direct terminal command execution"""
    command = data.get('command', '')
    ai_injected = data.get('ai_injected', False)
    workflow_id = data.get('workflow_id')
    session_id = data.get('session_id', 'default')
    
    # Execute command
    result = terminal_manager.execute_command(
        command, 
        session_id=session_id,
        ai_injected=ai_injected,
        workflow_id=workflow_id
    )
    
    # Emit result back to client
    emit('terminal_output', result)

@socketio.on('request_ai_help')
def handle_ai_help_request(data):
    """Handle requests for AI help with specific topics"""
    topic = data.get('topic', 'general')
    
    help_responses = {
        'general': """
        🤖 **AI Assistant Help**
        
        I'm powered by real AI agents with specialized tools:
        
        **System Information**: "check disk usage", "show memory info", "list processes"
        **File Operations**: "list files", "find files named *.txt", "show current directory"  
        **Network**: "check network status", "test connectivity", "show network interfaces"
        **Devices**: "scan for USB devices", "find IoT devices", "connect to COM3"
        **Terminal**: I can execute safe commands with your permission
        
        Just tell me what you want to achieve in natural language!
        """,
        'tools': """
        🔧 **Available AI Tools**
        
        **System Tools**: get_system_info, get_disk_usage, get_memory_info, get_process_list
        **File Tools**: list_directory, find_files, get_file_info
        **Network Tools**: get_network_interfaces, check_connectivity
        **Device Tools**: scan_usb_devices, scan_serial_ports, connect_to_device
        **Terminal Tools**: execute_safe_command (with permission)
        
        I automatically choose the right tools based on your request.
        """,
        'workflow': """
        ⚡ **AI Workflow Process**
        
        1. 🧠 **AI Thinking**: I analyze your goal
        2. 🔧 **Tool Selection**: I choose appropriate tools
        3. 🔐 **Permission**: I ask before executing commands
        4. ⚡ **Execution**: I use tools to gather information
        5. 📊 **Analysis**: I interpret results  
        6. 🎯 **Goal Check**: I verify if your goal was achieved
        7. 🔄 **Follow-up**: I suggest next steps if needed
        """
    }
    
    emit('ai_help_response', {
        'topic': topic,
        'content': help_responses.get(topic, help_responses['general'])
    })

# Error handling
@socketio.on_error_default
def default_error_handler(e):
    print(f"Socket error: {e}")
    emit('error', {'message': f'Socket error: {str(e)}'})

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    print("🚀 Real AI-Enhanced IoT Control System Starting...")
    print("🧠 Agno AI framework with Together AI")
    print("🔧 Real AI tools and agents loaded")
    print("🎯 Goal-oriented workflow with actual AI reasoning")
    print("🔐 Permission-based command execution")
    print("📡 WebSocket server enabled")
    
    if together_api_key:
        print("✅ Together AI API key detected - Full AI capabilities enabled")
    else:
        print("⚠️  No Together AI API key - Limited functionality")
        print("   Set TOGETHER_API_KEY environment variable for full AI features")
    
    print(f"🌐 Available AI tools: {len(ai_service.get_available_tools())} categories")
    print("🔄 Real-time AI processing ready")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5123)