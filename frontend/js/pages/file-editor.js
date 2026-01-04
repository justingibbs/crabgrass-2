/**
 * File Editor Page
 *
 * 50/50 layout with agent chat (left) and canvas (right).
 * Supports editing kernel files, context files, objective files, and objective context files.
 */

import { Canvas } from '../concepts/canvas.js';
import { Chat } from '../concepts/chat.js';
import { apiClient } from '../api/client.js';

// Mapping of kernel file types to display names
const KERNEL_FILE_DISPLAY_NAMES = {
    summary: 'Summary.md',
    challenge: 'Challenge.md',
    approach: 'Approach.md',
    coherent_steps: 'CoherentSteps.md',
};

/**
 * File Editor - manages the file editing page
 * Supports kernel files, context files, objective files, and objective context files.
 */
export class FileEditor {
    /**
     * Create a FileEditor instance.
     * @param {HTMLElement} container - The container element
     * @param {string} entityId - The idea ID or objective ID
     * @param {string} fileIdentifier - File type (kernel/objective) or file ID (context)
     * @param {string} mode - 'kernel', 'context', 'objective', or 'objective_context'
     */
    constructor(container, entityId, fileIdentifier, mode = 'kernel') {
        this.container = container;
        this.entityId = entityId;
        this.fileIdentifier = fileIdentifier;
        this.mode = mode;

        // Determine file type
        this.isKernelFile = mode === 'kernel';
        this.isContextFile = mode === 'context';
        this.isObjectiveFile = mode === 'objective';
        this.isObjectiveContextFile = mode === 'objective_context';

        // For backwards compatibility
        this.ideaId = (this.isKernelFile || this.isContextFile) ? entityId : null;
        this.objectiveId = (this.isObjectiveFile || this.isObjectiveContextFile) ? entityId : null;

        // File identifiers
        this.fileType = this.isKernelFile ? fileIdentifier : null;
        this.fileId = (this.isContextFile || this.isObjectiveContextFile) ? fileIdentifier : null;

        // State
        this.file = null;
        this.displayName = '';
        this.canvas = null;
        this.chat = null;
        this.isLoading = true;
        this.isSaving = false;
        this.isDeleting = false;
        this.error = null;
        this.isAdmin = false;

        this.render();
    }

    /**
     * Load the file data.
     */
    async load() {
        this.isLoading = true;
        this.error = null;
        this.render();

        try {
            // Check admin status for objective files
            if (this.isObjectiveFile || this.isObjectiveContextFile) {
                const user = await apiClient.getCurrentUser();
                this.isAdmin = user.role === 'org_admin';
            }

            if (this.isKernelFile) {
                this.file = await apiClient.getKernelFile(this.ideaId, this.fileType);
                this.displayName = KERNEL_FILE_DISPLAY_NAMES[this.fileType] || this.fileType;
            } else if (this.isContextFile) {
                this.file = await apiClient.getContextFileById(this.ideaId, this.fileId);
                this.displayName = this.file.filename;
            } else if (this.isObjectiveFile) {
                this.file = await apiClient.getObjectiveFile(this.objectiveId);
                this.displayName = 'Objective.md';
            } else if (this.isObjectiveContextFile) {
                this.file = await apiClient.getObjectiveContextFileById(this.objectiveId, this.fileId);
                this.displayName = this.file.filename;
            }

            this.isLoading = false;
            this.render();

            // Initialize canvas with content
            this._initCanvas();

            // Initialize chat component
            this._initChat();
        } catch (error) {
            console.error('Failed to load file:', error);
            this.error = error.message;
            this.isLoading = false;
            this.render();
        }
    }

    /**
     * Initialize the canvas component.
     * @private
     */
    _initCanvas() {
        const canvasContainer = this.container.querySelector('.file-editor-canvas');
        if (!canvasContainer) return;

        this.canvas = new Canvas(canvasContainer, {
            initialContent: this.file.content,
            onChange: (content, isDirty) => {
                this._updateSaveButtonState(isDirty);
            },
        });
    }

    /**
     * Initialize the chat component.
     * @private
     */
    _initChat() {
        const chatContainer = this.container.querySelector('.file-editor-chat');
        if (!chatContainer) return;

        if (this.isKernelFile) {
            // Kernel file: use the file type's agent
            this.chat = new Chat(chatContainer, {
                ideaId: this.ideaId,
                fileType: this.fileType,
                onCompletionChange: (isComplete) => {
                    this._updateCompletionStatus(isComplete);
                },
            });
        } else if (this.isContextFile) {
            // Context file: use ContextAgent
            this.chat = new Chat(chatContainer, {
                ideaId: this.ideaId,
                agentType: 'context',
                contextFileId: this.fileId,
            });
        } else if (this.isObjectiveFile) {
            // Objective file: use ObjectiveAgent
            this.chat = new Chat(chatContainer, {
                objectiveId: this.objectiveId,
                agentType: 'objective',
            });
        } else if (this.isObjectiveContextFile) {
            // Objective context file: use ObjectiveAgent (same as objective file)
            this.chat = new Chat(chatContainer, {
                objectiveId: this.objectiveId,
                agentType: 'objective',
            });
        }
    }

