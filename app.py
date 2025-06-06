import os
import json
import subprocess
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import serial
import serial.tools.list_ports
import psutil

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables for device management
connected_devices = {}
terminal_processes = {}
ai_model = None  # Placeholder for AI model integration

class IoTDeviceManager:
    """Manages IoT device connections and operations"""
    
    def __init__(self):
        self.devices = {}
        self.serial_connections = {}
    
    def scan_devices(self):
        """Scan for available IoT devices (serial ports)"""
        ports = serial.tools.list_ports.comports()
        available_devices = []
        
        for port in ports:
            device_info = {
                'port': port.device,
                'description': port.description,
                'hwid': port.hwid,
                'manufacturer': getattr(port, 'manufacturer', 'Unknown'),
                'status': 'disconnected'
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
            
            # Start monitoring thread for this device
            monitor_thread = threading.Thread(
                target=self._monitor_device, 
                args=(port,), 
                daemon=True
            )
            monitor_thread.start()
            
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
    
    def _monitor_device(self, port):
        """Monitor device output in background"""
        connection = self.serial_connections.get(port)
        while port in self.serial_connections and connection.is_open:
            try:
                if connection.in_waiting:
                    data = connection.readline().decode().strip()
                    if data:
                        socketio.emit('device_output', {
                            'port': port,
                            'data': data,
                            'timestamp': datetime.now().isoformat()
                        })
                time.sleep(0.1)
            except Exception as e:
                socketio.emit('device_error', {
                    'port': port,
                    'error': str(e)
                })
                break

class TerminalManager:
    """Manages terminal sessions and command execution"""
    
    def __init__(self):
        self.processes = {}
    
    def execute_command(self, command, session_id='default'):
        """Execute a terminal command"""
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
                'timestamp': datetime.now().isoformat()
            }
            
            return output
        except subprocess.TimeoutExpired:
            return {
                'command': command,
                'stdout': '',
                'stderr': 'Command timed out after 30 seconds',
                'return_code': -1,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'command': command,
                'stdout': '',
                'stderr': str(e),
                'return_code': -1,
                'timestamp': datetime.now().isoformat()
            }

# Import the new AI service (add this at the top of the file)
from ai_service_agno import AgnoAIService, AIResponse

