/**
 * FileList Concept
 *
 * Renders kernel file cards with completion status.
 * Handles click navigation to file editor.
 */

export class FileList {
    /**
     * @param {HTMLElement} containerEl - Container element to render into
     * @param {string} ideaId - ID of the parent idea
     */
    constructor(containerEl, ideaId) {
        this.container = containerEl;
        this.ideaId = ideaId;
        this.kernelFiles = [];
    }

    /**
     * Load kernel files from idea data.
     * @param {Array} kernelFiles - Array of kernel file metadata
     */
    load(kernelFiles) {
        this.kernelFiles = kernelFiles || [];
        this.render();
    }

    /**
     * Update completion status for a specific file.
     * @param {string} fileType - Type of kernel file
     * @param {boolean} isComplete - New completion status
     */
    updateCompletion(fileType, isComplete) {
        const file = this.kernelFiles.find(f => f.file_type === fileType);
        if (file) {
            file.is_complete = isComplete;
            this.render();
        }
    }

    /**
     * Get display name for file type.
     * @param {string} fileType - Internal file type
     */
    getDisplayName(fileType) {
        const names = {
            summary: 'Summary.md',
            challenge: 'Challenge.md',
            approach: 'Approach.md',
            coherent_steps: 'CoherentSteps.md',
        };
        return names[fileType] || fileType;
    }

    /**
     * Render the file list.
     */
    render() {
        if (this.kernelFiles.length === 0) {
            this.container.innerHTML = `
                <div class="empty-state">
                    <p>No kernel files found.</p>
                </div>
            `;
            return;
        }

        this.container.innerHTML = `
            <div class="kernel-file-grid">
                ${this.kernelFiles.map(file => this.renderFileCard(file)).join('')}
            </div>
        `;

        this.attachEventListeners();
    }

    /**
     * Render a single file card.
     * @param {Object} file - Kernel file metadata
     */
    renderFileCard(file) {
        const statusClass = file.is_complete ? 'complete' : 'incomplete';
        const statusIcon = file.is_complete ? '●' : '○';
        const statusText = file.is_complete ? 'Complete' : 'Not started';

        return `
            <div class="kernel-file-card" data-file-type="${file.file_type}">
                <div class="kernel-file-icon">📄</div>
                <div class="kernel-file-name">${this.getDisplayName(file.file_type)}</div>
                <div class="kernel-file-status ${statusClass}">
                    <span class="status-icon">${statusIcon}</span>
                    <span class="status-text">${statusText}</span>
                </div>
            </div>
        `;
    }

    /**
     * Attach event listeners to file cards.
     */
    attachEventListeners() {
        const cards = this.container.querySelectorAll('.kernel-file-card');
        cards.forEach(card => {
            card.addEventListener('click', () => {
                const fileType = card.dataset.fileType;
                window.location.hash = `#/ideas/${this.ideaId}/kernel/${fileType}`;
            });
        });
    }
}