    /**
     * Update the completion status display (kernel files only).
     * @private
     * @param {boolean} isComplete
     */
    _updateCompletionStatus(isComplete) {
        if (!this.isKernelFile) return;

        const statusEl = this.container.querySelector('.file-completion-status');
        if (statusEl) {
            statusEl.textContent = isComplete ? '●' : '○';
            statusEl.className = `file-completion-status ${isComplete ? 'complete' : 'incomplete'}`;
            statusEl.title = isComplete ? 'Complete' : 'Incomplete';
        }

        // Update the file state
        if (this.file) {
            this.file.is_complete = isComplete;
        }
    }

    /**
     * Update save button enabled state.
     * @private
     * @param {boolean} isDirty
     */
    _updateSaveButtonState(isDirty) {
        const saveButton = this.container.querySelector('.file-editor-save');
        if (saveButton) {
            saveButton.disabled = !isDirty || this.isSaving;
        }
    }

    /**
     * Handle save action.
     * @private
     */
    async _handleSave() {
        if (!this.canvas || this.isSaving) return;

        // Check admin status for objective files
        if ((this.isObjectiveFile || this.isObjectiveContextFile) && !this.isAdmin) {
            alert('Only admins can edit objective files.');
            return;
        }

        const content = this.canvas.state.content;

        this.isSaving = true;
        this._updateSaveButtonState(true);

        try {
            if (this.isKernelFile) {
                await apiClient.updateKernelFile(this.ideaId, this.fileType, content);
            } else if (this.isContextFile) {
                await apiClient.updateContextFile(this.ideaId, this.fileId, content);
            } else if (this.isObjectiveFile) {
                await apiClient.updateObjectiveFile(this.objectiveId, content);
            } else if (this.isObjectiveContextFile) {
                await apiClient.updateObjectiveContextFile(this.objectiveId, this.fileId, content);
            }

            // Update original content so isDirty becomes false
            this.canvas.load(content);

            // Navigate back to workspace
            this._navigateBack();
        } catch (error) {
            console.error('Failed to save file:', error);
            alert(`Failed to save: ${error.message}`);
            this.isSaving = false;
            this._updateSaveButtonState(true);
        }
    }

    /**
     * Navigate back to the appropriate workspace.
     * @private
     */
    _navigateBack() {
        if (this.isObjectiveFile || this.isObjectiveContextFile) {
            window.location.hash = `#/objectives/${this.objectiveId}`;
        } else {
            window.location.hash = `#/ideas/${this.ideaId}`;
        }
    }

    /**
     * Get the back link URL.
     * @private
     */
    _getBackLink() {
        if (this.isObjectiveFile || this.isObjectiveContextFile) {
            return `#/objectives/${this.objectiveId}`;
        }
        return `#/ideas/${this.ideaId}`;
    }

    /**
     * Get the back link text.
     * @private
     */
    _getBackLinkText() {
        if (this.isObjectiveFile || this.isObjectiveContextFile) {
            return '← Back to Objective';
        }
        return '← Back to Idea';
    }

    /**
     * Handle cancel action.
     * @private
     */
    _handleCancel() {
        if (this.canvas && this.canvas.hasUnsavedChanges()) {
            const confirmed = confirm('You have unsaved changes. Discard them?');
            if (!confirmed) return;
        }

        // Navigate back to workspace
        this._navigateBack();
    }

    /**
     * Handle delete action (context files only).
     * @private
     */
    async _handleDelete() {
        // Only allow deleting context files (not kernel or objective files)
        if (this.isKernelFile || this.isObjectiveFile || this.isDeleting) return;

        // Check admin status for objective context files
        if (this.isObjectiveContextFile && !this.isAdmin) {
            alert('Only admins can delete objective context files.');
            return;
        }

        const confirmed = confirm(`Delete "${this.displayName}"? This cannot be undone.`);
        if (!confirmed) return;

        this.isDeleting = true;
        const deleteBtn = this.container.querySelector('.file-editor-delete');
        if (deleteBtn) {
            deleteBtn.disabled = true;
            deleteBtn.textContent = 'Deleting...';
        }

        try {
            if (this.isContextFile) {
                await apiClient.deleteContextFile(this.ideaId, this.fileId);
            } else if (this.isObjectiveContextFile) {
                await apiClient.deleteObjectiveContextFile(this.objectiveId, this.fileId);
            }
            // Navigate back to workspace
            this._navigateBack();
        } catch (error) {
            console.error('Failed to delete file:', error);
            alert(`Failed to delete: ${error.message}`);
            this.isDeleting = false;
            if (deleteBtn) {
                deleteBtn.disabled = false;
                deleteBtn.textContent = 'Delete';
            }
        }
    }

