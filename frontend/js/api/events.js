/**
 * SSE (Server-Sent Events) client for real-time updates.
 */

const API_BASE = 'http://localhost:8000';

/**
 * SSE Client for subscribing to idea events.
 */
export class SSEClient {
    /**
     * Create an SSE client.
     * @param {string} ideaId - The idea ID to subscribe to
     */
    constructor(ideaId) {
        this.ideaId = ideaId;
        this.eventSource = null;
        this.listeners = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
    }

    /**
     * Connect to the SSE stream.
     */
    connect() {
        if (this.eventSource) {
            this.disconnect();
        }

        const url = `${API_BASE}/api/ideas/${this.ideaId}/events`;
        this.eventSource = new EventSource(url, { withCredentials: true });

        this.eventSource.onopen = () => {
            console.log('SSE connected:', this.ideaId);
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
    return new SSEClient(ideaId);
}

export default SSEClient;
