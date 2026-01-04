/**
 * Selection Popup Component
 *
 * A floating popup that appears when the user selects text in the canvas.
 * Allows the user to enter an instruction for the AI to modify the selection.
 */

/**
 * SelectionPopup - floating UI for selection actions
 */
export class SelectionPopup {
    /**
     * Create a SelectionPopup instance.
     * @param {Object} options - Configuration options
     * @param {Function} options.onSubmit - Callback when instruction is submitted (selection, instruction)
     * @param {Function} options.onClose - Callback when popup is closed
     */
    constructor(options = {}) {
        this.options = options;
        this.element = null;
        this.selection = null;
        this.isVisible = false;
        this.isProcessing = false;

        this._createPopup();
        this._attachEventListeners();
    }

    /**
     * Create the popup DOM element.
     * @private
     */
    _createPopup() {
        this.element = document.createElement('div');
        this.element.className = 'selection-popup';
        this.element.innerHTML = `
            <div class="selection-popup-content">
                <input
                    type="text"
                    class="selection-popup-input"
                    placeholder="How should AI modify this?"
                    autocomplete="off"
                    spellcheck="false"
                />
                <button class="selection-popup-submit" title="Submit (Enter)">
                    <span class="submit-icon">&#10148;</span>
                    <span class="submit-spinner"></span>
                </button>
            </div>
        `;

        // Initially hidden
        this.element.style.display = 'none';
        document.body.appendChild(this.element);
    }

    /**
     * Attach event listeners.
     * @private
     */
    _attachEventListeners() {
        const input = this.element.querySelector('.selection-popup-input');
        const submitBtn = this.element.querySelector('.selection-popup-submit');

        // Submit on Enter
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this._handleSubmit();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                this.hide();
            }
        });

        // Submit button click
        submitBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this._handleSubmit();
        });

        // Close on click outside
        document.addEventListener('mousedown', this._handleOutsideClick.bind(this));
    }

    /**
     * Handle click outside the popup.
     * @private
     * @param {MouseEvent} e
     */
    _handleOutsideClick(e) {
        if (this.isVisible && !this.element.contains(e.target)) {
            // Small delay to allow selection actions to complete
            setTimeout(() => {
                if (this.isVisible && !this.isProcessing) {
                    this.hide();
                }
            }, 100);
        }
    }

    /**
     * Handle form submission.
     * @private
     */
    async _handleSubmit() {
        if (this.isProcessing) return;

        const input = this.element.querySelector('.selection-popup-input');
        const instruction = input.value.trim();

        if (!instruction || !this.selection) {
            return;
        }

        this.setProcessing(true);

        try {
            if (this.options.onSubmit) {
                await this.options.onSubmit(this.selection, instruction);
            }
            // Hide on success
            this.hide();
        } catch (error) {
            console.error('Selection action failed:', error);
            this.setError(error.message || 'Failed to process');
            this.setProcessing(false);
        }
    }

    /**
     * Show the popup at a position.
     * @param {Object} selection - The selection {start, end, text}
     * @param {Object} position - The position {x, y}
     */
    show(selection, position) {
        this.selection = selection;
        this.isVisible = true;

        // Position the popup
        const popupWidth = 280;
        const popupHeight = 48;
        const padding = 10;

        // Ensure popup stays within viewport
        let x = position.x - popupWidth / 2;
        let y = position.y + padding;

        // Keep within horizontal bounds
        if (x < padding) x = padding;
        if (x + popupWidth > window.innerWidth - padding) {
            x = window.innerWidth - popupWidth - padding;
        }

        // Keep within vertical bounds
        if (y + popupHeight > window.innerHeight - padding) {
            y = position.y - popupHeight - padding;
        }

        this.element.style.left = `${x}px`;
        this.element.style.top = `${y}px`;
        this.element.style.display = 'block';

        // Reset state
        const input = this.element.querySelector('.selection-popup-input');
        input.value = '';
        this.element.classList.remove('error', 'processing');

        // Focus the input
        setTimeout(() => input.focus(), 10);
    }

    /**
     * Hide the popup.
     */
    hide() {
        this.isVisible = false;
        this.selection = null;
        this.isProcessing = false;
        this.element.style.display = 'none';
        this.element.classList.remove('error', 'processing');

        if (this.options.onClose) {
            this.options.onClose();
        }
    }

    /**
     * Set processing state.
     * @param {boolean} processing
     */
    setProcessing(processing) {
        this.isProcessing = processing;
        if (processing) {
            this.element.classList.add('processing');
        } else {
            this.element.classList.remove('processing');
        }
    }

    /**
     * Set error state.
     * @param {string} message
     */
    setError(message) {
        this.element.classList.add('error');
        const input = this.element.querySelector('.selection-popup-input');
        input.placeholder = message;
        setTimeout(() => {
            this.element.classList.remove('error');
            input.placeholder = 'How should AI modify this?';
        }, 3000);
    }

    /**
     * Check if the popup is currently visible.
     * @returns {boolean}
     */
    get visible() {
        return this.isVisible;
    }

    /**
     * Destroy the popup and clean up.
     */
    destroy() {
        document.removeEventListener('mousedown', this._handleOutsideClick);
        if (this.element && this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
        }
    }
}

export default SelectionPopup;
