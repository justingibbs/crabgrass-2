/**
 * SSE (Server-Sent Events) client for real-time updates.
 */

const API_BASE = 'http://localhost:8000';

/**
 * SSE Client for subscribing to idea or objective events.
 */
export class SSEClient {
    /**
     * Create an SSE client.
     * @param {string} entityId - The idea or objective ID to subscribe to
     * @param {string} entityType - 'idea' or 'objective'
     */
    constructor(entityId, entityType = 'idea') {
        this.entityId = entityId;
        this.entityType = entityType;
        this.eventSource = null;
        this.listeners = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;

        // Streaming edit state
        this.pendingEdits = new Map(); // edit_id -> { chunks: [], ... }
    }

    // Backwards compatibility
    get ideaId() {
        return this.entityId;
    }

    /**
     * Connect to the SSE stream.
     */
    connect() {
        if (this.eventSource) {
            this.disconnect();
        }

        const endpoint = this.entityType === 'objective' ? 'objectives' : 'ideas';
        const url = `${API_BASE}/api/${endpoint}/${this.entityId}/events`;
        this.eventSource = new EventSource(url, { withCredentials: true });

        this.eventSource.onopen = () => {
            console.log('SSE connected:', this.entityType, this.entityId);
            this.reconnectAttempts = 0;
        };

        this.eventSource.onerror = (error) => {
            console.error('SSE error:', error);
            this._handleError();
        };

        // Listen for specific event types
        this.eventSource.addEventListener('connected', (event) => {
            const data = JSON.parse(event.data);
            this._emit('connected', data);
        });

        this.eventSource.addEventListener('completion_changed', (event) => {
            const data = JSON.parse(event.data);
            this._emit('completion_changed', data);
        });

        this.eventSource.addEventListener('file_saved', (event) => {
            const data = JSON.parse(event.data);
            this._emit('file_saved', data);
        });

        this.eventSource.addEventListener('agent_message', (event) => {
            const data = JSON.parse(event.data);
            this._emit('agent_message', data);
        });

        // Agent edit events
        this.eventSource.addEventListener('agent_edit', (event) => {
            const data = JSON.parse(event.data);
            this._emit('agent_edit', data);
        });

        // Streaming edit events
        this.eventSource.addEventListener('agent_edit_stream_start', (event) => {
            const data = JSON.parse(event.data);
            this.pendingEdits.set(data.edit_id, {
                ...data,
                chunks: [],
            });
            this._emit('agent_edit_stream_start', data);
        });

        this.eventSource.addEventListener('agent_edit_stream_chunk', (event) => {
            const data = JSON.parse(event.data);
            const pending = this.pendingEdits.get(data.edit_id);
            if (pending) {
                pending.chunks.push(data.content);
            }
            this._emit('agent_edit_stream_chunk', data);
        });

        this.eventSource.addEventListener('agent_edit_stream_end', (event) => {
            const data = JSON.parse(event.data);
            const pending = this.pendingEdits.get(data.edit_id);
            if (pending) {
                // Emit complete edit with all data
                this._emit('agent_edit', {
                    edit_id: data.edit_id,
                    file_path: pending.file_path,
                    operation: pending.operation,
                    range: pending.range,
                    content: data.final_content,
                });
                this.pendingEdits.delete(data.edit_id);
            }
            this._emit('agent_edit_stream_end', data);
        });
    }

    /**
     * Disconnect from the SSE stream.
     */
    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
            console.log('SSE disconnected:', this.ideaId);
        }
    }

    /**
     * Subscribe to an event type.
     * @param {string} eventType - The event type to listen for
     * @param {Function} callback - The callback function
     */
    on(eventType, callback) {
        if (!this.listeners.has(eventType)) {
            this.listeners.set(eventType, []);
        }
        this.listeners.get(eventType).push(callback);
    }

    /**
     * Unsubscribe from an event type.
     * @param {string} eventType - The event type
     * @param {Function} callback - The callback to remove
     */
    off(eventType, callback) {
        if (this.listeners.has(eventType)) {
            const callbacks = this.listeners.get(eventType);
            const index = callbacks.indexOf(callback);
            if (index !== -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    /**
     * Emit an event to all listeners.
     * @private
     */
    _emit(eventType, data) {
        const callbacks = this.listeners.get(eventType) || [];
        for (const callback of callbacks) {
            try {
                callback(data);
            } catch (error) {
                console.error('SSE listener error:', error);
            }
        }
    }

    /**
     * Handle connection errors with exponential backoff.
     * @private
     */
    _handleError() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            console.log(`SSE reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
            setTimeout(() => this.connect(), delay);
        } else {
            console.error('SSE max reconnect attempts reached');
            this._emit('error', { message: 'Connection lost' });
        }
    }
}

/**
 * Create an SSE client for an idea.
 * @param {string} ideaId - The idea ID
 * @returns {SSEClient}
 */
export function createSSEClient(ideaId) {
    return new SSEClient(ideaId, 'idea');
}

/**
 * Create an SSE client for an objective.
 * @param {string} objectiveId - The objective ID
 * @returns {SSEClient}
 */
export function createObjectiveSSEClient(objectiveId) {
    return new SSEClient(objectiveId, 'objective');
}

export default SSEClient;
