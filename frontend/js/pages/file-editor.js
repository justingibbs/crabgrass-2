/**
 * File Editor Page
 *
 * 50/50 layout with chat placeholder (left) and canvas (right).
 * Supports editing kernel files with save/cancel functionality.
 */

import { Canvas } from '../concepts/canvas.js';
import { apiClient } from '../api/client.js';

// Mapping of kernel file types to display names
const FILE_DISPLAY_NAMES = {
    summary: 'Summary.md',
    challenge: 'Challenge.md',
    approach: 'Approach.md',
    coherent_steps: 'CoherentSteps.md',
};

/**
 * File Editor - manages the file editing page
 */
export class FileEditor {
    /**
     * Create a FileEditor instance.
     * @param {HTMLElement} container - The container element
     * @param {string} ideaId - The idea ID
     * @param {string} fileType - The kernel file type
     */
    constructor(container, ideaId, fileType) {
        this.container = container;
        this.ideaId = ideaId;
        this.fileType = fileType;
        this.displayName = FILE_DISPLAY_NAMES[fileType] || fileType;

        // State
        this.kernelFile = null;
        this.canvas = null;
        this.isLoading = true;
        this.isSaving = false;
        this.error = null;

        this.render();
    }

    /**
     * Load the kernel file data.
     */
    async load() {
        this.isLoading = true;
        this.error = null;
        this.render();

        try {
            this.kernelFile = await apiClient.getKernelFile(this.ideaId, this.fileType);
            this.isLoading = false;
            this.render();

            // Initialize canvas with content
            this._initCanvas();
        } catch (error) {
            console.error('Failed to load kernel file:', error);
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
            initialContent: this.kernelFile.content,
            onChange: (content, isDirty) => {
                this._updateSaveButtonState(isDirty);
            },
        });
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

        const content = this.canvas.state.content;

        this.isSaving = true;
        this._updateSaveButtonState(true);

        try {
            await apiClient.updateKernelFile(this.ideaId, this.fileType, content);

            // Update original content so isDirty becomes false
            this.canvas.load(content);

            // Navigate back to workspace
            window.location.hash = `#/ideas/${this.ideaId}`;
        } catch (error) {
            console.error('Failed to save kernel file:', error);
            alert(`Failed to save: ${error.message}`);
            this.isSaving = false;
            this._updateSaveButtonState(true);
        }
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
        window.location.hash = `#/ideas/${this.ideaId}`;
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
                        <a href="#/ideas/${this.ideaId}" class="back-link">← Back to Idea</a>
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

        const completionIcon = this.kernelFile.is_complete ? '●' : '○';
        const completionClass = this.kernelFile.is_complete ? 'complete' : 'incomplete';

        this.container.innerHTML = `
            <div class="file-editor">
                <div class="file-editor-header">
                    <a href="#/ideas/${this.ideaId}" class="back-link">← Back to Idea</a>
                    <div class="file-editor-title">
                        <h1>${this.displayName}</h1>
                        <span class="file-completion-status ${completionClass}" title="${this.kernelFile.is_complete ? 'Complete' : 'Incomplete'}">
                            ${completionIcon}
                        </span>
                    </div>
                    <div class="file-editor-actions-top">
                        <button class="btn btn-ghost file-editor-history" disabled title="History (coming soon)">
                            History
                        </button>
                    </div>
                </div>

                <div class="file-editor-body">
                    <div class="file-editor-chat">
                        <div class="chat-placeholder">
                            <div class="chat-placeholder-icon">💬</div>
                            <h3>Agent Chat</h3>
                            <p>AI coaching will be available in Slice 5.</p>
                        </div>
                    </div>
                    <div class="file-editor-canvas">
                        <!-- Canvas will be mounted here -->
                    </div>
                </div>

                <div class="file-editor-footer">
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
