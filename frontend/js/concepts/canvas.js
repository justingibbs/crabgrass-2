/**
 * Canvas Concept
 *
 * Manages the WYSIWYG markdown editor state and rendering.
 * Uses Quill for rich text editing with Markdown ↔ HTML conversion.
 */

import { createEditor } from '../lib/editor.js';
import { parseMarkdown, serializeAst } from '../lib/markdown-ast.js';
import { CanvasToolbar } from '../components/canvas-toolbar.js';

/**
 * Canvas - WYSIWYG markdown editor
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
        this.ast = null;
        this.isDirty = false;
        this.isInitialized = false;

        // Editor instances
        this.editor = null;
        this.toolbar = null;

        // Parse initial AST
        this.ast = parseMarkdown(this.originalContent);

        this.render();
        this._initEditor();
    }

    /**
     * Get current state.
     */
    get state() {
        return {
            content: this.content,
            originalContent: this.originalContent,
            ast: this.ast,
            isDirty: this.isDirty,
            isInitialized: this.isInitialized,
        };
    }

    /**
     * Load new content into the canvas.
     * @param {string} content - The content to load
     */
    load(content) {
        this.originalContent = content;
        this.content = content;
        this.ast = parseMarkdown(content);
        this.isDirty = false;

        if (this.editor) {
            this.editor.setContent(content);
        }

        this._updateDirtyIndicator();
    }

    /**
     * Update the current content.
     * @param {string} newContent - The new content
     */
    updateContent(newContent) {
        this.content = newContent;
        this.ast = parseMarkdown(newContent);
        this.isDirty = this.content !== this.originalContent;

        // Notify change listener
        if (this.options.onChange) {
            this.options.onChange(this.content, this.isDirty);
        }

        this._updateDirtyIndicator();
    }

    /**
     * Save the current content.
     * Emits canvas:save event and calls onSave callback.
     */
    save() {
        // Get the latest content from the editor
        if (this.editor) {
            this.content = this.editor.getContent();
        }

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
        this.ast = parseMarkdown(this.originalContent);
        this.isDirty = false;

        if (this.editor) {
            this.editor.setContent(this.originalContent);
        }

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
     * Focus the editor.
     */
    focus() {
        if (this.editor) {
            this.editor.focus();
        }
    }

    /**
     * Render the canvas structure.
     */
    render() {
        this.container.innerHTML = `
            <div class="canvas">
                <div class="canvas-toolbar-container">
                    <!-- Toolbar will be mounted here -->
                </div>
                <div class="canvas-content">
                    <div class="canvas-editor-container">
                        <!-- Editor will be mounted here -->
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Initialize the Milkdown editor.
     * @private
     */
    async _initEditor() {
        const editorContainer = this.container.querySelector('.canvas-editor-container');
        const toolbarContainer = this.container.querySelector('.canvas-toolbar-container');

        if (!editorContainer || !toolbarContainer) {
            console.error('Canvas: Could not find editor or toolbar container');
            return;
        }

        try {
            // Create the toolbar first (without editor)
            this.toolbar = new CanvasToolbar(toolbarContainer);

            // Add dirty indicator to toolbar
            const toolbarEl = toolbarContainer.querySelector('.canvas-toolbar');
            if (toolbarEl) {
                const indicator = document.createElement('span');
                indicator.className = 'canvas-dirty-indicator';
                indicator.title = 'Unsaved changes';
                indicator.textContent = '\u25CF'; // Bullet character
                toolbarEl.appendChild(indicator);
            }

            // Create the editor
            this.editor = await createEditor({
                container: editorContainer,
                initialContent: this.originalContent,
                onChange: (markdown) => {
                    this.updateContent(markdown);
                },
                onFocus: () => {
                    this.container.querySelector('.canvas')?.classList.add('focused');
                },
                onBlur: () => {
                    this.container.querySelector('.canvas')?.classList.remove('focused');
                },
            });

            // Connect toolbar to editor
            this.toolbar.setEditor(this.editor);

            // Set up keyboard shortcut for save (Cmd+S)
            this._setupSaveShortcut();

            this.isInitialized = true;

            // Focus the editor
            this.editor.focus();
        } catch (error) {
            console.error('Canvas: Failed to initialize editor:', error);
            // Fall back to textarea mode
            this._renderFallbackEditor(editorContainer);
        }
    }

    /**
     * Set up Cmd+S keyboard shortcut for save.
     * @private
     */
    _setupSaveShortcut() {
        this._keydownHandler = (e) => {
            // Cmd/Ctrl + S to save
            if ((e.metaKey || e.ctrlKey) && e.key === 's') {
                e.preventDefault();
                this.save();
            }
        };

        this.container.addEventListener('keydown', this._keydownHandler);
    }

    /**
     * Render a fallback textarea editor (if Milkdown fails to load).
     * @private
     * @param {HTMLElement} container
     */
    _renderFallbackEditor(container) {
        container.innerHTML = `
            <textarea
                class="canvas-fallback-editor"
                placeholder="Start writing..."
                spellcheck="true"
            >${this._escapeHtml(this.content)}</textarea>
        `;

        const textarea = container.querySelector('textarea');
        if (textarea) {
            textarea.addEventListener('input', (e) => {
                this.updateContent(e.target.value);
            });

            textarea.addEventListener('keydown', (e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === 's') {
                    e.preventDefault();
                    this.save();
                }
            });

            textarea.focus();
        }

        this.isInitialized = true;
    }

    /**
     * Update dirty indicator visibility.
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

    /**
     * Clean up the canvas and editor.
     */
    destroy() {
        if (this._keydownHandler) {
            this.container.removeEventListener('keydown', this._keydownHandler);
        }

        if (this.toolbar) {
            this.toolbar.destroy();
        }

        if (this.editor) {
            this.editor.destroy();
        }
    }
}
