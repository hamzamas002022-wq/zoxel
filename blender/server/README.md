# Blender WebSocket Server

A WebSocket and HTTP server that enables external clients (like web browsers) to control Blender operations remotely. This allows for real-time interaction with the Zoxel avatar system from a web interface.

## Features

- **WebSocket API**: Real-time bidirectional communication
- **HTTP API**: REST-like endpoints for state queries
- **Full Zoxel Integration**: Control avatar building, accessories, and more
- **Code Execution**: Safely execute Python code in Blender
- **Auto-reconnection**: Client automatically reconnects if the connection drops

## Quick Start

### 1. Start the Server

From the repository root:

```bash
# Run in background mode (no UI)
blender --background --python blender/server.py

# Or with a specific blend file
blender --background --python blender/server.py --blend blender/zoxel_avatar.blend

# Or in foreground mode (with UI)
blender --python blender/server.py
```

By default, the server listens on:
- WebSocket: `ws://localhost:8080`
- HTTP API: `http://localhost:8081`

Customize ports:

```bash
blender --background --python blender/server.py --ws-port 9000 --http-port 9001
```

### 2. Connect from Client

```typescript
import { BlenderConnection } from './blender-connection';

const connection = new BlenderConnection('ws://localhost:8080');
await connection.connect();

// Build the avatar
await connection.buildAvatar();

// Equip an item
await connection.equip('Hand', 'sword_item');

// Get current state
const state = await connection.getState();
```

## WebSocket API

All commands are sent as JSON messages and return JSON responses.

### Message Format

```json
{
  "requestId": "1",
  "command": "build_avatar",
  "param1": "value1",
  "param2": "value2"
}
```

### Available Commands

| Command | Parameters | Description |
|---------|-----------|-------------|
| `build_avatar` | - | Rebuild the avatar rig from proportions |
| `equip` | `slot`, `itemId` | Equip an item in a slot |
| `unequip` | `slot` | Unequip item from a slot |
| `get_state` | - | Get current scene state |
| `get_equipped` | - | Get currently equipped items |
| `reload` | - | Reload zoxel accessories module |
| `execute` | `code` | Execute Python code (restricted) |
| `ping` | - | Check connection |

### Example Commands

```json
# Build avatar
{"command": "build_avatar"}

# Equip item
{"command": "equip", "slot": "Hand", "itemId": "sword"}

# Unequip from slot
{"command": "unequip", "slot": "Back"}

# Get equipped items
{"command": "get_equipped"}

# Execute Python code
{"command": "execute", "code": "print(bpy.data.objects)"}
```

### Response Format

```json
{
  "requestId": "1",
  "status": "ok",
  "message": "Success message"
}
```

Or for errors:

```json
{
  "requestId": "1",
  "status": "error",
  "error": "Error message",
  "traceback": "Full traceback..."
}
```

## HTTP API

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Check server and Blender status |
| GET | `/api/state` | Get current scene state |
| GET | `/api/equipped` | Get currently equipped items |

### Example Requests

```bash
# Check status
curl http://localhost:8081/api/status

# Get state
curl http://localhost:8081/api/state

# Get equipped items
curl http://localhost:8081/api/equipped
```

## Client-Side Usage

### Basic Usage

```typescript
import { BlenderConnection } from './blender-connection';

async function main() {
  const connection = new BlenderConnection();
  
  // Connect
  await connection.connect();
  
  // Build avatar
  await connection.buildAvatar();
  
  // Equip an item
  await connection.equip('Hand', 'sword');
  
  // Get state
  const state = await connection.getState();
  console.log('Current state:', state);
  
  // Get equipped items
  const equipped = await connection.getEquipped();
  console.log('Equipped:', equipped);
  
  // Disconnect
  connection.disconnect();
}
```

### Event Listeners

```typescript
connection.onStateChange((state) => {
  console.log('State changed:', state);
});

connection.onEquippedChange((equipped) => {
  console.log('Equipped changed:', equipped);
});

connection.onError((error) => {
  console.error('Connection error:', error);
});

connection.onClose((code, reason) => {
  console.log('Connection closed:', code, reason);
});

connection.onMessage((message) => {
  console.log('Message received:', message);
});
```

### Auto-Reconnection

```typescript
// Create a connection with auto-reconnect
const connection = new BlenderConnection();

// Auto-reconnect is enabled by default
// It will try up to 5 times with exponential backoff
await connection.connect(true);

// Or create a persistent connection
import { createPersistentConnection } from './blender-connection';

const connection = createPersistentConnection();
// This will automatically reconnect on close
```

### Using HTTP API

```typescript
import { getDefaultConnection } from './blender-connection';

const connection = getDefaultConnection();

// Check status
const status = await connection.checkStatus();
console.log('Server status:', status);

// Get state via HTTP
const state = await connection.getStateHttp();
console.log('State:', state);

// Get equipped via HTTP
const equipped = await connection.getEquippedHttp();
console.log('Equipped:', equipped);
```

## Security

The server includes basic safety measures:

1. **Code Execution**: The `execute` command blocks dangerous operations like:
   - File system access (`os.system`, `open`, `remove`, etc.)
   - Process spawning (`subprocess`)
   - Module imports (`import os`, `__import__`)
   - Other dangerous builtins

2. **WebSocket Origin**: The server accepts connections from any origin by default. For production, consider:
   - Running behind a reverse proxy
   - Adding origin validation
   - Using HTTPS/WSS

3. **Authentication**: Currently no authentication is implemented. For production use, add authentication tokens or API keys.

## Integration with Zoxel Accessories

The server automatically integrates with the `zoxel_accessories` module. When Blender is running:

- All zoxel functions are available through the WebSocket API
- The avatar can be rebuilt programmatically
- Accessories can be equipped/unequipped
- State changes are tracked

## Running in Production

For production use, consider:

1. **Run Blender in background**:
   ```bash
   blender --background --python blender/server.py --blend blender/zoxel_avatar.blend
   ```

2. **Use a process manager**:
   - Systemd service
   - PM2
   - Docker container

3. **Reverse proxy**:
   - Nginx
   - Apache
   - Caddy

4. **Security**:
   - Add authentication
   - Validate origins
   - Use HTTPS/WSS

## Troubleshooting

### Connection Issues

1. **WebSocket connection fails**:
   - Check that Blender is running
   - Verify the port is correct
   - Check firewall settings
   - Ensure Blender has network access

2. **Blender not available**:
   - Make sure you're running the server inside Blender
   - Use `--background` mode for headless operation

3. **Commands not working**:
   - Ensure the zoxel_accessories module is loaded
   - Check that the blend file is opened
   - Verify the rig exists

### Debug Mode

Add `--debug` flag to enable verbose logging:

```bash
blender --background --python blender/server.py --debug
```

## Files

| File | Description |
|------|-------------|
| `server.py` | Main server implementation |
| `blender-connection.ts` | TypeScript client library |
| `README.md` | This documentation |
