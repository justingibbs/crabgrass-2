/**
 * API Client for Crabgrass backend.
 */

const API_BASE = 'http://localhost:8000';

/**
 * Make an API request with error handling.
 * @param {string} path - API path (e.g., '/api/auth/users')
 * @param {Object} options - Fetch options
 * @returns {Promise<any>} Response data
 */
async function request(path, options = {}) {
    const url = `${API_BASE}${path}`;

    const config = {
        ...options,
        credentials: 'include', // Include cookies for auth
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    };

    try {
        const response = await fetch(url, config);

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API Error: ${path}`, error);
        throw error;
    }
}

/**
 * API client methods.
 */
export const apiClient = {
    /**
     * Health check.
     */
    async health() {
        return request('/health');
    },

    /**
     * Get list of available dev users.
     */
    async getUsers() {
        return request('/api/auth/users');
    },

    /**
     * Get current user.
     */
    async getCurrentUser() {
        return request('/api/auth/me');
    },

    /**
     * Switch to a different user.
     * @param {string} userId - User ID to switch to
     */
    async switchUser(userId) {
        return request(`/api/auth/switch/${userId}`, {
            method: 'POST',
        });
    },
};

export default apiClient;
