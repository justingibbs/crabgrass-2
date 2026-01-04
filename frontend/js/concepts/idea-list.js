/**
 * IdeaList Concept
 *
 * Manages the display of ideas on the home page.
 */

import { apiClient } from '../api/client.js';
import { ObjectiveList } from './objective-list.js';

export class IdeaList {
    constructor(containerEl) {
        this.container = containerEl;
        this.ideas = [];
        this.loading = true;
        this.error = null;
        this.objectiveList = null;
        this.searchQuery = '';
        this._searchDebounceTimer = null;
    }

    /**
     * Get filtered ideas based on search query.
     */
    getFilteredIdeas() {
        if (!this.searchQuery.trim()) {
            return this.ideas;
        }
        const query = this.searchQuery.toLowerCase().trim();
        return this.ideas.filter(idea =>
            idea.title.toLowerCase().includes(query)
        );
    }

    /**
     * Load ideas from the API.
     */
    async load() {
        this.loading = true;
        this.error = null;
        this.render();

        try {
            const response = await apiClient.getIdeas();
            this.ideas = response.ideas || [];
            this.loading = false;
            this.render();
        } catch (err) {
            this.error = err.message;
            this.loading = false;
            this.render();
        }
    }

    /**
     * Create a new idea and navigate to its workspace.
     */
    async createIdea() {
        try {
            const idea = await apiClient.createIdea({ title: 'Untitled Idea' });
            // Navigate to the new idea's workspace
            window.location.hash = `#/ideas/${idea.id}`;
        } catch (err) {
            console.error('Failed to create idea:', err);
            alert('Failed to create idea: ' + err.message);
        }
    }

    /**
     * Render the idea list.
     */
    render() {
        if (this.loading) {
            this.container.innerHTML = `
                <div class="loading">Loading ideas...</div>
            `;
            return;
        }

        if (this.error) {
            this.container.innerHTML = `
                <div class="error-state">
                    <p>Failed to load ideas: ${this.error}</p>
                    <button class="button" onclick="window.crabgrass.ideaList.load()">Retry</button>
                </div>
            `;
            return;
        }

        const filteredIdeas = this.getFilteredIdeas();
        const hasSearchQuery = this.searchQuery.trim().length > 0;

        this.container.innerHTML = `
            <div class="page">
                <div class="section-header">
                    <span class="section-title">Contributing To</span>
                    <div class="search-container">
                        <input
                            type="text"
                            class="search-input"
                            placeholder="Search ideas..."
                            value="${this.escapeHtml(this.searchQuery)}"
                        />
                    </div>
                </div>
                <div class="card-grid" id="ideas-grid">
                    ${!hasSearchQuery ? this.renderNewIdeaCard() : ''}
                    ${filteredIdeas.length > 0
                        ? filteredIdeas.map(idea => this.renderIdeaCard(idea)).join('')
                        : (hasSearchQuery
                            ? '<div class="empty-state"><p>No ideas match your search.</p></div>'
                            : '<div class="empty-state"><p>No ideas yet. Create your first idea!</p></div>'
                          )
                    }
                </div>

                <div class="section-header" style="margin-top: var(--spacing-xl);">
                    <span class="section-title">Shared With Me</span>
                </div>
                <div class="empty-state">
                    <p>No ideas have been shared with you yet.</p>
                </div>

                <div class="section-header" style="margin-top: var(--spacing-xl);">
                    <span class="section-title">Objectives</span>
                </div>
                <div id="objectives-section"></div>
            </div>
        `;

        // Attach event listeners
        this.attachEventListeners();

        // Initialize and load objectives section
        const objectivesContainer = document.getElementById('objectives-section');
        if (objectivesContainer) {
            this.objectiveList = new ObjectiveList(objectivesContainer);
            window.crabgrass.objectiveList = this.objectiveList;
            this.objectiveList.load();
        }
    }

    /**
     * Render the "New Idea" card.
     */
    renderNewIdeaCard() {
        return `
            <div class="card new-idea-card" id="new-idea-card">
                <span class="new-idea-icon">+</span>
                <span>New Idea</span>
                <span style="font-size: 0.75rem; color: var(--text-muted);">Start capturing your next innovation</span>
            </div>
        `;
    }

    /**
     * Render an idea card.
     * @param {Object} idea - Idea data
     */
    renderIdeaCard(idea) {
        const completionDots = this.renderCompletionDots(idea.kernel_completion);
        const updatedAt = this.formatRelativeTime(idea.updated_at);

        return `
            <div class="card idea-card" data-idea-id="${idea.id}">
                <div class="idea-card-header">
                    <span class="idea-title">${this.escapeHtml(idea.title)}</span>
                    <span class="idea-status status-${idea.status}">${idea.status}</span>
                </div>
                <div class="idea-card-body">
                    <div class="kernel-progress">
                        ${completionDots}
                        <span class="kernel-count">${idea.kernel_completion}/4</span>
                    </div>
                </div>
                <div class="idea-card-footer">
                    <span class="idea-updated">Updated ${updatedAt}</span>
                </div>
            </div>
        `;
    }

    /**
     * Render kernel completion dots.
     * @param {number} count - Number of completed kernel files (0-4)
     */
    renderCompletionDots(count) {
        const dots = [];
        for (let i = 0; i < 4; i++) {
            const filled = i < count;
            dots.push(`<span class="kernel-dot ${filled ? 'filled' : ''}"></span>`);
        }
        return dots.join('');
    }

    /**
     * Format a timestamp as relative time.
     * @param {string} timestamp - ISO timestamp
     */
    formatRelativeTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
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
     * Handle search input with debouncing.
     * @param {string} value - Search query
     */
    handleSearch(value) {
        this.searchQuery = value;

        // Debounce the re-render to avoid excessive updates
        if (this._searchDebounceTimer) {
            clearTimeout(this._searchDebounceTimer);
        }

        this._searchDebounceTimer = setTimeout(() => {
            this.render();
            // Restore focus to search input
            const searchInput = this.container.querySelector('.search-input');
            if (searchInput) {
                searchInput.focus();
                searchInput.setSelectionRange(value.length, value.length);
            }
        }, 150);
    }

    /**
     * Attach event listeners.
     */
    attachEventListeners() {
        // Search input
        const searchInput = this.container.querySelector('.search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.handleSearch(e.target.value);
            });
        }

        // New idea card
        const newIdeaCard = document.getElementById('new-idea-card');
        if (newIdeaCard) {
            newIdeaCard.addEventListener('click', () => this.createIdea());
        }

        // Idea cards
        const ideaCards = this.container.querySelectorAll('.idea-card');
        ideaCards.forEach(card => {
            card.addEventListener('click', () => {
                const ideaId = card.dataset.ideaId;
                window.location.hash = `#/ideas/${ideaId}`;
            });
        });
    }
}
