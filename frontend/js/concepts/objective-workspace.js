/**
 * ObjectiveWorkspace Concept
 *
 * Manages the objective workspace view including:
 * - Objective header with editable title (admin only)
 * - ObjectiveAgent chat
 * - Objective file (single file per objective)
 * - Linked ideas section
 * - Context files section
 */

import { apiClient } from '../api/client.js';
import { Chat } from './chat.js';

export class ObjectiveWorkspace {
    /**
     * @param {HTMLElement} containerEl - Container element to render into
     * @param {string} objectiveId - ID of the objective to display
     */
    constructor(containerEl, objectiveId) {
        this.container = containerEl;
        this.objectiveId = objectiveId;
        this.objective = null;
        this.objectiveFile = null;
        this.linkedIdeas = [];
        this.contextFiles = [];
        this.isAdmin = false;
        this.loading = true;
        this.error = null;
        this.titleSaveTimeout = null;

        // Child concepts
        this.objectiveChat = null;
    }

    /**
     * Load objective data from API.
     */
    async load() {
        this.loading = true;
        this.error = null;
        this.render();

        try {
            // Check if current user is admin
            const user = await apiClient.getCurrentUser();
            this.isAdmin = user.role === 'org_admin';

            // Load objective data in parallel
            const [objective, ideasResponse, fileResponse, contextFilesResponse] = await Promise.all([
                apiClient.getObjective(this.objectiveId),
                apiClient.getObjectiveIdeas(this.objectiveId).catch(() => ({ ideas: [] })),
                apiClient.getObjectiveFile(this.objectiveId).catch(() => null),
                apiClient.getObjectiveContextFiles(this.objectiveId).catch(() => ({ files: [] })),
            ]);

            this.objective = objective;
            this.linkedIdeas = ideasResponse.ideas || [];
            this.objectiveFile = fileResponse;
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
        // Initialize ObjectiveAgent Chat
        const objectiveChatContainer = document.getElementById('objective-chat-container');
        if (objectiveChatContainer) {
            this.objectiveChat = new Chat(objectiveChatContainer, {
                objectiveId: this.objectiveId,
                agentType: 'objective',
            });
        }
    }

    /**
     * Update the objective title with debounced auto-save (admin only).
     * @param {string} newTitle - New title value
     */
    updateTitle(newTitle) {
        if (!this.objective || !this.isAdmin) return;

        // Clear any pending save
        if (this.titleSaveTimeout) {
            clearTimeout(this.titleSaveTimeout);
        }

        // Update local state immediately
        this.objective.title = newTitle;

        // Debounce the API call
        this.titleSaveTimeout = setTimeout(async () => {
            try {
                await apiClient.updateObjective(this.objectiveId, { title: newTitle });
                console.log('Objective title saved:', newTitle);
            } catch (err) {
                console.error('Failed to save objective title:', err);
            }
        }, 500);
    }

    /**
     * Navigate to idea workspace.
     * @param {string} ideaId - Idea ID
     */
    openIdea(ideaId) {
        window.location.hash = `#/ideas/${ideaId}`;
    }

    /**
     * Open objective file editor.
     */
    openObjectiveFile() {
        window.location.hash = `#/objectives/${this.objectiveId}/file`;
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
     * Format file size for display.
     * @private
     */
    _formatFileSize(bytes) {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }

    /**
     * Render linked ideas section.
     * @private
     */
    _renderLinkedIdeas() {
        if (!this.linkedIdeas || this.linkedIdeas.length === 0) {
            return `
                <div class="empty-state">
                    <p>No ideas linked to this objective yet.</p>
                </div>
            `;
        }

        return `
            <div class="linked-ideas-grid">
                ${this.linkedIdeas.map(idea => this._renderLinkedIdeaCard(idea)).join('')}
            </div>
        `;
    }

    /**
     * Render a linked idea card.
     * @private
     */
    _renderLinkedIdeaCard(idea) {
        return `
            <div class="linked-idea-card" data-idea-id="${this.escapeHtml(idea.id)}">
                <div class="linked-idea-header">
                    <span class="linked-idea-title">${this.escapeHtml(idea.title)}</span>
                    <span class="idea-status status-${idea.status}">${idea.status}</span>
                </div>
                <div class="linked-idea-meta">
                    <span class="kernel-count">${idea.kernel_completion || 0}/4 kernel files</span>
                    <span class="updated-at">Updated ${this._formatDate(idea.updated_at)}</span>
                </div>
            </div>
        `;
    }

    /**
     * Render context files section.
     * @private
     */
    _renderContextFiles() {
        if (!this.contextFiles || this.contextFiles.length === 0) {
            return `
                <div class="empty-state">
                    <p>No context files yet. ${this.isAdmin ? 'Add supporting material for this objective.' : ''}</p>
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
     * Render a context file card.
     * @private
     */
    _renderContextFileCard(file) {
        return `
            <div class="context-file-card" data-file-id="${this.escapeHtml(file.id)}">
                <div class="context-file-header">
                    <span class="context-file-name">${this.escapeHtml(file.filename)}</span>
                </div>
                <div class="context-file-meta">
                    <span class="context-file-size">${this._formatFileSize(file.size_bytes)}</span>
                    <span class="context-file-updated">Updated ${this._formatDate(file.updated_at)}</span>
                </div>
            </div>
        `;
    }

    /**
     * Show create context file modal (admin only).
     * @private
     */
    _showCreateContextFileModal() {
        if (!this.isAdmin) {
            alert('Only admins can create context files for objectives.');
            return;
        }

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
                            placeholder="research-notes"
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

        filenameInput.focus();

        const validateFilename = (name) => {
            if (!name) return 'Filename is required';
            if (!/^[a-zA-Z0-9_-]+$/.test(name)) return 'Only letters, numbers, hyphens, and underscores allowed';
            const fullFilename = name + '.md';
            if (this.contextFiles.some(f => f.filename === fullFilename)) return 'A file with this name already exists';
            return null;
        };

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

        const closeModal = () => modal.remove();
        document.getElementById('close-create-modal').addEventListener('click', closeModal);
        document.getElementById('cancel-create-file').addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });

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
                const newFile = await apiClient.createObjectiveContextFile(this.objectiveId, filename, '');
                closeModal();
                window.location.hash = `#/objectives/${this.objectiveId}/context/${newFile.id}`;
            } catch (err) {
                errorEl.textContent = err.message || 'Failed to create file';
                errorEl.style.display = 'block';
                createBtn.disabled = false;
                createBtn.textContent = 'Create';
            }
        });

        filenameInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !createBtn.disabled) createBtn.click();
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        }, { once: true });
    }

    /**
     * Render the workspace.
     */
    render() {
        if (this.loading) {
            this.container.innerHTML = `
                <div class="workspace-loading">
                    <div class="loading">Loading objective...</div>
                </div>
            `;
            return;
        }

        if (this.error) {
            this.container.innerHTML = `
                <div class="workspace-error">
                    <div class="error-state">
                        <p>Failed to load objective: ${this.error}</p>
                        <a href="#/" class="button">← Back to Home</a>
                    </div>
                </div>
            `;
            return;
        }

        this.container.innerHTML = `
            <div class="objective-workspace">
                <!-- Header -->
                <div class="workspace-header">
                    <a href="#/" class="back-link">← Home</a>
                </div>

                <!-- Objective Info Section -->
                <div class="workspace-info-section">
                    <div class="workspace-title-row">
                        <input
                            type="text"
                            class="workspace-title-input"
                            id="objective-title-input"
                            value="${this.escapeHtml(this.objective.title)}"
                            placeholder="Untitled Objective"
                            ${!this.isAdmin ? 'disabled' : ''}
                        />
                        ${this.objective.timeframe ? `<span class="objective-timeframe-badge">${this.escapeHtml(this.objective.timeframe)}</span>` : ''}
                    </div>
                    <div class="workspace-meta-row">
                        <div class="workspace-status">
                            <span class="meta-label">Status:</span>
                            <span class="objective-status status-${this.objective.status}">${this.objective.status}</span>
                        </div>
                        <div class="workspace-ideas-count">
                            <span class="meta-label">Linked Ideas:</span>
                            <span class="meta-value">${this.linkedIdeas.length}</span>
                        </div>
                    </div>
                    ${this.objective.description ? `
                        <div class="workspace-description">
                            <p>${this.escapeHtml(this.objective.description)}</p>
                        </div>
                    ` : ''}
                </div>

                <!-- Divider -->
                <div class="workspace-divider"></div>

                <!-- ObjectiveAgent Chat Section -->
                <div class="workspace-section">
                    <div class="section-header">
                        <span class="section-title">Chat with Objective Agent</span>
                    </div>
                    <div id="objective-chat-container" class="objective-chat-container"></div>
                </div>

                <!-- Divider -->
                <div class="workspace-divider"></div>

                <!-- Objective File Section -->
                <div class="workspace-section">
                    <div class="section-header">
                        <span class="section-title">Objective</span>
                    </div>
                    <div class="objective-file-section">
                        ${this.objectiveFile ? `
                            <div class="objective-file-card" id="objective-file-card">
                                <div class="objective-file-name">Objective.md</div>
                                <div class="objective-file-meta">
                                    <span class="file-size">${this._formatFileSize(this.objectiveFile.size_bytes || 0)}</span>
                                    <span class="file-updated">Updated ${this._formatDate(this.objectiveFile.updated_at)}</span>
                                </div>
                            </div>
                        ` : `
                            <div class="empty-state">
                                <p>Objective file not found.</p>
                            </div>
                        `}
                    </div>
                </div>

                <!-- Divider -->
                <div class="workspace-divider"></div>

                <!-- Linked Ideas Section -->
                <div class="workspace-section">
                    <div class="section-header">
                        <span class="section-title">Linked Ideas</span>
                    </div>
                    ${this._renderLinkedIdeas()}
                </div>

                <!-- Divider -->
                <div class="workspace-divider"></div>

                <!-- Context Files Section -->
                <div class="workspace-section">
                    <div class="section-header">
                        <span class="section-title">Context Files</span>
                        ${this.isAdmin ? '<button class="add-file-button" id="add-context-file-btn">+ New File</button>' : ''}
                    </div>
                    ${this._renderContextFiles()}
                </div>

                ${this.isAdmin ? `
                    <!-- Divider -->
                    <div class="workspace-divider"></div>

                    <!-- Action Bar (Admin Only) -->
                    <div class="workspace-action-bar">
                        <button class="button button-secondary" id="archive-objective-btn">Archive Objective</button>
                    </div>
                ` : ''}
            </div>
        `;

        this.attachEventListeners();
    }

    /**
     * Attach event listeners.
     */
    attachEventListeners() {
        // Title input auto-save (admin only)
        const titleInput = document.getElementById('objective-title-input');
        if (titleInput && this.isAdmin) {
            titleInput.addEventListener('input', (e) => {
                this.updateTitle(e.target.value);
            });

            titleInput.addEventListener('blur', (e) => {
                if (this.titleSaveTimeout) {
                    clearTimeout(this.titleSaveTimeout);
                }
                this.updateTitle(e.target.value);
            });
        }

        // Objective file card click
        const objectiveFileCard = document.getElementById('objective-file-card');
        if (objectiveFileCard) {
            objectiveFileCard.addEventListener('click', () => {
                this.openObjectiveFile();
            });
        }

        // Linked idea cards
        const linkedIdeaCards = document.querySelectorAll('.linked-idea-card[data-idea-id]');
        linkedIdeaCards.forEach(card => {
            card.addEventListener('click', () => {
                this.openIdea(card.dataset.ideaId);
            });
        });

        // Add context file button (admin only)
        const addFileBtn = document.getElementById('add-context-file-btn');
        if (addFileBtn) {
            addFileBtn.addEventListener('click', () => {
                this._showCreateContextFileModal();
            });
        }

        // Context file cards
        const contextFileCards = document.querySelectorAll('.context-file-card[data-file-id]');
        contextFileCards.forEach(card => {
            card.addEventListener('click', () => {
                const fileId = card.dataset.fileId;
                window.location.hash = `#/objectives/${this.objectiveId}/context/${fileId}`;
            });
        });

        // Archive button (admin only)
        const archiveBtn = document.getElementById('archive-objective-btn');
        if (archiveBtn) {
            archiveBtn.addEventListener('click', async () => {
                if (confirm('Are you sure you want to archive this objective?')) {
                    try {
                        await apiClient.archiveObjective(this.objectiveId);
                        window.location.hash = '#/';
                    } catch (err) {
                        alert('Failed to archive objective: ' + err.message);
                    }
                }
            });
        }
    }
}
