/**
 * Canvas Concept
 *
 * Manages the WYSIWYG markdown editor state and rendering.
 * Uses Quill for rich text editing with Markdown ↔ HTML conversion.
 */

import { createEditor } from '../lib/editor.js';
import { parseMarkdown, serializeAst } from '../lib/markdown-ast.js';
import { CanvasToolbar } from '../components/canvas-toolbar.js';
import { SelectionPopup } from '../components/selection-popup.js';

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
     * @param {function} options.onSelectionAction - Callback when selection action is submitted
     * @param {Object} options.sseClient - SSE client for real-time updates
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
        this.selectionPopup = null;

        // Agent edit state
        this.pendingEdits = new Map();
        this.isProcessingEdit = false;

        // Parse initial AST
        this.ast = parseMarkdown(this.originalContent);

        this.render();
        this._initEditor();
        this._initSelectionPopup();
        this._initSSEHandler();
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
     * Initialize the selection popup for AI actions.
     * @private
     */
    _initSelectionPopup() {
        this.selectionPopup = new SelectionPopup({
            onSubmit: async (selection, instruction) => {
                if (this.options.onSelectionAction) {
                    await this.options.onSelectionAction(selection, instruction);
                }
            },
            onClose: () => {
                // Clear selection when popup closes
            },
        });

        // Listen for selection changes in the editor
        document.addEventListener('selectionchange', this._handleSelectionChange.bind(this));
    }

    /**
     * Initialize SSE event handlers for agent edits.
     * @private
     */
    _initSSEHandler() {
        const sseClient = this.options.sseClient;
        if (!sseClient) return;

        // Handle complete edits
        sseClient.on('agent_edit', (data) => {
            this._applyAgentEdit(data);
        });

        // Handle streaming edit start - show working indicator
        sseClient.on('agent_edit_stream_start', (data) => {
            this._showWorkingIndicator(data);
        });

        // Handle streaming edit end - hide working indicator (edit applied via agent_edit)
        sseClient.on('agent_edit_stream_end', (data) => {
            this._hideWorkingIndicator(data.edit_id);
        });
    }

    /**
     * Handle selection change events.
     * @private
     */
    _handleSelectionChange() {
        if (!this.editor || !this.isInitialized) return;

        // Don't show popup if selection popup is already processing
        if (this.selectionPopup && this.selectionPopup.isProcessing) return;

        const selection = window.getSelection();
        if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
            // No selection or empty selection
            return;
        }

        // Check if selection is within our editor
        const range = selection.getRangeAt(0);
        const editorEl = this.container.querySelector('.ql-editor');
        if (!editorEl || !editorEl.contains(range.commonAncestorContainer)) {
            return;
        }

        // Get the selected text
        const selectedText = selection.toString().trim();
        if (!selectedText || selectedText.length < 2) {
            return;
        }

        // Get position for popup (below selection)
        const rect = range.getBoundingClientRect();
        const position = {
            x: rect.left + rect.width / 2,
            y: rect.bottom,
        };

        // Show popup after a small delay to avoid flickering
        clearTimeout(this._selectionTimeout);
        this._selectionTimeout = setTimeout(() => {
            // Re-check selection is still valid
            const currentSelection = window.getSelection();
            if (!currentSelection || currentSelection.isCollapsed) {
                return;
            }

            // Get markdown position of selection (recalculate to ensure freshness)
            const markdownSelection = this._getMarkdownSelection();
            if (!markdownSelection) {
                console.warn('Canvas: Could not map selection to markdown positions');
                return;
            }

            this.selectionPopup.show(markdownSelection, position);
        }, 300);
    }

    /**
     * Get the current selection as markdown character positions.
     * @private
     * @returns {Object|null} { start, end, text } or null
     */
    _getMarkdownSelection() {
        if (!this.editor) return null;

        const selection = window.getSelection();
        if (!selection || selection.isCollapsed) return null;

        const text = selection.toString();
        if (!text.trim()) return null;

        // Get the current markdown content
        const markdown = this.editor.getContent();
        const selectedText = text.trim();

        // Strategy 1: Try exact match first
        let start = markdown.indexOf(selectedText);
        if (start !== -1) {
            return {
                start,
                end: start + selectedText.length,
                text: selectedText,
            };
        }

        // Strategy 2: Try with normalized whitespace (single spaces, newlines to spaces)
        const normalizedText = text.replace(/\s+/g, ' ').trim();
        const normalizedMarkdown = markdown.replace(/\s+/g, ' ');
        const normalizedStart = normalizedMarkdown.indexOf(normalizedText);

        if (normalizedStart !== -1) {
            // Map normalized position back to original markdown
            // Count characters in original up to the normalized position
            let originalPos = 0;
            let normalizedPos = 0;
            while (normalizedPos < normalizedStart && originalPos < markdown.length) {
                if (/\s/.test(markdown[originalPos])) {
                    // Skip consecutive whitespace in original
                    while (originalPos < markdown.length && /\s/.test(markdown[originalPos])) {
                        originalPos++;
                    }
                    normalizedPos++; // One space in normalized
                } else {
                    originalPos++;
                    normalizedPos++;
                }
            }

            // Find the end position similarly
            const endNormalized = normalizedStart + normalizedText.length;
            let endOriginal = originalPos;
            while (normalizedPos < endNormalized && endOriginal < markdown.length) {
                if (/\s/.test(markdown[endOriginal])) {
                    while (endOriginal < markdown.length && /\s/.test(markdown[endOriginal])) {
                        endOriginal++;
                    }
                    normalizedPos++;
                } else {
                    endOriginal++;
                    normalizedPos++;
                }
            }

            return {
                start: originalPos,
                end: endOriginal,
                text: markdown.slice(originalPos, endOriginal),
            };
        }

        // Strategy 3: Try line-by-line matching for multi-line selections
        const selectedLines = selectedText.split(/\n/).map(l => l.trim()).filter(l => l);
        if (selectedLines.length > 0) {
            const firstLine = selectedLines[0];
            const lastLine = selectedLines[selectedLines.length - 1];

            const firstLineStart = markdown.indexOf(firstLine);
            if (firstLineStart !== -1) {
                // Find the last line after the first
                const searchFrom = firstLineStart + firstLine.length;
                const lastLineStart = markdown.indexOf(lastLine, searchFrom);

                if (lastLineStart !== -1 || selectedLines.length === 1) {
                    const endPos = selectedLines.length === 1
                        ? firstLineStart + firstLine.length
                        : lastLineStart + lastLine.length;

                    return {
                        start: firstLineStart,
                        end: endPos,
                        text: markdown.slice(firstLineStart, endPos),
                    };
                }
            }
        }

        // Can't reliably determine position - return null instead of wrong position
        console.warn('Canvas: Could not determine selection position in markdown');
        return null;
    }

    /**
     * Apply an agent edit to the content.
     * @param {Object} data - Edit data { edit_id, file_path, operation, range, content }
     */
    _applyAgentEdit(data) {
        if (!this.editor) return;

        // Check if this edit is for us (match file_path)
        // file_path will be like "kernel/challenge" or "context/{id}"
        // The file-editor should check this, but we'll just apply
        const { operation, range, content } = data;

        // Get current markdown content
        const currentMarkdown = this.editor.getContent();

        let newMarkdown;
        if (operation === 'replace' && range) {
            const [start, end] = range;
            newMarkdown =
                currentMarkdown.slice(0, start) +
                content +
                currentMarkdown.slice(end);
        } else if (operation === 'insert' && range) {
            const [start] = range;
            newMarkdown =
                currentMarkdown.slice(0, start) +
                content +
                currentMarkdown.slice(start);
        } else if (operation === 'delete' && range) {
            const [start, end] = range;
            newMarkdown =
                currentMarkdown.slice(0, start) +
                currentMarkdown.slice(end);
        } else {
            // Append if no range
            newMarkdown = currentMarkdown + content;
        }

        // Store cursor position
        // Apply the new content
        this.editor.setContent(newMarkdown);

        // Update our state
        this.content = newMarkdown;
        this.ast = parseMarkdown(newMarkdown);
        this.isDirty = this.content !== this.originalContent;
        this._updateDirtyIndicator();

        // Show highlight on the edited region
        if (range) {
            this._showEditHighlight(range[0], range[0] + content.length);
        }

        // Notify change listener
        if (this.options.onChange) {
            this.options.onChange(this.content, this.isDirty);
        }

        // Hide working indicator
        this._hideWorkingIndicator(data.edit_id);
    }

    /**
     * Show a working indicator for a pending edit.
     * @private
     * @param {Object} data - Stream start data
     */
    _showWorkingIndicator(data) {
        this.pendingEdits.set(data.edit_id, data);

        // Add working class to canvas
        const canvas = this.container.querySelector('.canvas');
        if (canvas) {
            canvas.classList.add('canvas-edit-working');
        }
    }

    /**
     * Hide the working indicator for an edit.
     * @private
     * @param {string} editId
     */
    _hideWorkingIndicator(editId) {
        this.pendingEdits.delete(editId);

        // Remove working class if no more pending edits
        if (this.pendingEdits.size === 0) {
            const canvas = this.container.querySelector('.canvas');
            if (canvas) {
                canvas.classList.remove('canvas-edit-working');
            }
        }
    }

    /**
     * Show a highlight on the edited region.
     * @private
     * @param {number} start - Start position in markdown
     * @param {number} end - End position in markdown
     */
    _showEditHighlight(start, end) {
        // For now, flash the whole canvas content area
        // A more sophisticated implementation would highlight the exact range
        const contentArea = this.container.querySelector('.canvas-content');
        if (contentArea) {
            contentArea.classList.add('agent-edit-highlight');
            setTimeout(() => {
                contentArea.classList.add('fade-out');
                setTimeout(() => {
                    contentArea.classList.remove('agent-edit-highlight', 'fade-out');
                }, 1000);
            }, 100);
        }
    }

    /**
     * Clean up the canvas and editor.
     */
    destroy() {
        if (this._keydownHandler) {
            this.container.removeEventListener('keydown', this._keydownHandler);
        }

        if (this._selectionTimeout) {
            clearTimeout(this._selectionTimeout);
        }

        document.removeEventListener('selectionchange', this._handleSelectionChange);

        if (this.selectionPopup) {
            this.selectionPopup.destroy();
        }

        if (this.toolbar) {
            this.toolbar.destroy();
        }

        if (this.editor) {
            this.editor.destroy();
        }
    }
}
