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
        this.objectives = []; // Available objectives for linking
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
            // Load idea, context files, and objectives in parallel
            const [idea, contextFilesResponse, objectivesResponse] = await Promise.all([
                apiClient.getIdea(this.ideaId),
                apiClient.getContextFiles(this.ideaId).catch(() => ({ files: [] })),
                apiClient.getObjectives().catch(() => ({ objectives: [] })),
            ]);

            this.idea = idea;
            this.kernelFiles = idea.kernel_files || [];
            this.contextFiles = contextFilesResponse.files || [];
            this.objectives = objectivesResponse.objectives || [];
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
     * Link this idea to an objective.
     * @param {string} objectiveId - The objective ID to link to
     */
    async linkToObjective(objectiveId) {
        try {
            await apiClient.linkIdeaToObjective(this.ideaId, objectiveId);
            this.idea.objective_id = objectiveId;
            this.render();
            this.initChildConcepts();
            console.log('Linked to objective:', objectiveId);
        } catch (err) {
            console.error('Failed to link to objective:', err);
            alert('Failed to link to objective: ' + err.message);
        }
    }

    /**
     * Unlink this idea from its current objective.
     */
    async unlinkFromObjective() {
        try {
            await apiClient.unlinkIdeaFromObjective(this.ideaId);
            this.idea.objective_id = null;
            this.render();
            this.initChildConcepts();
            console.log('Unlinked from objective');
        } catch (err) {
            console.error('Failed to unlink from objective:', err);
            alert('Failed to unlink from objective: ' + err.message);
        }
    }

    /**
     * Get the current linked objective.
     * @returns {Object|null} The linked objective or null
     */
    _getLinkedObjective() {
        if (!this.idea.objective_id) return null;
        return this.objectives.find(obj => obj.id === this.idea.objective_id) || null;
    }

    /**
     * Render the objective selector section.
     * @private
     */
    _renderObjectiveSelector() {
        const linkedObjective = this._getLinkedObjective();

        if (linkedObjective) {
            // Show linked objective with option to unlink
            return `
                <div class="workspace-objective">
                    <span class="meta-label">Objective:</span>
                    <a href="#/objectives/${linkedObjective.id}" class="objective-link">${this.escapeHtml(linkedObjective.title)}</a>
                    <button class="link-button" id="unlink-objective-btn">Unlink</button>
                </div>
            `;
        }

        // Show dropdown to select objective
        if (this.objectives.length === 0) {
            return `
                <div class="workspace-objective">
                    <span class="meta-label">Objective:</span>
                    <span class="meta-value">No objectives available</span>
                </div>
            `;
        }

        return `
            <div class="workspace-objective">
                <span class="meta-label">Objective:</span>
                <select id="objective-selector" class="objective-select">
                    <option value="">Select an objective...</option>
                    ${this.objectives.map(obj => `
                        <option value="${obj.id}">${this.escapeHtml(obj.title)}</option>
                    `).join('')}
                </select>
            </div>
        `;
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
                 data-file-id="${this.escapeHtml(file.id)}"
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
     * Navigate to context file editor.
     * @private
     */
    _openContextFile(fileId) {
        window.location.hash = `#/ideas/${this.ideaId}/context/${fileId}`;
    }

    /**
     * Show the create context file modal.
     * @private
     */
    _showCreateContextFileModal() {
        // Remove existing modal if any
        const existingModal = document.getElementById('create-context-file-modal');
        if (existingModal) {
            existingModal.remove();
        }

        const modal = document.createElement('div');
        modal.id = 'create-context-file-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content create-file-modal-content">
                <div class="modal-header">
                    <h2>Create Context File</h2>
                    <button class="modal-close" id="close-create-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <label for="context-filename-input">Filename</label>
                    <div class="filename-input-wrapper">
                        <input
                            type="text"
                            id="context-filename-input"
                            placeholder="my-research-notes"
                            class="filename-input"
                            pattern="[a-zA-Z0-9_-]+"
                        />
                        <span class="filename-extension">.md</span>
                    </div>
                    <p class="filename-hint">Use letters, numbers, hyphens, and underscores only.</p>
                    <p id="filename-error" class="filename-error" style="display: none;"></p>
                </div>
                <div class="modal-footer">
                    <button class="button button-secondary" id="cancel-create-file">Cancel</button>
                    <button class="button button-primary" id="confirm-create-file">Create</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        const filenameInput = document.getElementById('context-filename-input');
        const errorEl = document.getElementById('filename-error');
        const createBtn = document.getElementById('confirm-create-file');

        // Focus input
        filenameInput.focus();

        // Validation function
        const validateFilename = (name) => {
            if (!name) {
                return 'Filename is required';
            }
            if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
                return 'Only letters, numbers, hyphens, and underscores allowed';
            }
            const fullFilename = name + '.md';
            if (this.contextFiles.some(f => f.filename === fullFilename)) {
                return 'A file with this name already exists';
            }
            return null;
        };

        // Real-time validation
        filenameInput.addEventListener('input', () => {
            const error = validateFilename(filenameInput.value.trim());
            if (error) {
                errorEl.textContent = error;
                errorEl.style.display = 'block';
                createBtn.disabled = true;
            } else {
                errorEl.style.display = 'none';
                createBtn.disabled = false;
            }
        });

        // Close handlers
        const closeModal = () => modal.remove();
        document.getElementById('close-create-modal').addEventListener('click', closeModal);
        document.getElementById('cancel-create-file').addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });

        // Create handler
        createBtn.addEventListener('click', async () => {
            const baseName = filenameInput.value.trim();
            const error = validateFilename(baseName);
            if (error) {
                errorEl.textContent = error;
                errorEl.style.display = 'block';
                return;
            }

            const filename = baseName + '.md';
            createBtn.disabled = true;
            createBtn.textContent = 'Creating...';

            try {
                const newFile = await apiClient.createContextFile(this.ideaId, filename, '');
                closeModal();
                // Navigate to the new file's editor
                window.location.hash = `#/ideas/${this.ideaId}/context/${newFile.id}`;
            } catch (err) {
                errorEl.textContent = err.message || 'Failed to create file';
                errorEl.style.display = 'block';
                createBtn.disabled = false;
                createBtn.textContent = 'Create';
            }
        });

        // Enter key to submit
        filenameInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !createBtn.disabled) {
                createBtn.click();
            }
        });

        // Escape to close
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
                        ${this._renderObjectiveSelector()}
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
                        <button class="add-file-button" id="add-context-file-btn">+ New File</button>
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

        // Objective selector
        const objectiveSelector = document.getElementById('objective-selector');
        if (objectiveSelector) {
            objectiveSelector.addEventListener('change', (e) => {
                const objectiveId = e.target.value;
                if (objectiveId) {
                    this.linkToObjective(objectiveId);
                }
            });
        }

        // Unlink objective button
        const unlinkBtn = document.getElementById('unlink-objective-btn');
        if (unlinkBtn) {
            unlinkBtn.addEventListener('click', () => {
                this.unlinkFromObjective();
            });
        }

        // Add context file button
        const addFileBtn = document.getElementById('add-context-file-btn');
        if (addFileBtn) {
            addFileBtn.addEventListener('click', () => {
                this._showCreateContextFileModal();
            });
        }

        // Context file card clicks - navigate to editor
        const contextFileCards = document.querySelectorAll('.context-file-card[data-file-id]');
        contextFileCards.forEach(card => {
            card.addEventListener('click', () => {
                const fileId = card.dataset.fileId;
                this._openContextFile(fileId);
            });
        });
    }
}
