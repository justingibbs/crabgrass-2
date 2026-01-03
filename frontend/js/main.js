/**
 * Crabgrass Frontend Entry Point
 *
 * Initializes the application and sets up routing.
 */

import { UserSwitcher } from './concepts/user-switcher.js';
import { IdeaList } from './concepts/idea-list.js';
import { IdeaWorkspace } from './concepts/idea-workspace.js';
import { FileEditor } from './pages/file-editor.js';

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
 * Get display name for kernel file type.
 * @param {string} fileType - Internal file type
 */
function getFileDisplayName(fileType) {
    const names = {
        summary: 'Summary.md',
        challenge: 'Challenge.md',
        approach: 'Approach.md',
        coherent_steps: 'CoherentSteps.md',
    };
    return names[fileType] || fileType;
}

/**
 * Route handlers.
 */
const routes = {
    '/': (params, container) => {
        // Use IdeaList concept to render and manage the home page
        const ideaList = new IdeaList(container);
        window.crabgrass.ideaList = ideaList; // Store reference for retry button
        ideaList.load();
    },

    '/ideas/:id': (params, container) => {
        // Use IdeaWorkspace concept to render and manage the idea workspace
        const workspace = new IdeaWorkspace(container, params.id);
        window.crabgrass.ideaWorkspace = workspace; // Store reference
        workspace.load();
    },

    '/ideas/:id/kernel/:type': (params, container) => {
        // Kernel file editor with canvas
        const fileEditor = new FileEditor(container, params.id, params.type, 'kernel');
        window.crabgrass.fileEditor = fileEditor;
        fileEditor.load();
    },

    '/ideas/:id/context/:fileId': (params, container) => {
        // Context file editor with ContextAgent
        const fileEditor = new FileEditor(container, params.id, params.fileId, 'context');
        window.crabgrass.fileEditor = fileEditor;
        fileEditor.load();
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

    // Initialize global state object first (routes may need it)
    window.crabgrass = {};

    // Initialize user switcher
    const userSwitcher = new UserSwitcher();
    await userSwitcher.init();
    window.crabgrass.userSwitcher = userSwitcher;

    // Initialize router (this will trigger the initial route)
    const router = new Router(routes);
    window.crabgrass.router = router;

    console.log('Crabgrass ready');
}

// Start the app
init().catch(console.error);
