"""Blender WebSocket Server for Zoxel Avatar Control.

This module provides a WebSocket server that allows external clients (like the
web browser) to control Blender operations remotely. It enables:

- Building and rebuilding the avatar
- Equipping/unequipping accessories
- Getting the current state
- Running arbitrary Blender Python code (with safety checks)

Usage:

    # Run the server (Blender must have sockets available)
    blender --background --python blender/server.py

    # Or run in foreground mode
    blender --python blender/server.py

The server listens on ws://localhost:8080 by default.
"""

import asyncio
import json
import os
import sys
import traceback
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Blender imports - only available when running inside Blender
try:
    import bpy
    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False

# Add the blender directory to the path
_BLENDER_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_DIR = os.path.dirname(_BLENDER_DIR)
if _BLENDER_DIR not in sys.path:
    sys.path.insert(0, _BLENDER_DIR)

# Import zoxel accessories if available
try:
    import zoxel_accessories as zx
    ZOXEL_AVAILABLE = True
except ImportError:
    ZOXEL_AVAILABLE = False


# =============================================================================
# WebSocket Server Implementation
# =============================================================================

class WebSocketHandler:
    """Handles WebSocket connections and message processing."""
    
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.connections = []
        self.server = None
        
    async def handle_connection(self, reader, writer):
        """Handle a new WebSocket connection."""
        try:
            # Perform WebSocket handshake
            request = await reader.read(1024)
            if not self._validate_websocket_handshake(request):
                writer.close()
                return
            
            # Send WebSocket handshake response
            response = self._create_websocket_response(request)
            writer.write(response)
            await writer.drain()
            
            # Add to connections list
            self.connections.append(writer)
            print(f"WebSocket client connected ({len(self.connections)} total)")
            
            # Process messages
            while True:
                try:
                    data = await reader.read(4096)
                    if not data:
                        break
                    
                    # Parse and handle message
                    await self._handle_message(data.decode('utf-8'), writer)
                except ConnectionError:
                    break
                    
        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            if writer in self.connections:
                self.connections.remove(writer)
            writer.close()
            print(f"WebSocket client disconnected ({len(self.connections)} remaining)")
    
    def _validate_websocket_handshake(self, request):
        """Validate WebSocket handshake request."""
        return b'Sec-WebSocket-Key' in request and b'Upgrade: websocket' in request
    
    def _create_websocket_response(self, request):
        """Create WebSocket handshake response."""
        # Extract Sec-WebSocket-Key from request
        lines = request.split(b'\r\n')
        key = None
        for line in lines:
            if line.startswith(b'Sec-WebSocket-Key:'):
                key = line.split(b': ')[1].strip()
                break
        
        if not key:
            return b""
        
        import base64
        import hashlib
        
        # Create accept key
        magic = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        accept = base64.b64encode(hashlib.sha1(key + magic).digest())
        
        response = (
            b'HTTP/1.1 101 Switching Protocols\r\n'
            b'Upgrade: websocket\r\n'
            b'Connection: Upgrade\r\n'
            b'Sec-WebSocket-Accept: ' + accept + b'\r\n'
            b'\r\n'
        )
        return response
    
    async def _handle_message(self, message, writer):
        """Handle an incoming WebSocket message."""
        try:
            # Parse JSON message
            data = json.loads(message)
            
            # Get command type
            command = data.get('command', '')
            request_id = data.get('requestId', None)
            
            print(f"Received command: {command}")
            
            # Route to appropriate handler
            response = None
            
            if command == 'build_avatar':
                response = await self._handle_build_avatar()
            elif command == 'equip':
                slot = data.get('slot')
                item_id = data.get('itemId')
                response = await self._handle_equip(slot, item_id)
            elif command == 'unequip':
                slot = data.get('slot')
                response = await self._handle_unequip(slot)
            elif command == 'get_state':
                response = await self._handle_get_state()
            elif command == 'get_equipped':
                response = await self._handle_get_equipped()
            elif command == 'reload':
                response = await self._handle_reload()
            elif command == 'execute':
                # Execute arbitrary Python code (with safety checks)
                code = data.get('code', '')
                response = await self._handle_execute(code)
            elif command == 'ping':
                response = {'status': 'ok', 'message': 'pong'}
            else:
                response = {'error': f'Unknown command: {command}'}
            
            # Add request ID to response
            if request_id is not None:
                response = response or {}
                response['requestId'] = request_id
            
            # Send response
            await self._send_message(writer, response)
            
        except json.JSONDecodeError:
            await self._send_message(writer, {'error': 'Invalid JSON'})
        except Exception as e:
            error_response = {
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            if request_id is not None:
                error_response['requestId'] = request_id
            await self._send_message(writer, error_response)
    
    async def _send_message(self, writer, message):
        """Send a message to a WebSocket client."""
        message_json = json.dumps(message)
        # Simple text frame (for simplicity, not full WebSocket framing)
        writer.write(message_json.encode('utf-8') + b'\n')
        await writer.drain()
    
    async def broadcast(self, message):
        """Broadcast a message to all connected clients."""
        message_json = json.dumps(message)
        for writer in self.connections[:]:  # Copy list to avoid modification during iteration
            try:
                writer.write(message_json.encode('utf-8') + b'\n')
                await writer.drain()
            except:
                # Remove dead connections
                if writer in self.connections:
                    self.connections.remove(writer)
    
    # =========================================================================
    # Command Handlers
    # =========================================================================
    
    async def _handle_build_avatar(self):
        """Handle build_avatar command."""
        if not BLENDER_AVAILABLE:
            return {'error': 'Blender is not available'}
        
        try:
            if ZOXEL_AVAILABLE:
                root = zx.build_avatar()
                return {
                    'status': 'ok',
                    'message': 'Avatar rebuilt successfully',
                    'root': root.name if root else None
                }
            else:
                # Fallback: just report success
                return {'status': 'ok', 'message': 'Avatar rebuild requested'}
        except Exception as e:
            return {'error': str(e)}
    
    async def _handle_equip(self, slot, item_id):
        """Handle equip command."""
        if not BLENDER_AVAILABLE:
            return {'error': 'Blender is not available'}
        
        try:
            if ZOXEL_AVAILABLE and slot and item_id:
                zx.equip(slot, item_id)
                return {
                    'status': 'ok',
                    'message': f'Equipped {item_id} in {slot}',
                    'slot': slot,
                    'itemId': item_id
                }
            else:
                return {'error': 'Missing slot or itemId, or zoxel_accessories not available'}
        except Exception as e:
            return {'error': str(e)}
    
    async def _handle_unequip(self, slot):
        """Handle unequip command."""
        if not BLENDER_AVAILABLE:
            return {'error': 'Blender is not available'}
        
        try:
            if ZOXEL_AVAILABLE and slot:
                zx.unequip(slot)
                return {
                    'status': 'ok',
                    'message': fUnequipped from {slot}',
                    'slot': slot
                }
            else:
                return {'error': 'Missing slot or zoxel_accessories not available'}
        except Exception as e:
            return {'error': str(e)}
    
    async def _handle_get_state(self):
        """Handle get_state command - returns current Blender scene info."""
        if not BLENDER_AVAILABLE:
            return {'error': 'Blender is not available'}
        
        try:
            state = {
                'objects': [obj.name for obj in bpy.data.objects],
                'collections': [col.name for col in bpy.data.collections],
            }
            
            # Add rig info if available
            if ZOXEL_AVAILABLE:
                root = zx.rig.rig_root()
                if root:
                    state['rig'] = root.name
                    state['rig_children'] = [child.name for child in root.children]
            
            return {'status': 'ok', 'state': state}
        except Exception as e:
            return {'error': str(e)}
    
    async def _handle_get_equipped(self):
        """Handle get_equipped command."""
        if not BLENDER_AVAILABLE:
            return {'error': 'Blender is not available'}
        
        try:
            if ZOXEL_AVAILABLE:
                equipped = zx.get_equipped()
                return {'status': 'ok', 'equipped': equipped}
            else:
                return {'error': 'zoxel_accessories not available'}
        except Exception as e:
            return {'error': str(e)}
    
    async def _handle_reload(self):
        """Handle reload command."""
        if not BLENDER_AVAILABLE:
            return {'error': 'Blender is not available'}
        
        try:
            if ZOXEL_AVAILABLE:
                zx.reload()
                return {'status': 'ok', 'message': 'Zoxel accessories reloaded'}
            else:
                return {'error': 'zoxel_accessories not available'}
        except Exception as e:
            return {'error': str(e)}
    
    async def _handle_execute(self, code):
        """Handle execute command - runs arbitrary Python code."""
        if not BLENDER_AVAILABLE:
            return {'error': 'Blender is not available'}
        
        # Safety checks - prevent dangerous operations
        dangerous_keywords = ['os.system', 'subprocess', 'import os', 'import sys', 
                             '__import__', 'eval(', 'exec(', 'open(', 'remove(', 
                             'delete', 'rmdir', 'chmod', 'kill']
        
        for keyword in dangerous_keywords:
            if keyword in code:
                return {'error': f'Code contains prohibited operation: {keyword}'}
        
        try:
            # Create a safe namespace
            safe_namespace = {
                'bpy': bpy,
                'zx': zx if ZOXEL_AVAILABLE else None,
            }
            
            # Execute and capture output
            import io
            from contextlib import redirect_stdout, redirect_stderr
            
            stdout = io.StringIO()
            stderr = io.StringIO()
            
            with redirect_stdout(stdout), redirect_stderr(stderr):
                # Use exec with restricted globals
                exec(code, {'__builtins__': {}}, safe_namespace)
            
            return {
                'status': 'ok',
                'stdout': stdout.getvalue(),
                'stderr': stderr.getvalue()
            }
        except Exception as e:
            return {
                'error': str(e),
                'traceback': traceback.format_exc()
            }


# =============================================================================
# HTTP Server for serving files
# =============================================================================

class ZoxelHTTPHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves static files and provides API endpoints."""
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # API endpoints
        if path == '/api/status':
            self._send_json({'status': 'ok', 'blender': BLENDER_AVAILABLE, 'zoxel': ZOXEL_AVAILABLE})
            return
        elif path == '/api/equipped':
            if ZOXEL_AVAILABLE:
                self._send_json({'equipped': zx.get_equipped()})
            else:
                self._send_json({'error': 'zoxel_accessories not available'}, 500)
            return
        elif path == '/api/state':
            if BLENDER_AVAILABLE:
                state = {
                    'objects': [obj.name for obj in bpy.data.objects],
                }
                if ZOXEL_AVAILABLE:
                    root = zx.rig.rig_root()
                    if root:
                        state['rig'] = root.name
                self._send_json(state)
            else:
                self._send_json({'error': 'Blender not available'}, 500)
            return
        
        # Serve static files
        try:
            # Try to serve from client directory
            client_path = os.path.join(_REPO_DIR, 'client', path.lstrip('/'))
            if os.path.exists(client_path) and os.path.isfile(client_path):
                self._serve_file(client_path)
                return
            
            # Try to serve from current directory
            if os.path.exists(path.lstrip('/')):
                self._serve_file(path.lstrip('/'))
                return
            
            # Fallback to default handler
            super().do_GET()
        except Exception as e:
            self.send_error(500, str(e))
    
    def _send_json(self, data, status_code=200):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def _serve_file(self, filepath):
        """Serve a file."""
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            
            # Determine content type
            ext = os.path.splitext(filepath)[1].lower()
            content_types = {
                '.html': 'text/html',
                '.htm': 'text/html',
                '.js': 'application/javascript',
                '.ts': 'application/typescript',
                '.css': 'text/css',
                '.json': 'application/json',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.glb': 'model/gltf-binary',
                '.gltf': 'model/gltf+json',
            }
            
            content_type = content_types.get(ext, 'application/octet-stream')
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, str(e))


# =============================================================================
# Main Server
# =============================================================================

class BlenderServer:
    """Main server class that runs both WebSocket and HTTP servers."""
    
    def __init__(self, host='localhost', ws_port=8080, http_port=8081):
        self.host = host
        self.ws_port = ws_port
        self.http_port = http_port
        self.ws_handler = WebSocketHandler(host, ws_port)
        self.http_server = None
    
    async def start(self):
        """Start both servers."""
        # Start WebSocket server
        ws_server = await asyncio.start_server(
            self.ws_handler.handle_connection,
            self.host,
            self.ws_port
        )
        
        # Start HTTP server in a separate thread
        def run_http():
            httpd = HTTPServer((self.host, self.http_port), ZoxelHTTPHandler)
            print(f"HTTP server running on http://{self.host}:{self.http_port}")
            httpd.serve_forever()
        
        import threading
        http_thread = threading.Thread(target=run_http, daemon=True)
        http_thread.start()
        
        print(f"WebSocket server running on ws://{self.host}:{self.ws_port}")
        print(f"Blender available: {BLENDER_AVAILABLE}")
        print(f"Zoxel accessories available: {ZOXEL_AVAILABLE}")
        
        async with ws_server:
            await ws_server.serve_forever()
    
    def run(self):
        """Run the server (synchronous wrapper)."""
        asyncio.run(self.start())


def start_server(host='localhost', ws_port=8080, http_port=8081):
    """Start the Blender server.
    
    Args:
        host: Host to bind to
        ws_port: WebSocket port
        http_port: HTTP API port
    """
    server = BlenderServer(host, ws_port, http_port)
    server.run()


if __name__ == '__main__':
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Zoxel Blender WebSocket Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--ws-port', type=int, default=8080, help='WebSocket port')
    parser.add_argument('--http-port', type=int, default=8081, help='HTTP port')
    parser.add_argument('--blend', default=None, help='Blender file to open')
    args = parser.parse_args()
    
    # Open blend file if specified
    if args.blend and BLENDER_AVAILABLE:
        try:
            bpy.ops.wm.open_mainfile(filepath=args.blend)
            print(f"Opened Blender file: {args.blend}")
        except Exception as e:
            print(f"Could not open {args.blend}: {e}")
    
    # Start the server
    start_server(args.host, args.ws_port, args.http_port)
