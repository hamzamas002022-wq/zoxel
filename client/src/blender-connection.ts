/**
 * Zoxel Blender Connection
 * 
 * Provides WebSocket-based communication with a running Blender instance
 * that has the Zoxel server running.
 * 
 * Usage:
 * 
 * ```typescript
 * import { BlenderConnection } from './blender-connection';
 * 
 * const connection = new BlenderConnection('ws://localhost:8080');
 * 
 * // Connect to Blender
 * await connection.connect();
 * 
 * // Build the avatar
 * await connection.buildAvatar();
 * 
 * // Equip an item
 * await connection.equip('Back', 'my_item_id');
 * 
 * // Get current state
 * const state = await connection.getState();
 * 
 * // Subscribe to state changes
 * connection.onStateChange((state) => {
 *   console.log('State changed:', state);
 * });
 * ```
 */

// =============================================================================
// Types
// =============================================================================

export interface BlenderMessage {
  requestId?: string;
  command: string;
  [key: string]: unknown;
}

export interface BlenderResponse {
  requestId?: string;
  status?: 'ok' | 'error';
  error?: string;
  traceback?: string;
  message?: string;
  [key: string]: unknown;
}

export interface AvatarState {
  objects?: string[];
  collections?: string[];
  rig?: string;
  rig_children?: string[];
}

export interface EquippedItems {
  Back?: string;
  Hand?: string;
  [slot: string]: string | undefined;
}

export interface ServerStatus {
  status: 'ok' | 'error';
  blender: boolean;
  zoxel: boolean;
}

// =============================================================================
// Event Types
// =============================================================================

export type StateChangeCallback = (state: AvatarState) => void;
export type EquippedChangeCallback = (equipped: EquippedItems) => void;
export type ErrorCallback = (error: Error) => void;
export type CloseCallback = (code: number, reason: string) => void;
export type MessageCallback = (message: BlenderResponse) => void;

// =============================================================================
// Main Connection Class
// =============================================================================

export class BlenderConnection {
  private ws: WebSocket | null = null;
  private url: string;
  private requestIdCounter: number = 0;
  private pendingRequests: Map<number, (response: BlenderResponse) => void> = new Map();
  
  // Event listeners
  private stateChangeListeners: StateChangeCallback[] = [];
  private equippedChangeListeners: EquippedChangeCallback[] = [];
  private errorListeners: ErrorCallback[] = [];
  private closeListeners: CloseCallback[] = [];
  private messageListeners: MessageCallback[] = [];
  
  // Connection state
  private isConnected: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectDelay: number = 1000; // ms
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(url: string = 'ws://localhost:8080') {
    this.url = url;
  }

  // ===========================================================================
  // Connection Management
  // ===========================================================================