class AIAssistant:
    """Enhanced AI assistant using Agno framework with Together AI"""
    
    def __init__(self, device_manager, terminal_manager):
        self.device_manager = device_manager
        self.terminal_manager = terminal_manager
        
        # Initialize Agno AI Service
        # Get Together AI API key from environment variable
        together_api_key = os.getenv('TOGETHER_API_KEY')
        if not together_api_key:
            print("⚠️  Warning: TOGETHER_API_KEY not found. AI features will use fallback mode.")
            self.ai_service = None
            self.model_loaded = False
        else:
            try:
                self.ai_service = AgnoAIService(device_manager, terminal_manager, together_api_key)
                self.model_loaded = True
                print("🧠 Agno AI Service initialized successfully")
            except Exception as e:
                print(f"❌ Failed to initialize Agno AI Service: {str(e)}")
                self.ai_service = None
                self.model_loaded = False
    
    async def process_natural_language(self, text, context=None):
        """Process natural language input with advanced AI reasoning"""
        if self.ai_service and self.model_loaded:
            try:
                # Use Agno AI service for advanced processing
                response = await self.ai_service.process_natural_language(
                    text=text,
                    context=context or {},
                    use_reasoning=True,
                    agent_type="auto"
                )
                
                # Convert Agno response to legacy format for compatibility
                if response.success:
                    # Parse the response to determine command type
                    command_type = self._infer_command_type(text, response.response)
                    
                    return {
                        'command': command_type,
                        'original_text': text,
                        'confidence': response.confidence,
                        'ai_response': response.response,
                        'reasoning': response.reasoning,
                        'actions_taken': response.actions_taken,
                        'parameters': self._extract_parameters_from_ai_response(response.response)
                    }
                else:
                    return {
                        'command': 'error',
                        'original_text': text,
                        'confidence': 0.0,
                        'ai_response': response.response,
                        'parameters': {}
                    }
                    
            except Exception as e:
                print(f"AI Service Error: {str(e)}")
                return await self._fallback_processing(text, context)
        else:
            # Fallback to simple processing
            return await self._fallback_processing(text, context)
    
    async def _fallback_processing(self, text, context=None):
        """Fallback processing when AI service is not available"""
        # Simple command mapping for demonstration
        command_mapping = {
            'scan devices': 'device_scan',
            'list devices': 'device_list',
            'connect to': 'device_connect',
            'disconnect': 'device_disconnect',
            'flash firmware': 'firmware_flash',
            'reset device': 'device_reset',
            'check status': 'device_status',
            'explain': 'explain_command',
            'help': 'help',
            'diagnose': 'diagnostic'
        }
        
        text_lower = text.lower().strip()
        
        for phrase, command in command_mapping.items():
            if phrase in text_lower:
                return {
                    'command': command,
                    'original_text': text,
                    'confidence': 0.6,  # Lower confidence for fallback
                    'ai_response': f"Fallback mode: Interpreted as {command}",
                    'parameters': self._extract_parameters(text, command)
                }
        
        return {
            'command': 'unknown',
            'original_text': text,
            'confidence': 0.0,
            'ai_response': 'Command not recognized. Try: "scan devices", "connect to [port]", "help"',
            'parameters': {}
        }
    
    def _infer_command_type(self, original_text, ai_response):
        """Infer command type from AI response"""
        response_lower = ai_response.lower()
        text_lower = original_text.lower()
        
        # Check for specific actions in the AI response
        if 'scan' in response_lower and 'device' in response_lower:
            return 'device_scan'
        elif 'connect' in response_lower:
            return 'device_connect'
        elif 'disconnect' in response_lower:
            return 'device_disconnect'
        elif 'flash' in response_lower or 'firmware' in response_lower:
            return 'firmware_flash'
        elif 'command' in response_lower and 'terminal' in response_lower:
            return 'terminal_command'
        elif 'help' in text_lower or 'explain' in text_lower:
            return 'explain_command'
        elif 'diagnose' in response_lower or 'troubleshoot' in response_lower:
            return 'diagnostic'
        else:
            return 'ai_response'  # General AI response
    
    def _extract_parameters(self, text, command):
        """Extract parameters from natural language"""
        params = {}
        
        if command == 'device_connect':
            # Extract COM port or device name
            words = text.split()
            for word in words:
                if 'COM' in word.upper() or '/dev/' in word or '/tty' in word.lower():
                    params['port'] = word
        elif command == 'terminal_command':
            # Extract command after keywords
            for keyword in ['run', 'execute', 'command']:
                if keyword in text.lower():
                    parts = text.lower().split(keyword, 1)
                    if len(parts) > 1:
                        params['command'] = parts[1].strip()
        
        return params
    
    def _extract_parameters_from_ai_response(self, ai_response):
        """Extract parameters from AI response"""
        params = {}
        
        # Look for specific patterns in AI response
        if 'port' in ai_response.lower():
            # Try to extract port information
            import re
            port_pattern = r'(COM\d+|/dev/tty\w+|/dev/cu\.\w+)'
            matches = re.findall(port_pattern, ai_response)
            if matches:
                params['port'] = matches[0]
        
        return params
    
    async def explain_command(self, command):
        """Get AI explanation for a command"""
        if self.ai_service and self.model_loaded:
            try:
                response = await self.ai_service.explain_command(command)
                return response.response
            except Exception as e:
                return f"Error explaining command: {str(e)}"
        else:
            return f"Command '{command}' - explanation not available (AI service not loaded)"
    
    async def get_device_recommendations(self, device_context):
        """Get AI recommendations for device management"""
        if self.ai_service and self.model_loaded:
            try:
                response = await self.ai_service.get_device_recommendations(device_context)
                return response.response
            except Exception as e:
                return f"Error getting recommendations: {str(e)}"
        else:
            return "Recommendations not available (AI service not loaded)"
    
    def get_status(self):
        """Get AI service status"""
        if self.ai_service and self.model_loaded:
            return {
                'status': 'active',
                'service': 'Agno + Together AI',
                'agents': self.ai_service.get_agent_status()
            }
        else:
            return {
                'status': 'fallback',
                'service': 'Basic pattern matching',
                'agents': {}
            }

# Initialize managers
device_manager = IoTDeviceManager()
terminal_manager = TerminalManager()
ai_assistant = AIAssistant(device_manager, terminal_manager)  # Pass managers to AI assistant

@app.route('/')
def index():
    """Main application page"""
    return render_template('index.html')

@app.route('/api/devices/scan')
def scan_devices():
    """API endpoint to scan for devices"""
    devices = device_manager.scan_devices()
    return jsonify(devices)

@app.route('/api/devices/connect', methods=['POST'])
def connect_device():
    """API endpoint to connect to a device"""
    data = request.get_json()
    port = data.get('port')
    baudrate = data.get('baudrate', 115200)
    
    success, message = device_manager.connect_device(port, baudrate)
    return jsonify({'success': success, 'message': message})

@app.route('/api/devices/disconnect', methods=['POST'])
def disconnect_device():
    """API endpoint to disconnect from a device"""
    data = request.get_json()
    port = data.get('port')
    
    success = device_manager.disconnect_device(port)
    return jsonify({'success': success})

@app.route('/api/devices/command', methods=['POST'])
def send_device_command():
    """API endpoint to send command to device"""
    data = request.get_json()
    port = data.get('port')
    command = data.get('command')
    
    success, message = device_manager.send_command(port, command)
    return jsonify({'success': success, 'message': message})

@app.route('/api/ai/status')
def ai_status():
    """Get AI service status"""
    status = ai_assistant.get_status()
    return jsonify(status)

