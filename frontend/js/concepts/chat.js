/**
 * Chat Concept - manages agent conversation UI.
 */

import { apiClient } from '../api/client.js';

// Agent display names
const AGENT_NAMES = {
    challenge: 'ChallengeAgent',
    summary: 'SummaryAgent',
    approach: 'ApproachAgent',
    steps: 'StepsAgent',
    coherent_steps: 'StepsAgent',
    coherence: 'CoherenceAgent',
    context: 'ContextAgent',
    objective: 'ObjectiveAgent',
};

/**
 * Chat component for agent conversations.
 */
export class Chat {
    /**
     * Create a Chat instance.
     * @param {HTMLElement} container - The container element
     * @param {Object} options - Configuration options
     * @param {string} options.ideaId - The idea ID
     * @param {string} [options.fileType] - The kernel file type (for kernel file agents)
     * @param {string} [options.agentType] - The agent type (for idea-level agents like coherence)
     * @param {Function} [options.onCompletionChange] - Callback when completion status changes
     */
    constructor(container, options) {
        this.container = container;
        this.ideaId = options.ideaId;
        this.fileType = options.fileType || null;
        this.agentType = options.agentType || null;
        this.onCompletionChange = options.onCompletionChange;

        // Determine if this is a coherence chat (idea-level) or file-level
        this.isCoherenceChat = this.agentType === 'coherence';

        // State
        this.messages = [];
        this.sessionId = null;
        this.isLoading = false;
        this.error = null;
        this.agentName = AGENT_NAMES[this.agentType || this.fileType] || 'Agent';

        this.render();
        this._loadExistingSession();
    }

    /**
     * Get the current state.
     */
    get state() {
        return {
            messages: this.messages,
            sessionId: this.sessionId,
            isLoading: this.isLoading,
            error: this.error,
        };
    }

    /**
     * Load an existing session if one exists.
     * @private
     */
    async _loadExistingSession() {
        try {
            let response;
            if (this.isCoherenceChat) {
                response = await apiClient.getCoherenceSessions(this.ideaId);
            } else {
                response = await apiClient.getSessions(this.ideaId, this.fileType);
            }
            if (response.sessions && response.sessions.length > 0) {
                // Load the most recent session
                const latestSession = response.sessions[0];
                await this.loadSession(latestSession.id);
            }
        } catch (error) {
            console.log('No existing session found, starting fresh');
        }
    }

    /**
     * Load a session with its messages.
     * @param {string} sessionId - The session ID to load
     */
    async loadSession(sessionId) {
        try {
            const response = await apiClient.getSessionWithMessages(this.ideaId, sessionId);
            this.sessionId = sessionId;
            this.messages = response.messages.map(m => ({
                role: m.role,
                content: m.content,
                timestamp: new Date(m.created_at),
            }));
            this.render();
        } catch (error) {
            console.error('Failed to load session:', error);
        }
    }

    /**
     * Send a message to the agent.
     * @param {string} message - The message to send
     */
    async send(message) {
        if (!message.trim() || this.isLoading) return;

        // Add user message immediately
        this.messages.push({
            role: 'user',
            content: message,
            timestamp: new Date(),
        });
        this.isLoading = true;
        this.error = null;
        this.render();

        try {
            let response;
            if (this.isCoherenceChat) {
                response = await apiClient.sendCoherenceChatMessage(
                    this.ideaId,
                    message,
                    this.sessionId
                );
            } else {
                response = await apiClient.sendChatMessage(
                    this.ideaId,
                    this.fileType,
                    message,
                    this.sessionId
                );
            }

            // Store session ID for future messages
            this.sessionId = response.session_id;

            // Add agent response
            this.messages.push({
                role: 'agent',
                content: response.response,
                timestamp: new Date(),
            });

            // Notify if completion status changed (only for kernel file agents)
            if (!this.isCoherenceChat && response.is_complete && this.onCompletionChange) {
                this.onCompletionChange(true);
            }

            this.isLoading = false;
            this.render();

        } catch (error) {
            console.error('Chat error:', error);
            this.error = error.message;
            this.isLoading = false;
            this.render();
        }
    }

