/**
 * IdeaWorkspace Concept
 *
 * Manages the idea workspace view including:
 * - Idea header with editable title
 * - Kernel completion status
 * - CoherenceAgent chat placeholder
 * - Kernel files grid
 * - Context files section
 */

import { apiClient } from '../api/client.js';
import { KernelStatus } from './kernel-status.js';
import { FileList } from './file-list.js';

export class IdeaWorkspace {
    /**
     * @param {HTMLElement} containerEl - Container element to render into
     * @param {string} ideaId - ID of the idea to display
     */
    constructor(containerEl, ideaId) {
        this.container = containerEl;
        this.ideaId = ideaId;
        this.idea = null;
        this.kernelFiles = [];
        this.loading = true;
        this.error = null;
        this.titleSaveTimeout = null;

        // Child concepts (initialized after first render)
        this.kernelStatus = null;
        this.fileList = null;
    }

    /**
     * Load idea data from API.
     */
    async load() {
        this.loading = true;
        this.error = null;
        this.render();

        try {
            const idea = await apiClient.getIdea(this.ideaId);
            this.idea = idea;
            this.kernelFiles = idea.kernel_files || [];
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
        // Initialize KernelStatus
        const statusContainer = document.getElementById('kernel-status-container');
        if (statusContainer) {
            this.kernelStatus = new KernelStatus(statusContainer, this.idea.kernel_completion);
        }

        // Initialize FileList
        const fileListContainer = document.getElementById('file-list-container');
        if (fileListContainer) {
            this.fileList = new FileList(fileListContainer, this.ideaId);
            this.fileList.load(this.kernelFiles);
        }
    }

    /**
     * Update the idea title with debounced auto-save.
     * @param {string} newTitle - New title value
     */
    updateTitle(newTitle) {
        if (!this.idea) return;

        // Clear any pending save
        if (this.titleSaveTimeout) {
            clearTimeout(this.titleSaveTimeout);
        }

        // Update local state immediately
        this.idea.title = newTitle;

        // Debounce the API call
        this.titleSaveTimeout = setTimeout(async () => {
            try {
                await apiClient.updateIdea(this.ideaId, { title: newTitle });
                console.log('Title saved:', newTitle);
            } catch (err) {
                console.error('Failed to save title:', err);
            }
        }, 500);
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
     * Render the workspace.
     */
    render() {
        if (this.loading) {
            this.container.innerHTML = `
                <div class="workspace-loading">
                    <div class="loading">Loading idea...</div>
                </div>
            `;
            return;
        }

        if (this.error) {
            this.container.innerHTML = `
                <div class="workspace-error">
                    <div class="error-state">
                        <p>Failed to load idea: ${this.error}</p>
                        <a href="#/" class="button">← Back to Home</a>
                    </div>
                </div>
            `;
            return;
        }

        this.container.innerHTML = `
            <div class="idea-workspace">
                <!-- Header -->
                <div class="workspace-header">
                    <a href="#/" class="back-link">← Home</a>
                </div>

                <!-- Idea Info Section -->
                <div class="workspace-info-section">
                    <div class="workspace-title-row">
                        <input
                            type="text"
                            class="workspace-title-input"
                            id="idea-title-input"
                            value="${this.escapeHtml(this.idea.title)}"
                            placeholder="Untitled Idea"
                        />
                        <div id="kernel-status-container"></div>
                    </div>
                    <div class="workspace-meta-row">
                        <div class="workspace-objective">
                            <span class="meta-label">Objective:</span>
                            <span class="meta-value">
                                ${this.idea.objective_id ? 'Linked' : 'Not selected'}
                            </span>
                            <button class="link-button" disabled>Select</button>
                        </div>
                        <div class="workspace-status">
                            <span class="meta-label">Status:</span>
                            <span class="idea-status status-${this.idea.status}">${this.idea.status}</span>
                        </div>
                    </div>
                    <div class="workspace-collaborators">
                        <span class="collaborator-badge">👤 You (Owner)</span>
                        <button class="share-button" disabled>Share ▼</button>
                    </div>
                </div>

                <!-- Divider -->
                <div class="workspace-divider"></div>

                <!-- CoherenceAgent Chat Section -->
                <div class="workspace-section">
                    <div class="section-header">
                        <span class="section-title">Chat with Coherence Agent</span>
                        <button class="sessions-button" disabled>Sessions ▼</button>
                    </div>
                    <div class="chat-placeholder">
                        <div class="chat-coming-soon">
                            <p>💬 Agent chat coming soon</p>
                            <p class="hint">CoherenceAgent will help you develop your idea and ensure all kernel files work together.</p>
                        </div>
                    </div>
                </div>

                <!-- Divider -->
                <div class="workspace-divider"></div>

                <!-- Kernel Files Section -->
                <div class="workspace-section">
                    <div class="section-header">
                        <span class="section-title">Kernel Files</span>
                    </div>
                    <div id="file-list-container"></div>
                </div>

                <!-- Divider -->
                <div class="workspace-divider"></div>

                <!-- Context Files Section -->
                <div class="workspace-section">
                    <div class="section-header">
                        <span class="section-title">Context Files</span>
                        <button class="add-file-button" disabled>+ New File</button>
                    </div>
                    <div class="empty-state">
                        <p>No context files yet. Add research, notes, or supporting material.</p>
                    </div>
                </div>

                <!-- Divider -->
                <div class="workspace-divider"></div>

                <!-- Action Bar -->
                <div class="workspace-action-bar">
                    <button class="button button-secondary" disabled>Archive</button>
                    <button class="button button-primary" disabled>Publish → Active</button>
                </div>
            </div>
        `;

        this.attachEventListeners();
    }

    /**
     * Attach event listeners.
     */
    attachEventListeners() {
        // Title input auto-save
        const titleInput = document.getElementById('idea-title-input');
        if (titleInput) {
            titleInput.addEventListener('input', (e) => {
                this.updateTitle(e.target.value);
            });

            // Save on blur
            titleInput.addEventListener('blur', (e) => {
                if (this.titleSaveTimeout) {
                    clearTimeout(this.titleSaveTimeout);
                }
                this.updateTitle(e.target.value);
            });
        }
    }
}