@app.route('/api/ai/explain', methods=['POST'])
def explain_command():
    """Get AI explanation for a command"""
    data = request.get_json()
    command = data.get('command', '')
    
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        explanation = loop.run_until_complete(ai_assistant.explain_command(command))
        return jsonify({'success': True, 'explanation': explanation})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ai/recommendations', methods=['POST'])
def get_recommendations():
    """Get AI recommendations for device management"""
    data = request.get_json()
    device_context = data.get('context', {})
    
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        recommendations = loop.run_until_complete(ai_assistant.get_device_recommendations(device_context))
        return jsonify({'success': True, 'recommendations': recommendations})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/system/info')
def system_info():
    """Get system information"""
    info = {
        'cpu_percent': psutil.cpu_percent(),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent,
        'platform': os.name,
        'timestamp': datetime.now().isoformat()
    }
    return jsonify(info)

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('status', {'message': 'Connected to IoT Control System'})

@socketio.on('terminal_command')
def handle_terminal_command(data):
    """Handle terminal command execution"""
    command = data.get('command', '')
    session_id = data.get('session_id', 'default')
    
    # Execute command
    result = terminal_manager.execute_command(command, session_id)
    
    # Emit result back to client
    emit('terminal_output', result)

@socketio.on('natural_language_input')
def handle_natural_language(data):
    """Handle natural language processing with advanced AI"""
    text = data.get('text', '')
    context = data.get('context', {})
    
    try:
        # Use asyncio to run the async AI processing
        import asyncio
        
        # Create event loop if one doesn't exist
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Process with AI
        if loop.is_running():
            # If loop is already running, create a task
            future = asyncio.ensure_future(ai_assistant.process_natural_language(text, context))
            result = None
            # Wait for completion (this is a simplified approach)
            import time
            timeout = 30  # 30 second timeout
            start_time = time.time()
            while not future.done() and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if future.done():
                result = future.result()
            else:
                result = {
                    'command': 'timeout',
                    'original_text': text,
                    'confidence': 0.0,
                    'ai_response': 'Request timed out after 30 seconds',
                    'parameters': {}
                }
        else:
            # Run the coroutine
            result = loop.run_until_complete(ai_assistant.process_natural_language(text, context))
        
        # Emit AI response
        emit('ai_response', {
            'interpretation': result,
            'status': 'success' if result.get('command') != 'unknown' else 'unknown_command',
            'message': result.get('ai_response', ''),
            'reasoning': result.get('reasoning'),
            'actions_taken': result.get('actions_taken', [])
        })
        
        # Auto-execute some commands based on AI interpretation
        command = result.get('command')
        if command == 'device_scan':
            devices = device_manager.scan_devices()
            emit('device_list_update', devices)
            emit('command_executed', {'action': 'device_scan', 'result': f'Found {len(devices)} devices'})
        
        elif command == 'device_connect':
            port = result.get('parameters', {}).get('port')
            if port:
                success, message = device_manager.connect_device(port)
                emit('command_executed', {
                    'action': 'device_connect', 
                    'result': f"Connection to {port}: {'Success' if success else 'Failed'} - {message}"
                })
        
        elif command == 'device_disconnect':
            port = result.get('parameters', {}).get('port')
            if port:
                success = device_manager.disconnect_device(port)
                emit('command_executed', {
                    'action': 'device_disconnect',
                    'result': f"Disconnection from {port}: {'Success' if success else 'Failed'}"
                })
        
        elif command == 'terminal_command':
            cmd = result.get('parameters', {}).get('command')
            if cmd:
                terminal_result = terminal_manager.execute_command(cmd)
                emit('terminal_output', terminal_result)
        
        elif command == 'help':
            help_message = """
            Available AI Commands:
            - "scan for devices" - Scan for available IoT devices
            - "connect to [port]" - Connect to specific device (e.g., "connect to COM3")
            - "disconnect from [port]" - Disconnect from device
            - "run command [cmd]" - Execute terminal command
            - "explain [command]" - Get explanation of a command
            - "diagnose issues" - Run diagnostic checks
            - "flash firmware to [port]" - Flash firmware to device
            - "check system status" - Get system health report
            """
            emit('ai_response', {
                'interpretation': result,
                'status': 'help',
                'message': help_message
            })
    
    except Exception as e:
        emit('ai_response', {
            'interpretation': {'command': 'error', 'original_text': text},
            'status': 'error',
            'message': f'AI processing error: {str(e)}'
        })

@socketio.on('file_upload')
def handle_file_upload(data):
    """Handle firmware file uploads"""
    filename = data.get('filename')
    file_data = data.get('data')
    
    # Save uploaded file
    upload_dir = os.path.join(os.getcwd(), 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, filename)
    
    try:
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        emit('upload_status', {
            'success': True,
            'message': f'File {filename} uploaded successfully',
            'path': file_path
        })
    except Exception as e:
        emit('upload_status', {
            'success': False,
            'message': f'Upload failed: {str(e)}'
        })

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("🚀 IoT Control System Starting...")
    print("📡 WebSocket server enabled")
    print("🔌 Device scanning ready")
    print("🧠 AI assistant loaded")
    print("💻 Terminal access enabled")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5123)