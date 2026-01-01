/**
 * Crabgrass Frontend Entry Point
 *
 * Initializes the application and sets up routing.
 */

import { UserSwitcher } from './concepts/user-switcher.js';

/**
 * Simple hash-based router.
 */
class Router {
    constructor(routes) {
        this.routes = routes;
        this.mainContent = document.getElementById('main-content');

        // Listen for hash changes
        window.addEventListener('hashchange', () => this.handleRoute());

        // Handle initial route
        this.handleRoute();
    }

    /**
     * Get current route info from hash.
     */
    parseRoute() {
        const hash = window.location.hash.slice(1) || '/';
        const [path, ...rest] = hash.split('?');
        const segments = path.split('/').filter(Boolean);

        return { path, segments };
    }

    /**
     * Handle route change.
     */
    handleRoute() {
        const { path, segments } = this.parseRoute();

        // Match route
        for (const [pattern, handler] of Object.entries(this.routes)) {
            const match = this.matchRoute(pattern, segments);
            if (match) {
                handler(match.params, this.mainContent);
                return;
            }
        }

        // 404 fallback
        this.render404();
    }

    /**
     * Match a route pattern against segments.
     * @param {string} pattern - Route pattern (e.g., '/ideas/:id')
     * @param {string[]} segments - URL segments
     */
    matchRoute(pattern, segments) {
        const patternSegments = pattern.split('/').filter(Boolean);

        if (patternSegments.length !== segments.length) {
            return null;
        }

        const params = {};

        for (let i = 0; i < patternSegments.length; i++) {
            const patternPart = patternSegments[i];
            const segment = segments[i];

            if (patternPart.startsWith(':')) {
                // Dynamic segment
                params[patternPart.slice(1)] = segment;
            } else if (patternPart !== segment) {
                // Static segment mismatch
                return null;
            }
        }

        return { params };
    }

    /**
     * Navigate to a new route.
     * @param {string} path - Route path
     */
    navigate(path) {
        window.location.hash = path;
    }

    /**
     * Render 404 page.
     */
    render404() {
        this.mainContent.innerHTML = `
            <div class="route-placeholder">
                <h1>404 - Not Found</h1>
                <p>The page you're looking for doesn't exist.</p>
                <a href="#/">Go Home</a>
            </div>
        `;
    }
}

/**
 * Route handlers.
 */
const routes = {
    '/': (params, container) => {
        container.innerHTML = `
            <div class="page">
                <div class="section-header">
                    <span class="section-title">Contributing To</span>
                    <button class="button button-primary">+ New Idea</button>
                </div>
                <div class="card-grid">
                    <div class="card new-idea-card" onclick="window.location.hash='#/ideas/new'">
                        <span class="new-idea-icon">+</span>
                        <span>New Idea</span>
                        <span style="font-size: 0.75rem; color: var(--text-muted);">Start capturing your next innovation</span>
                    </div>
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
                <div class="empty-state">
                    <p>No objectives yet. Objectives will appear here once created by admins.</p>
                </div>
            </div>
        `;
    },

    '/ideas/:id': (params, container) => {
        container.innerHTML = `
            <div class="route-placeholder">
                <h1>Idea Workspace</h1>
                <p>Viewing idea: ${params.id}</p>
                <p style="margin-top: var(--spacing-md); color: var(--text-muted);">
                    This screen will be implemented in Slice 2.
                </p>
                <a href="#/" style="margin-top: var(--spacing-md);">← Back to Home</a>
            </div>
        `;
    },

    '/objectives/:id': (params, container) => {
        container.innerHTML = `
            <div class="route-placeholder">
                <h1>Objective Workspace</h1>
                <p>Viewing objective: ${params.id}</p>
                <p style="margin-top: var(--spacing-md); color: var(--text-muted);">
                    This screen will be implemented in Slice 9.
                </p>
                <a href="#/" style="margin-top: var(--spacing-md);">← Back to Home</a>
            </div>
        `;
    },
};

/**
 * Initialize the application.
 */
async function init() {
    console.log('Crabgrass initializing...');

    // Initialize user switcher
    const userSwitcher = new UserSwitcher();
    await userSwitcher.init();

    // Initialize router
    const router = new Router(routes);

    // Make router available globally for debugging
    window.crabgrass = { router, userSwitcher };

    console.log('Crabgrass ready');
}

// Start the app
init().catch(console.error);
