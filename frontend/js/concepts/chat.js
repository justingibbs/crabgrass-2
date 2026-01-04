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
     * @param {string} [options.ideaId] - The idea ID (for idea-based chats)
     * @param {string} [options.objectiveId] - The objective ID (for objective-based chats)
     * @param {string} [options.fileType] - The kernel file type (for kernel file agents)
     * @param {string} [options.agentType] - The agent type (for idea-level agents like coherence, context, objective)
     * @param {string} [options.contextFileId] - The context file ID (for context agent)
     * @param {Function} [options.onCompletionChange] - Callback when completion status changes
     */
    constructor(container, options) {
        this.container = container;
        this.ideaId = options.ideaId || null;
        this.objectiveId = options.objectiveId || null;
        this.fileType = options.fileType || null;
        this.agentType = options.agentType || null;
        this.contextFileId = options.contextFileId || null;
        this.onCompletionChange = options.onCompletionChange;

        // Determine chat type
        this.isCoherenceChat = this.agentType === 'coherence';
        this.isContextChat = this.agentType === 'context';
        this.isObjectiveChat = this.agentType === 'objective';

        // State
        this.messages = [];
        this.sessionId = null;
        this.sessions = []; // List of available sessions
        this.isLoading = false;
        this.error = null;
        this.agentName = AGENT_NAMES[this.agentType || this.fileType] || 'Agent';
        this._pendingNewSession = false; // Track if next message should create new session

        this.render();
        this._loadSessions();
    }

    /**
     * Get the current state.
     */
    get state() {
        return {
            messages: this.messages,
            sessionId: this.sessionId,
            sessions: this.sessions,
            isLoading: this.isLoading,
            error: this.error,
        };
    }

    /**
     * Load available sessions and the most recent one.
     * @private
     */
    async _loadSessions() {
        try {
            let response;
            if (this.isObjectiveChat) {
                response = await apiClient.getObjectiveSessions(this.objectiveId);
            } else if (this.isCoherenceChat) {
                response = await apiClient.getCoherenceSessions(this.ideaId);
            } else if (this.isContextChat) {
                // Context files don't have a sessions list endpoint yet
                // Start fresh each time - sessions will be created on first message
                this.sessions = [];
                return;
            } else {
                response = await apiClient.getSessions(this.ideaId, this.fileType);
            }

            if (response.sessions && response.sessions.length > 0) {
                this.sessions = response.sessions;
                // Load the most recent session
                await this.loadSession(response.sessions[0].id);
            } else {
                this.sessions = [];
            }
            this.render();
        } catch (error) {
            console.log('No sessions found, starting fresh');
            this.sessions = [];
        }
    }

    /**
     * Start a new session (clears current chat).
     */
    startNewSession() {
        this.sessionId = null;
        this.messages = [];
        this.error = null;
        this._pendingNewSession = true; // Force new session on next message
        this.render();
    }

    /**
     * Refresh the sessions list without changing current session.
     * @private
     */
    async _refreshSessionsList() {
        try {
            let response;
            if (this.isObjectiveChat) {
                response = await apiClient.getObjectiveSessions(this.objectiveId);
            } else if (this.isCoherenceChat) {
                response = await apiClient.getCoherenceSessions(this.ideaId);
            } else if (this.isContextChat) {
                return; // Context files don't have sessions list
            } else {
                response = await apiClient.getSessions(this.ideaId, this.fileType);
            }

            if (response.sessions) {
                this.sessions = response.sessions;
                this.render();
            }
        } catch (error) {
            console.log('Failed to refresh sessions list:', error);
        }
    }

    /**
     * Load a session with its messages.
     * @param {string} sessionId - The session ID to load
     */
    async loadSession(sessionId) {
        try {
            // For objective chats, we use the objectiveId; for idea chats, we use ideaId
            const entityId = this.objectiveId || this.ideaId;
            const response = await apiClient.getSessionWithMessages(entityId, sessionId);
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
            // Check if we need to force a new session
            const createNew = this._pendingNewSession;
            this._pendingNewSession = false; // Reset the flag

            let response;
            if (this.isObjectiveChat) {
                response = await apiClient.sendObjectiveChatMessage(
                    this.objectiveId,
                    message,
                    this.sessionId,
                    createNew
                );
            } else if (this.isCoherenceChat) {
                response = await apiClient.sendCoherenceChatMessage(
                    this.ideaId,
                    message,
                    this.sessionId,
                    createNew
                );
            } else if (this.isContextChat) {
                response = await apiClient.sendContextChatMessage(
                    this.ideaId,
                    this.contextFileId,
                    message,
                    this.sessionId,
                    createNew
                );
            } else {
                response = await apiClient.sendChatMessage(
                    this.ideaId,
                    this.fileType,
                    message,
                    this.sessionId,
                    createNew
                );
            }

            // Store session ID for future messages
            const wasNewSession = createNew;
            this.sessionId = response.session_id;

            // Add agent response
            this.messages.push({
                role: 'agent',
                content: response.response,
                timestamp: new Date(),
            });

            // Notify if completion status changed (only for kernel file agents)
            if (!this.isCoherenceChat && !this.isContextChat && response.is_complete && this.onCompletionChange) {
                this.onCompletionChange(true);
            }

            this.isLoading = false;
            this.render();

            // Refresh sessions list if we created a new session
            if (wasNewSession) {
                this._refreshSessionsList();
            }

        } catch (error) {
            console.error('Chat error:', error);
            this.error = error.message;
            this.isLoading = false;
            this.render();
        }
    }

    /**
     * Render the sessions dropdown.
     * @private
     */
    _renderSessionsDropdown() {
        if (this.isContextChat) {
            // Context chats don't support session switching
            return '';
        }

        const sessionOptions = this.sessions.map(session => {
            const isSelected = session.id === this.sessionId;
            const title = session.title || this._formatSessionDate(session.created_at);
            return `<option value="${session.id}" ${isSelected ? 'selected' : ''}>${title}</option>`;
        }).join('');

        return `
            <div class="chat-sessions-dropdown">
                <select class="chat-session-select">
                    <option value="new">+ New Session</option>
                    ${sessionOptions}
                </select>
            </div>
        `;
    }

    /**
     * Format a session date for display.
     * @private
     */
    _formatSessionDate(dateStr) {
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString([], { month: 'short', day: 'numeric' }) +
                   ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch {
            return 'Session';
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
                    ${this._renderSessionsDropdown()}
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

        // Session dropdown
        const sessionSelect = this.container.querySelector('.chat-session-select');
        if (sessionSelect) {
            sessionSelect.addEventListener('change', async (e) => {
                const value = e.target.value;
                if (value === 'new') {
                    this.startNewSession();
                } else {
                    await this.loadSession(value);
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
