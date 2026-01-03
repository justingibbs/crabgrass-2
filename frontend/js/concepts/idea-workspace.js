/**
 * IdeaWorkspace Concept
 *
 * Manages the idea workspace view including:
 * - Idea header with editable title
 * - Kernel completion status
 * - CoherenceAgent chat
 * - Kernel files grid
 * - Context files section
 */

import { apiClient } from '../api/client.js';
import { KernelStatus } from './kernel-status.js';
import { FileList } from './file-list.js';
import { Chat } from './chat.js';

export class IdeaWorkspace {
    /**
     * @param {HTMLElement} containerEl - Container element to render into
     * @param {string} ideaId - ID of the idea to display
     */
    constructor(containerEl, ideaId) {
        this.container = containerEl;
        this.ideaId = ideaId;
        this.idea = null;
        this.kernelFiles = [];
        this.contextFiles = [];
        this.loading = true;
        this.error = null;
        this.titleSaveTimeout = null;

        // Child concepts (initialized after first render)
        this.kernelStatus = null;
        this.fileList = null;
        this.coherenceChat = null;
    }

    /**
     * Load idea data from API.
     */
    async load() {
        this.loading = true;
        this.error = null;
        this.render();

        try {
            // Load idea and context files in parallel
            const [idea, contextFilesResponse] = await Promise.all([
                apiClient.getIdea(this.ideaId),
                apiClient.getContextFiles(this.ideaId).catch(() => ({ files: [] })),
            ]);

            this.idea = idea;
            this.kernelFiles = idea.kernel_files || [];
            this.contextFiles = contextFilesResponse.files || [];
            this.loading = false;
            this.render();
            this.initChildConcepts();
        } catch (err) {
            this.error = err.message;
            this.loading = false;
            this.render();
        }
    }

    /**
     * Initialize child concepts after DOM is ready.
     */
    initChildConcepts() {
        // Initialize KernelStatus
        const statusContainer = document.getElementById('kernel-status-container');
        if (statusContainer) {
            this.kernelStatus = new KernelStatus(statusContainer, this.idea.kernel_completion);
        }

        // Initialize FileList
        const fileListContainer = document.getElementById('file-list-container');
        if (fileListContainer) {
            this.fileList = new FileList(fileListContainer, this.ideaId);
            this.fileList.load(this.kernelFiles);
        }

        // Initialize CoherenceAgent Chat
        const coherenceChatContainer = document.getElementById('coherence-chat-container');
        if (coherenceChatContainer) {
            this.coherenceChat = new Chat(coherenceChatContainer, {
                ideaId: this.ideaId,
                agentType: 'coherence',
            });
        }
    }

    /**
     * Update the idea title with debounced auto-save.
     * @param {string} newTitle - New title value
     */
    updateTitle(newTitle) {
        if (!this.idea) return;

        // Clear any pending save
        if (this.titleSaveTimeout) {
            clearTimeout(this.titleSaveTimeout);
        }

        // Update local state immediately
        this.idea.title = newTitle;

        // Debounce the API call
        this.titleSaveTimeout = setTimeout(async () => {
            try {
                await apiClient.updateIdea(this.ideaId, { title: newTitle });
                console.log('Title saved:', newTitle);
            } catch (err) {
                console.error('Failed to save title:', err);
            }
        }, 500);
    }

    /**
     * Escape HTML to prevent XSS.
     * @param {string} str - String to escape
     */
    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Render context files section.
     * @private
     */
    _renderContextFiles() {
        if (!this.contextFiles || this.contextFiles.length === 0) {
            return `
                <div class="empty-state">
                    <p>No context files yet. Add research, notes, or supporting material.</p>
                </div>
            `;
        }

        return `
            <div class="context-files-grid">
                ${this.contextFiles.map(file => this._renderContextFileCard(file)).join('')}
            </div>
        `;
    }

    /**
     * Render a single context file card.
     * @private
     */
    _renderContextFileCard(file) {
        const isAgentGenerated = file.created_by_agent;
        const isFeedbackTasks = file.filename === 'feedback-tasks.md';
        const badgeClass = isAgentGenerated ? 'badge-agent' : 'badge-user';
        const badgeText = isAgentGenerated ? 'AI Generated' : 'User';

        return `
            <div class="context-file-card ${isFeedbackTasks ? 'feedback-tasks-card' : ''}"
                 data-filename="${this.escapeHtml(file.filename)}"
                 style="cursor: pointer;">
                <div class="context-file-header">
                    <span class="context-file-name">${this.escapeHtml(file.filename)}</span>
                    <span class="context-file-badge ${badgeClass}">${badgeText}</span>
                </div>
                <div class="context-file-meta">
                    <span class="context-file-size">${this._formatFileSize(file.size_bytes)}</span>
                    <span class="context-file-updated">Updated ${this._formatDate(file.updated_at)}</span>
                </div>
            </div>
        `;
    }