  /**
   * Connect to the Blender WebSocket server.
   */
  async connect(autoReconnect: boolean = true): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
          this.isConnected = true;
          this.reconnectAttempts = 0;
          console.log('[BlenderConnection] Connected to Blender server');
          resolve();
        };
        
        this.ws.onclose = (event: CloseEvent) => {
          this.isConnected = false;
          console.log('[BlenderConnection] Disconnected:', event.code, event.reason);
          
          // Notify listeners
          this.notifyClose(event.code, event.reason);
          
          // Auto-reconnect if enabled
          if (autoReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        };
        
        this.ws.onerror = (error: Event) => {
          console.error('[BlenderConnection] WebSocket error:', error);
          this.notifyError(new Error(`WebSocket error: ${error}`));
        };
        
        this.ws.onmessage = (event: MessageEvent) => {
          try {
            const response: BlenderResponse = JSON.parse(event.data as string);
            this.handleMessage(response);
          } catch (error) {
            console.error('[BlenderConnection] Error parsing message:', error);
            this.notifyError(error as Error);
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Disconnect from the Blender server.
   */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
  }

  /**
   * Check if connected to the Blender server.
   */
  get connected(): boolean {
    return this.isConnected;
  }

  /**
   * Get the WebSocket ready state.
   */
  get readyState(): number | undefined {
    return this.ws?.readyState;
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    console.log(`[BlenderConnection] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    this.reconnectTimer = setTimeout(() => {
      this.connect(true).catch(console.error);
    }, delay);
  }

  private handleMessage(response: BlenderResponse): void {
    // Notify all message listeners
    this.notifyMessage(response);
    
    // Check if this is a response to a pending request
    if (response.requestId !== undefined) {
      const requestId = parseInt(response.requestId as unknown as string);
      const callback = this.pendingRequests.get(requestId);
      if (callback) {
        callback(response);
        this.pendingRequests.delete(requestId);
      }
    }
    
    // Handle state change notifications
    if (response.status === 'ok') {
      if ('state' in response) {
        this.notifyStateChange(response.state as AvatarState);
      }
      if ('equipped' in response) {
        this.notifyEquippedChange(response.equipped as EquippedItems);
      }
    }
  }

  // ===========================================================================
  // Event Listeners
  // ===========================================================================

  onStateChange(callback: StateChangeCallback): void {
    this.stateChangeListeners.push(callback);
  }

  offStateChange(callback: StateChangeCallback): void {
    this.stateChangeListeners = this.stateChangeListeners.filter(
      (cb) => cb !== callback
    );
  }

  onEquippedChange(callback: EquippedChangeCallback): void {
    this.equippedChangeListeners.push(callback);
  }

  offEquippedChange(callback: EquippedChangeCallback): void {
    this.equippedChangeListeners = this.equippedChangeListeners.filter(
      (cb) => cb !== callback
    );
  }

  onError(callback: ErrorCallback): void {
    this.errorListeners.push(callback);
  }

  offError(callback: ErrorCallback): void {
    this.errorListeners = this.errorListeners.filter((cb) => cb !== callback);
  }

  onClose(callback: CloseCallback): void {
    this.closeListeners.push(callback);
  }

  offClose(callback: CloseCallback): void {
    this.closeListeners = this.closeListeners.filter((cb) => cb !== callback);
  }

  onMessage(callback: MessageCallback): void {
    this.messageListeners.push(callback);
  }

  offMessage(callback: MessageCallback): void {
    this.messageListeners = this.messageListeners.filter((cb) => cb !== callback);
  }

  private notifyStateChange(state: AvatarState): void {
    for (const callback of this.stateChangeListeners) {
      try {
        callback(state);
      } catch (error) {
        console.error('[BlenderConnection] Error in state change listener:', error);
      }
    }
  }

  private notifyEquippedChange(equipped: EquippedItems): void {
    for (const callback of this.equippedChangeListeners) {
      try {
        callback(equipped);
      } catch (error) {
        console.error('[BlenderConnection] Error in equipped change listener:', error);
      }
    }
  }

  private notifyError(error: Error): void {
    for (const callback of this.errorListeners) {
      try {
        callback(error);
      } catch (e) {
        console.error('[BlenderConnection] Error in error listener:', e);
      }
    }
  }

  private notifyClose(code: number, reason: string): void {
    for (const callback of this.closeListeners) {
      try {
        callback(code, reason);
      } catch (error) {
        console.error('[BlenderConnection] Error in close listener:', error);
      }
    }
  }

  private notifyMessage(message: BlenderResponse): void {
    for (const callback of this.messageListeners) {
      try {
        callback(message);
      } catch (error) {
        console.error('[BlenderConnection] Error in message listener:', error);
      }
    }
  }

  // ===========================================================================
  // Command Methods
  // ===========================================================================

  private sendCommand(command: string, params: Record<string, unknown> = {}): Promise<BlenderResponse> {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('Not connected to Blender server'));
        return;
      }

      const requestId = ++this.requestIdCounter;
      const message: BlenderMessage = {
        requestId: requestId.toString(),
        command,
        ...params,
      };

      this.pendingRequests.set(requestId, (response: BlenderResponse) => {
        if (response.error) {
          reject(new Error(response.error));
        } else if (response.status === 'error') {
          reject(new Error(response.message || 'Unknown error'));
        } else {
          resolve(response);
        }
      });

      try {
        this.ws.send(JSON.stringify(message));
        
        // Set timeout for response
        setTimeout(() => {
          if (this.pendingRequests.has(requestId)) {
            this.pendingRequests.delete(requestId);
            reject(new Error('Request timeout'));
          }
        }, 10000); // 10 second timeout
      } catch (error) {
        this.pendingRequests.delete(requestId);
        reject(error);
      }
    });
  }

  /**
   * Build the avatar rig.
   */
  async buildAvatar(): Promise<BlenderResponse> {
    return this.sendCommand('build_avatar');
  }

  /**
   * Equip an item in a slot.
   * @param slot The slot name (e.g., 'Back', 'Hand')
   * @param itemId The ID of the item to equip
   */
  async equip(slot: string, itemId: string): Promise<BlenderResponse> {
    return this.sendCommand('equip', { slot, itemId });
  }

  /**
   * Unequip an item from a slot.
   * @param slot The slot name (e.g., 'Back', 'Hand')
   */
  async unequip(slot: string): Promise<BlenderResponse> {
    return this.sendCommand('unequip', { slot });
  }

  /**
   * Get the current avatar state.
   */
  async getState(): Promise<BlenderResponse & { state?: AvatarState }> {
    return this.sendCommand('get_state') as Promise<BlenderResponse & { state?: AvatarState }>;
  }

  /**
   * Get currently equipped items.
   */
  async getEquipped(): Promise<BlenderResponse & { equipped?: EquippedItems }> {
    return this.sendCommand('get_equipped') as Promise<BlenderResponse & { equipped?: EquippedItems }>;
  }

  /**
   * Reload the zoxel accessories module.
   */
  async reload(): Promise<BlenderResponse> {
    return this.sendCommand('reload');
  }

  /**
   * Execute arbitrary Python code in Blender.
   * WARNING: Only use with trusted code as it can perform dangerous operations.
   * @param code Python code to execute
   */
  async execute(code: string): Promise<BlenderResponse> {
    return this.sendCommand('execute', { code });
  }

  /**
   * Ping the server to check connection.
   */
  async ping(): Promise<BlenderResponse> {
    return this.sendCommand('ping');
  }

  // ===========================================================================
  // Utility Methods
  // ===========================================================================

  /**
   * Check server status via HTTP.
   */
  async checkStatus(httpUrl: string = 'http://localhost:8081'): Promise<ServerStatus> {
    try {
      const response = await fetch(`${httpUrl}/api/status`);
      return await response.json() as ServerStatus;
    } catch (error) {
      return {
        status: 'error',
        blender: false,
        zoxel: false,
      };
    }
  }

  /**
   * Get avatar state via HTTP.
   */
  async getStateHttp(httpUrl: string = 'http://localhost:8081'): Promise<AvatarState> {
    try {
      const response = await fetch(`${httpUrl}/api/state`);
      return await response.json() as AvatarState;
    } catch (error) {
      throw new Error(`Failed to get state: ${error}`);
    }
  }

  /**
   * Get equipped items via HTTP.
   */
  async getEquippedHttp(httpUrl: string = 'http://localhost:8081'): Promise<EquippedItems> {
    try {
      const response = await fetch(`${httpUrl}/api/equipped`);
      const data = await response.json();
      return data.equipped as EquippedItems;
    } catch (error) {
      throw new Error(`Failed to get equipped items: ${error}`);
    }
  }
}

// =============================================================================
// Singleton Instance
// =============================================================================

let defaultConnection: BlenderConnection | null = null;

/**
 * Get the default Blender connection instance.
 */
export function getDefaultConnection(url?: string): BlenderConnection {
  if (!defaultConnection) {
    defaultConnection = new BlenderConnection(url);
  }
  return defaultConnection;
}

/**
 * Connect the default Blender connection.
 */
export async function connectDefault(url?: string): Promise<BlenderConnection> {
  const conn = getDefaultConnection(url);
  await conn.connect();
  return conn;
}

/**
 * Disconnect the default Blender connection.
 */
export function disconnectDefault(): void {
  if (defaultConnection) {
    defaultConnection.disconnect();
    defaultConnection = null;
  }
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Create a connection with automatic reconnection.
 */
export function createPersistentConnection(url: string = 'ws://localhost:8080'): BlenderConnection {
  const connection = new BlenderConnection(url);
  
  // Auto-reconnect on close
  connection.onClose((code, reason) => {
    console.log(`Connection closed (${code}: ${reason}), reconnecting...`);
    setTimeout(() => {
      connection.connect(true).catch(console.error);
    }, 1000);
  });
  
  return connection;
}

export default BlenderConnection;
