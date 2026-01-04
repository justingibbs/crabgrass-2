/**
 * Version History Modal Component
 *
 * Displays version history for a kernel file and allows restoring previous versions.
 */

import { apiClient } from '../api/client.js';

/**
 * VersionHistoryModal - modal for viewing and restoring file versions.
 */
export class VersionHistoryModal {
    /**
     * Create a VersionHistoryModal instance.
     * @param {Object} options - Configuration options
     * @param {string} options.ideaId - The idea ID
     * @param {string} options.fileType - The kernel file type
     * @param {Function} options.onRestore - Callback when a version is restored (receives new content)
     * @param {Function} options.onClose - Callback when modal is closed
     */
    constructor(options) {
        this.ideaId = options.ideaId;
        this.fileType = options.fileType;
        this.onRestore = options.onRestore;
        this.onClose = options.onClose;

        this.versions = [];
        this.isLoading = true;
        this.error = null;
        this.isRestoring = false;
        this.confirmingVersion = null; // change_id of version being confirmed

        this._createModal();
        this._loadVersions();
    }

    /**
     * Create the modal DOM structure.
     * @private
     */
    _createModal() {
        // Create backdrop
        this.backdrop = document.createElement('div');
        this.backdrop.className = 'modal-backdrop';
        this.backdrop.addEventListener('click', (e) => {
            if (e.target === this.backdrop) {
                this.close();
            }
        });

        // Create modal container
        this.modal = document.createElement('div');
        this.modal.className = 'modal version-history-modal';

        this.backdrop.appendChild(this.modal);
        document.body.appendChild(this.backdrop);

        // Handle escape key
        this._escapeHandler = (e) => {
            if (e.key === 'Escape') {
                this.close();
            }
        };
        document.addEventListener('keydown', this._escapeHandler);

        this.render();
    }

    /**
     * Load versions from the API.
     * @private
     */
    async _loadVersions() {
        try {
            const response = await apiClient.getKernelFileHistory(this.ideaId, this.fileType);
            this.versions = response.versions || [];
            this.isLoading = false;
            this.render();
        } catch (error) {
            console.error('Failed to load versions:', error);
            this.error = error.message;
            this.isLoading = false;
            this.render();
        }
    }

    /**
     * Handle restore button click.
     * @param {string} changeId - The change ID to restore
     * @private
     */
    _handleRestoreClick(changeId) {
        this.confirmingVersion = changeId;
        this.render();
    }

    /**
     * Cancel restore confirmation.
     * @private
     */
    _cancelRestore() {
        this.confirmingVersion = null;
        this.render();
    }

    /**
     * Confirm and execute restore.
     * @param {string} changeId - The change ID to restore
     * @private
     */
    async _confirmRestore(changeId) {
        this.isRestoring = true;
        this.render();

        try {
            const response = await apiClient.restoreKernelFileVersion(
                this.ideaId,
                this.fileType,
                changeId
            );

            // Call the onRestore callback with the new content
            if (this.onRestore) {
                this.onRestore(response.content);
            }

            this.close();
        } catch (error) {
            console.error('Failed to restore version:', error);
            this.error = error.message;
            this.isRestoring = false;
            this.confirmingVersion = null;
            this.render();
        }
    }

    /**
     * Format a timestamp for display.
     * @param {string} timestamp - ISO timestamp
     * @private
     */
    _formatTimestamp(timestamp) {
        try {
            const date = new Date(timestamp);
            return date.toLocaleDateString([], {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch {
            return timestamp;
        }
    }

    /**
     * Render the modal content.
     */
    render() {
        const fileTypeDisplay = this.fileType.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());

        this.modal.innerHTML = `
            <div class="modal-header">
                <h2 class="modal-title">Version History - ${fileTypeDisplay}</h2>
                <button class="modal-close" aria-label="Close">&times;</button>
            </div>
            <div class="modal-body">
                ${this._renderContent()}
            </div>
        `;

        // Attach event listeners
        this.modal.querySelector('.modal-close').addEventListener('click', () => this.close());

        // Attach restore button listeners
        this.modal.querySelectorAll('.version-restore-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this._handleRestoreClick(btn.dataset.changeId);
            });
        });

        // Attach confirmation listeners
        const confirmBtn = this.modal.querySelector('.version-confirm-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                this._confirmRestore(confirmBtn.dataset.changeId);
            });
        }

        const cancelBtn = this.modal.querySelector('.version-cancel-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this._cancelRestore());
        }
    }

    /**
     * Render the main content area.
     * @private
     */
    _renderContent() {
        if (this.isLoading) {
            return `
                <div class="version-loading">
                    <p>Loading version history...</p>
                </div>
            `;
        }

        if (this.error) {
            return `
                <div class="version-error">
                    <p>Error: ${this._escapeHtml(this.error)}</p>
                </div>
            `;
        }

        if (this.versions.length === 0) {
            return `
                <div class="version-empty">
                    <p>No version history available.</p>
                    <p class="hint">Versions are created each time you save the file.</p>
                </div>
            `;
        }

        if (this.confirmingVersion) {
            return this._renderConfirmation();
        }

        return `
            <div class="version-list">
                ${this.versions.map((version, index) => `
                    <div class="version-item ${index === 0 ? 'version-current' : ''}">
                        <div class="version-info">
                            <div class="version-message">${this._escapeHtml(version.message)}</div>
                            <div class="version-meta">
                                <span class="version-time">${this._formatTimestamp(version.timestamp)}</span>
                                <span class="version-id">${version.change_id}</span>
                            </div>
                        </div>
                        <div class="version-actions">
                            ${index === 0
                                ? '<span class="version-current-label">Current</span>'
                                : `<button class="btn btn-ghost version-restore-btn" data-change-id="${version.change_id}">Restore</button>`
                            }
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    /**
     * Render the confirmation dialog.
     * @private
     */
    _renderConfirmation() {
        const version = this.versions.find(v => v.change_id === this.confirmingVersion);
        if (!version) return '';

        return `
            <div class="version-confirm">
                <div class="version-confirm-icon">!</div>
                <h3>Restore this version?</h3>
                <p>This will replace the current content with the version from:</p>
                <div class="version-confirm-details">
                    <strong>${this._escapeHtml(version.message)}</strong>
                    <span>${this._formatTimestamp(version.timestamp)}</span>
                </div>
                <div class="version-confirm-actions">
                    <button class="btn btn-ghost version-cancel-btn" ${this.isRestoring ? 'disabled' : ''}>
                        Cancel
                    </button>
                    <button class="btn btn-primary version-confirm-btn" data-change-id="${version.change_id}" ${this.isRestoring ? 'disabled' : ''}>
                        ${this.isRestoring ? 'Restoring...' : 'Restore'}
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Escape HTML special characters.
     * @private
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Close the modal.
     */
    close() {
        document.removeEventListener('keydown', this._escapeHandler);
        this.backdrop.remove();
        if (this.onClose) {
            this.onClose();
        }
    }
}

export default VersionHistoryModal;