    /**
     * Render the page.
     */
    render() {
        if (this.isLoading) {
            this.container.innerHTML = `
                <div class="file-editor">
                    <div class="file-editor-loading">
                        <p>Loading...</p>
                    </div>
                </div>
            `;
            return;
        }

        if (this.error) {
            this.container.innerHTML = `
                <div class="file-editor">
                    <div class="file-editor-header">
                        <a href="${this._getBackLink()}" class="back-link">${this._getBackLinkText()}</a>
                    </div>
                    <div class="file-editor-error">
                        <h2>Error</h2>
                        <p>${this._escapeHtml(this.error)}</p>
                        <button class="btn btn-primary" onclick="window.location.reload()">
                            Retry
                        </button>
                    </div>
                </div>
            `;
            return;
        }

        // Build completion status (kernel files only)
        let completionHtml = '';
        if (this.isKernelFile) {
            const completionIcon = this.file.is_complete ? '●' : '○';
            const completionClass = this.file.is_complete ? 'complete' : 'incomplete';
            completionHtml = `
                <span class="file-completion-status ${completionClass}" title="${this.file.is_complete ? 'Complete' : 'Incomplete'}">
                    ${completionIcon}
                </span>
            `;
        }

        // Build file badge for context files
        let badgeHtml = '';
        if (this.isContextFile || this.isObjectiveContextFile) {
            const badgeClass = this.file.created_by_agent ? 'badge-agent' : 'badge-user';
            const badgeText = this.file.created_by_agent ? 'AI Generated' : 'User Created';
            badgeHtml = `<span class="file-badge ${badgeClass}">${badgeText}</span>`;
        }

        // Build objective file badge
        if (this.isObjectiveFile) {
            badgeHtml = `<span class="file-badge badge-objective">Objective</span>`;
        }

        // Build delete button (context files only, not kernel or objective files)
        let deleteButtonHtml = '';
        if (this.isContextFile || this.isObjectiveContextFile) {
            const canDelete = this.isContextFile || (this.isObjectiveContextFile && this.isAdmin);
            deleteButtonHtml = `
                <button class="btn btn-danger file-editor-delete" ${!canDelete ? 'disabled' : ''}>
                    Delete
                </button>
            `;
        }

        // Check if user can edit (for objective files, admin only)
        const canEdit = !this.isObjectiveFile || this.isAdmin;
        const readOnlyNote = !canEdit ? '<span class="read-only-badge">Read Only</span>' : '';

        this.container.innerHTML = `
            <div class="file-editor">
                <div class="file-editor-header">
                    <a href="${this._getBackLink()}" class="back-link">${this._getBackLinkText()}</a>
                    <div class="file-editor-title">
                        <h1>${this._escapeHtml(this.displayName)}</h1>
                        ${completionHtml}
                        ${badgeHtml}
                        ${readOnlyNote}
                    </div>
                    <div class="file-editor-actions-top">
                        <button class="btn btn-ghost file-editor-history" disabled title="History (coming soon)">
                            History
                        </button>
                    </div>
                </div>

                <div class="file-editor-body">
                    <div class="file-editor-chat">
                        <!-- Chat component will be mounted here -->
                    </div>
                    <div class="file-editor-canvas">
                        <!-- Canvas will be mounted here -->
                    </div>
                </div>

                <div class="file-editor-footer">
                    ${deleteButtonHtml}
                    <div class="file-editor-footer-spacer"></div>
                    <button class="btn btn-ghost file-editor-cancel">
                        Cancel
                    </button>
                    <button class="btn btn-primary file-editor-save" disabled>
                        Save & Close
                    </button>
                </div>
            </div>
        `;

        this._attachEventListeners();
    }

    /**
     * Attach event listeners.
     * @private
     */
    _attachEventListeners() {
        // Cancel button
        const cancelButton = this.container.querySelector('.file-editor-cancel');
        if (cancelButton) {
            cancelButton.addEventListener('click', () => this._handleCancel());
        }

        // Save button
        const saveButton = this.container.querySelector('.file-editor-save');
        if (saveButton) {
            saveButton.addEventListener('click', () => this._handleSave());
        }

        // Delete button (context files only)
        const deleteButton = this.container.querySelector('.file-editor-delete');
        if (deleteButton) {
            deleteButton.addEventListener('click', () => this._handleDelete());
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', this._handleKeydown.bind(this));
    }

    /**
     * Handle keyboard shortcuts.
     * @private
     * @param {KeyboardEvent} e
     */
    _handleKeydown(e) {
        // Cmd/Ctrl + S to save
        if ((e.metaKey || e.ctrlKey) && e.key === 's') {
            e.preventDefault();
            if (this.canvas && this.canvas.hasUnsavedChanges()) {
                this._handleSave();
            }
        }

        // Escape to cancel
        if (e.key === 'Escape') {
            this._handleCancel();
        }
    }

    /**
     * Clean up when leaving the page.
     */
    destroy() {
        document.removeEventListener('keydown', this._handleKeydown.bind(this));
    }

    /**
     * Escape HTML special characters.
     * @private
     * @param {string} text
     * @returns {string}
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