    /**
     * Open a context file in a modal.
     * @private
     */
    async _openContextFile(filename) {
        try {
            const file = await apiClient.getContextFile(this.ideaId, filename);
            this._showContextFileModal(file);
        } catch (err) {
            console.error('Failed to load context file:', err);
            alert(`Failed to load file: ${err.message}`);
        }
    }

    /**
     * Show modal with context file content.
     * @private
     */
    _showContextFileModal(file) {
        // Remove existing modal if any
        const existingModal = document.getElementById('context-file-modal');
        if (existingModal) {
            existingModal.remove();
        }

        const modal = document.createElement('div');
        modal.id = 'context-file-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content context-file-modal-content">
                <div class="modal-header">
                    <h2>${this.escapeHtml(file.filename)}</h2>
                    <button class="modal-close" id="close-context-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <pre class="context-file-content">${this.escapeHtml(file.content)}</pre>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Close handlers
        const closeModal = () => modal.remove();
        document.getElementById('close-context-modal').addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        }, { once: true });
    }

    /**
     * Format file size for display.
     * @private
     */
    _formatFileSize(bytes) {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }

    /**
     * Format date for display.
     * @private
     */
    _formatDate(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    }

    /**
     * Render the workspace.
     */
    render() {
        if (this.loading) {
            this.container.innerHTML = `
                <div class="workspace-loading">
                    <div class="loading">Loading idea...</div>
                </div>
            `;
            return;
        }

        if (this.error) {
            this.container.innerHTML = `
                <div class="workspace-error">
                    <div class="error-state">
                        <p>Failed to load idea: ${this.error}</p>
                        <a href="#/" class="button">← Back to Home</a>
                    </div>
                </div>
            `;
            return;
        }

        this.container.innerHTML = `
            <div class="idea-workspace">
                <!-- Header -->
                <div class="workspace-header">
                    <a href="#/" class="back-link">← Home</a>
                </div>

                <!-- Idea Info Section -->
                <div class="workspace-info-section">
                    <div class="workspace-title-row">
                        <input
                            type="text"
                            class="workspace-title-input"
                            id="idea-title-input"
                            value="${this.escapeHtml(this.idea.title)}"
                            placeholder="Untitled Idea"
                        />
                        <div id="kernel-status-container"></div>
                    </div>
                    <div class="workspace-meta-row">
                        <div class="workspace-objective">
                            <span class="meta-label">Objective:</span>
                            <span class="meta-value">
                                ${this.idea.objective_id ? 'Linked' : 'Not selected'}
                            </span>
                            <button class="link-button" disabled>Select</button>
                        </div>
                        <div class="workspace-status">
                            <span class="meta-label">Status:</span>
                            <span class="idea-status status-${this.idea.status}">${this.idea.status}</span>
                        </div>
                    </div>
                    <div class="workspace-collaborators">
                        <span class="collaborator-badge">👤 You (Owner)</span>
                        <button class="share-button" disabled>Share ▼</button>
                    </div>
                </div>

                <!-- Divider -->
                <div class="workspace-divider"></div>

                <!-- CoherenceAgent Chat Section -->
                <div class="workspace-section">
                    <div class="section-header">
                        <span class="section-title">Chat with Coherence Agent</span>
                    </div>
                    <div id="coherence-chat-container" class="coherence-chat-container"></div>
                </div>

                <!-- Divider -->
                <div class="workspace-divider"></div>

                <!-- Kernel Files Section -->
                <div class="workspace-section">
                    <div class="section-header">
                        <span class="section-title">Kernel Files</span>
                    </div>
                    <div id="file-list-container"></div>
                </div>

                <!-- Divider -->
                <div class="workspace-divider"></div>

                <!-- Context Files Section -->
                <div class="workspace-section">
                    <div class="section-header">
                        <span class="section-title">Context Files</span>
                        <button class="add-file-button" disabled>+ New File</button>
                    </div>
                    ${this._renderContextFiles()}
                </div>

                <!-- Divider -->
                <div class="workspace-divider"></div>

                <!-- Action Bar -->
                <div class="workspace-action-bar">
                    <button class="button button-secondary" disabled>Archive</button>
                    <button class="button button-primary" disabled>Publish → Active</button>
                </div>
            </div>
        `;

        this.attachEventListeners();
    }

    /**
     * Attach event listeners.
     */
    attachEventListeners() {
        // Title input auto-save
        const titleInput = document.getElementById('idea-title-input');
        if (titleInput) {
            titleInput.addEventListener('input', (e) => {
                this.updateTitle(e.target.value);
            });

            // Save on blur
            titleInput.addEventListener('blur', (e) => {
                if (this.titleSaveTimeout) {
                    clearTimeout(this.titleSaveTimeout);
                }
                this.updateTitle(e.target.value);
            });
        }

        // Context file card clicks
        const contextFileCards = document.querySelectorAll('.context-file-card[data-filename]');
        contextFileCards.forEach(card => {
            card.addEventListener('click', () => {
                const filename = card.dataset.filename;
                this._openContextFile(filename);
            });
        });
    }
}