    /**
     * Render the chat component.
     */
    render() {
        this.container.innerHTML = `
            <div class="chat">
                <div class="chat-header">
                    <span class="chat-agent-name">${this.agentName}</span>
                </div>
                <div class="chat-messages">
                    ${this._renderMessages()}
                    ${this._renderLoading()}
                    ${this._renderError()}
                </div>
                <div class="chat-input-container">
                    <textarea
                        class="chat-input"
                        placeholder="Ask ${this.agentName} for help..."
                        rows="2"
                        ${this.isLoading ? 'disabled' : ''}
                    ></textarea>
                    <button
                        class="btn btn-primary chat-send"
                        ${this.isLoading ? 'disabled' : ''}
                    >
                        Send
                    </button>
                </div>
            </div>
        `;

        this._attachEventListeners();
        this._scrollToBottom();
    }

    /**
     * Render messages.
     * @private
     */
    _renderMessages() {
        if (this.messages.length === 0) {
            return `
                <div class="chat-empty">
                    <p>Hi! I'm ${this.agentName}. I'll help you develop this section.</p>
                    <p class="chat-hint">Ask me questions or request feedback on your content.</p>
                </div>
            `;
        }

        return this.messages.map(msg => `
            <div class="chat-message chat-message-${msg.role}">
                <div class="chat-message-header">
                    <span class="chat-message-sender">
                        ${msg.role === 'user' ? 'You' : this.agentName}
                    </span>
                    <span class="chat-message-time">
                        ${this._formatTime(msg.timestamp)}
                    </span>
                </div>
                <div class="chat-message-content">
                    ${this._formatContent(msg.content)}
                </div>
            </div>
        `).join('');
    }

    /**
     * Render loading indicator.
     * @private
     */
    _renderLoading() {
        if (!this.isLoading) return '';
        return `
            <div class="chat-message chat-message-agent chat-loading">
                <div class="chat-message-content">
                    <span class="chat-typing">Thinking...</span>
                </div>
            </div>
        `;
    }

    /**
     * Render error message.
     * @private
     */
    _renderError() {
        if (!this.error) return '';
        return `
            <div class="chat-error">
                <p>Error: ${this._escapeHtml(this.error)}</p>
                <button class="btn btn-ghost chat-retry">Retry</button>
            </div>
        `;
    }

    /**
     * Format message content (basic markdown support).
     * @private
     */
    _formatContent(content) {
        // Basic escaping and formatting
        let formatted = this._escapeHtml(content);

        // Convert markdown-style formatting
        formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');
        formatted = formatted.replace(/`(.+?)`/g, '<code>$1</code>');

        // Convert line breaks
        formatted = formatted.replace(/\n/g, '<br>');

        return formatted;
    }

    /**
     * Format timestamp.
     * @private
     */
    _formatTime(date) {
        if (!date) return '';
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    /**
     * Escape HTML special characters.
     * @private
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Attach event listeners.
     * @private
     */
    _attachEventListeners() {
        const input = this.container.querySelector('.chat-input');
        const sendButton = this.container.querySelector('.chat-send');

        if (input && sendButton) {
            // Send on button click
            sendButton.addEventListener('click', () => {
                this.send(input.value);
                input.value = '';
            });

            // Send on Enter (Shift+Enter for newline)
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.send(input.value);
                    input.value = '';
                }
            });
        }

        // Retry button
        const retryButton = this.container.querySelector('.chat-retry');
        if (retryButton) {
            retryButton.addEventListener('click', () => {
                this.error = null;
                this.render();
            });
        }
    }

    /**
     * Scroll messages to bottom.
     * @private
     */
    _scrollToBottom() {
        const messagesContainer = this.container.querySelector('.chat-messages');
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
}

export default Chat;
