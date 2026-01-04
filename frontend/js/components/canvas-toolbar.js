/**
 * Canvas Toolbar Component
 *
 * Provides formatting controls for the Quill WYSIWYG canvas editor.
 */

/**
 * Toolbar button configuration.
 */
const TOOLBAR_BUTTONS = [
    {
        id: 'bold',
        label: 'B',
        title: 'Bold (Cmd+B)',
        format: 'bold',
        shortcut: { key: 'b', meta: true },
    },
    {
        id: 'italic',
        label: 'I',
        title: 'Italic (Cmd+I)',
        format: 'italic',
        shortcut: { key: 'i', meta: true },
        className: 'italic',
    },
    { type: 'separator' },
    {
        id: 'h1',
        label: 'H1',
        title: 'Heading 1',
        format: 'header',
        value: 1,
    },
    {
        id: 'h2',
        label: 'H2',
        title: 'Heading 2',
        format: 'header',
        value: 2,
    },
    {
        id: 'h3',
        label: 'H3',
        title: 'Heading 3',
        format: 'header',
        value: 3,
    },
    { type: 'separator' },
    {
        id: 'bullet-list',
        label: '•',
        title: 'Bullet List',
        format: 'list',
        value: 'bullet',
    },
    {
        id: 'ordered-list',
        label: '1.',
        title: 'Numbered List',
        format: 'list',
        value: 'ordered',
    },
    { type: 'separator' },
    {
        id: 'blockquote',
        label: '"',
        title: 'Quote',
        format: 'blockquote',
        value: true,
    },
    {
        id: 'code',
        label: '</>',
        title: 'Code',
        format: 'code-block',
        value: true,
    },
];

/**
 * Canvas Toolbar - formatting controls for the editor
 */
export class CanvasToolbar {
    /**
     * Create a CanvasToolbar instance.
     * @param {HTMLElement} container - The container element for the toolbar
     * @param {Object} options - Configuration options
     * @param {Object} options.editor - The editor API object
     */
    constructor(container, options = {}) {
        this.container = container;
        this.editor = options.editor || null;
        this._keydownHandler = null;

        this.render();
        this._setupKeyboardShortcuts();
    }

    /**
     * Set the editor instance (can be set after construction).
     * @param {Object} editor - The editor API object
     */
    setEditor(editor) {
        this.editor = editor;
    }

    /**
     * Execute a toolbar format command.
     * @param {string} format - The Quill format name
     * @param {*} [value] - The format value
     */
    executeFormat(format, value) {
        if (!this.editor || !this.editor.instance) {
            console.warn('No editor instance available');
            return;
        }

        try {
            const quill = this.editor.instance;

            // Toggle behavior for boolean formats
            if (value === true || value === undefined) {
                const currentFormat = quill.getFormat();
                const isActive = currentFormat[format];
                quill.format(format, !isActive);
            } else {
                // For formats with values (like header level), toggle off if same value
                const currentFormat = quill.getFormat();
                if (currentFormat[format] === value) {
                    quill.format(format, false);
                } else {
                    quill.format(format, value);
                }
            }

            // Refocus the editor after format
            this.editor.focus();
        } catch (error) {
            console.error('Failed to execute format:', format, error);
        }
    }

    /**
     * Set up keyboard shortcuts for toolbar commands.
     * @private
     */
    _setupKeyboardShortcuts() {
        this._keydownHandler = (e) => {
            // Only handle if meta/ctrl key is pressed
            if (!e.metaKey && !e.ctrlKey) return;

            const button = TOOLBAR_BUTTONS.find(
                (btn) =>
                    btn.shortcut &&
                    btn.shortcut.key === e.key.toLowerCase() &&
                    ((btn.shortcut.meta && (e.metaKey || e.ctrlKey)) || !btn.shortcut.meta)
            );

            if (button && button.format) {
                e.preventDefault();
                this.executeFormat(button.format, button.value);
            }
        };

        document.addEventListener('keydown', this._keydownHandler);
    }

    /**
     * Render the toolbar.
     */
    render() {
        const buttonsHtml = TOOLBAR_BUTTONS.map((btn) => {
            if (btn.type === 'separator') {
                return '<span class="toolbar-separator"></span>';
            }

            const className = `toolbar-button ${btn.className || ''}`;
            return `
                <button
                    class="${className}"
                    data-format="${btn.format}"
                    data-value="${btn.value !== undefined ? btn.value : ''}"
                    title="${btn.title}"
                    type="button"
                >
                    ${btn.label}
                </button>
            `;
        }).join('');

        this.container.innerHTML = `
            <div class="canvas-toolbar">
                ${buttonsHtml}
            </div>
        `;

        this._attachEventListeners();
    }

    /**
     * Attach event listeners.
     * @private
     */
    _attachEventListeners() {
        const buttons = this.container.querySelectorAll('.toolbar-button');
        buttons.forEach((button) => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const format = button.dataset.format;
                let value = button.dataset.value;

                // Parse value
                if (value === '') {
                    value = true;
                } else if (value === 'true') {
                    value = true;
                } else if (value === 'false') {
                    value = false;
                } else if (!isNaN(parseInt(value, 10))) {
                    value = parseInt(value, 10);
                }

                this.executeFormat(format, value);
            });

            // Prevent button from stealing focus from editor
            button.addEventListener('mousedown', (e) => {
                e.preventDefault();
            });
        });
    }

    /**
     * Clean up the toolbar.
     */
    destroy() {
        if (this._keydownHandler) {
            document.removeEventListener('keydown', this._keydownHandler);
        }
    }
}
