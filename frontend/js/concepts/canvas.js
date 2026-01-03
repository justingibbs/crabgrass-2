/**
 * Canvas Concept
 *
 * Manages the markdown editor state and rendering.
 * Supports toggle mode between Edit and Preview.
 */

import { renderMarkdown } from '../lib/markdown.js';

/**
 * Canvas - markdown editor with edit/preview toggle
 */
export class Canvas {
    /**
     * Create a Canvas instance.
     * @param {HTMLElement} container - The container element
     * @param {Object} options - Configuration options
     * @param {string} options.initialContent - Initial content to display
     * @param {function} options.onSave - Callback when save is triggered
     * @param {function} options.onCancel - Callback when cancel is triggered
     * @param {function} options.onChange - Callback when content changes
     */
    constructor(container, options = {}) {
        this.container = container;
        this.options = options;

        // State
        this.originalContent = options.initialContent || '';
        this.content = this.originalContent;
        this.mode = 'edit'; // 'edit' or 'preview'
        this.isDirty = false;

        this.render();
    }

    /**
     * Get current state.
     */
    get state() {
        return {
            content: this.content,
            originalContent: this.originalContent,
            mode: this.mode,
            isDirty: this.isDirty,
        };
    }

    /**
     * Load new content into the canvas.
     * @param {string} content - The content to load
     */
    load(content) {
        this.originalContent = content;
        this.content = content;
        this.isDirty = false;
        this.render();
    }

    /**
     * Update the current content.
     * @param {string} newContent - The new content
     */
    updateContent(newContent) {
        this.content = newContent;
        this.isDirty = this.content !== this.originalContent;

        // Notify change listener
        if (this.options.onChange) {
            this.options.onChange(this.content, this.isDirty);
        }

        // Update dirty indicator without full re-render
        this._updateDirtyIndicator();
    }

    /**
     * Switch between edit and preview modes.
     * @param {string} mode - 'edit' or 'preview'
     */
    setMode(mode) {
        if (mode !== this.mode) {
            this.mode = mode;
            this.render();
        }
    }

    /**
     * Toggle between edit and preview modes.
     */
    toggleMode() {
        this.setMode(this.mode === 'edit' ? 'preview' : 'edit');
    }

    /**
     * Save the current content.
     * Emits canvas:save event and calls onSave callback.
     */
    save() {
        // Emit event for synchronization
        this.container.dispatchEvent(
            new CustomEvent('canvas:save', {
                detail: { content: this.content },
                bubbles: true,
            })
        );

        // Call callback if provided
        if (this.options.onSave) {
            this.options.onSave(this.content);
        }
    }

    /**
     * Cancel editing and revert to original content.
     */
    cancel() {
        // If dirty, could show confirmation here
        this.content = this.originalContent;
        this.isDirty = false;

        // Emit event
        this.container.dispatchEvent(
            new CustomEvent('canvas:cancel', {
                detail: {},
                bubbles: true,
            })
        );

        // Call callback if provided
        if (this.options.onCancel) {
            this.options.onCancel();
        }
    }

    /**
     * Check if there are unsaved changes.
     * @returns {boolean}
     */
    hasUnsavedChanges() {
        return this.isDirty;
    }

    /**
     * Render the canvas.
     */
    render() {
        this.container.innerHTML = `
            <div class="canvas">
                <div class="canvas-tabs">
                    <button class="canvas-tab ${this.mode === 'edit' ? 'active' : ''}" data-mode="edit">
                        Edit
                    </button>
                    <button class="canvas-tab ${this.mode === 'preview' ? 'active' : ''}" data-mode="preview">
                        Preview
                    </button>
                    <span class="canvas-dirty-indicator ${this.isDirty ? 'visible' : ''}" title="Unsaved changes">
                        ●
                    </span>
                </div>
                <div class="canvas-content">
                    ${this.mode === 'edit' ? this._renderEditor() : this._renderPreview()}
                </div>
            </div>
        `;

        this._attachEventListeners();
    }

    /**
     * Render the editor (edit mode).
     * @private
     */
    _renderEditor() {
        return `
            <textarea
                class="canvas-editor"
                placeholder="Start writing..."
                spellcheck="true"
            >${this._escapeHtml(this.content)}</textarea>
        `;
    }

    /**
     * Render the preview (preview mode).
     * @private
     */
    _renderPreview() {
        const html = renderMarkdown(this.content);
        return `
            <div class="canvas-preview markdown-body">
                ${html || '<p class="canvas-empty">Nothing to preview</p>'}
            </div>
        `;
    }

    /**
     * Attach event listeners.
     * @private
     */
    _attachEventListeners() {
        // Tab buttons
        const tabs = this.container.querySelectorAll('.canvas-tab');
        tabs.forEach((tab) => {
            tab.addEventListener('click', (e) => {
                const mode = e.target.dataset.mode;
                if (mode) {
                    this.setMode(mode);
                }
            });
        });

        // Textarea input
        const textarea = this.container.querySelector('.canvas-editor');
        if (textarea) {
            textarea.addEventListener('input', (e) => {
                this.updateContent(e.target.value);
            });

            // Auto-focus in edit mode
            textarea.focus();

            // Handle keyboard shortcuts
            textarea.addEventListener('keydown', (e) => {
                // Cmd/Ctrl + S to save
                if ((e.metaKey || e.ctrlKey) && e.key === 's') {
                    e.preventDefault();
                    this.save();
                }
            });
        }
    }

    /**
     * Update dirty indicator without full re-render.
     * @private
     */
    _updateDirtyIndicator() {
        const indicator = this.container.querySelector('.canvas-dirty-indicator');
        if (indicator) {
            if (this.isDirty) {
                indicator.classList.add('visible');
            } else {
                indicator.classList.remove('visible');
            }
        }
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
