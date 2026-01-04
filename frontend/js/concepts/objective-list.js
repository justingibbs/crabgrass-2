/**
 * ObjectiveList Concept
 *
 * Manages the display of objectives on the home page.
 */

import { apiClient } from '../api/client.js';

export class ObjectiveList {
    constructor(containerEl) {
        this.container = containerEl;
        this.objectives = [];
        this.loading = true;
        this.error = null;
        this.isAdmin = false;
    }

    /**
     * Load objectives from the API.
     */
    async load() {
        this.loading = true;
        this.error = null;
        this.render();

        try {
            // Check if current user is admin
            const user = await apiClient.getCurrentUser();
            this.isAdmin = user.role === 'org_admin';

            const response = await apiClient.getObjectives();
            this.objectives = response.objectives || [];
            this.loading = false;
            this.render();
        } catch (err) {
            this.error = err.message;
            this.loading = false;
            this.render();
        }
    }

    /**
     * Create a new objective (admin only).
     */
    async createObjective() {
        if (!this.isAdmin) {
            alert('Only admins can create objectives.');
            return;
        }

        const title = prompt('Enter objective title:');
        if (!title) return;

        try {
            const objective = await apiClient.createObjective({ title });
            // Navigate to the new objective's workspace
            window.location.hash = `#/objectives/${objective.id}`;
        } catch (err) {
            console.error('Failed to create objective:', err);
            alert('Failed to create objective: ' + err.message);
        }
    }

    /**
     * Render the objective list.
     */
    render() {
        if (this.loading) {
            this.container.innerHTML = `
                <div class="loading">Loading objectives...</div>
            `;
            return;
        }

        if (this.error) {
            this.container.innerHTML = `
                <div class="error-state">
                    <p>Failed to load objectives: ${this.error}</p>
                    <button class="button" onclick="window.crabgrass.objectiveList.load()">Retry</button>
                </div>
            `;
            return;
        }

        if (this.objectives.length === 0 && !this.isAdmin) {
            this.container.innerHTML = `
                <div class="empty-state">
                    <p>No objectives yet. Objectives will appear here once created by admins.</p>
                </div>
            `;
            return;
        }

        this.container.innerHTML = `
            <div class="card-grid" id="objectives-grid">
                ${this.isAdmin ? this.renderNewObjectiveCard() : ''}
                ${this.objectives.map(obj => this.renderObjectiveCard(obj)).join('')}
            </div>
        `;

        // Attach event listeners
        this.attachEventListeners();
    }

    /**
     * Render the "New Objective" card (admin only).
     */
    renderNewObjectiveCard() {
        return `
            <div class="card new-idea-card" id="new-objective-card">
                <span class="new-idea-icon">+</span>
                <span>New Objective</span>
                <span style="font-size: 0.75rem; color: var(--text-muted);">Define a strategic goal</span>
            </div>
        `;
    }

    /**
     * Render an objective card.
     * @param {Object} objective - Objective data
     */
    renderObjectiveCard(objective) {
        const ideasCount = objective.ideas_count || 0;

        return `
            <div class="card objective-card" data-objective-id="${objective.id}">
                <div class="idea-card-header">
                    <span class="idea-title">${this.escapeHtml(objective.title)}</span>
                    ${objective.timeframe ? `<span class="objective-timeframe">${this.escapeHtml(objective.timeframe)}</span>` : ''}
                </div>
                <div class="idea-card-body">
                    <span class="ideas-count">${ideasCount} idea${ideasCount !== 1 ? 's' : ''} linked</span>
                </div>
                <div class="idea-card-footer">
                    <span class="objective-status status-${objective.status}">${objective.status}</span>
                </div>
            </div>
        `;
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
     * Attach event listeners.
     */
    attachEventListeners() {
        // New objective card (admin only)
        const newObjectiveCard = document.getElementById('new-objective-card');
        if (newObjectiveCard) {
            newObjectiveCard.addEventListener('click', () => this.createObjective());
        }

        // Objective cards
        const objectiveCards = this.container.querySelectorAll('.objective-card');
        objectiveCards.forEach(card => {
            card.addEventListener('click', () => {
                const objectiveId = card.dataset.objectiveId;
                window.location.hash = `#/objectives/${objectiveId}`;
            });
        });
    }
}
