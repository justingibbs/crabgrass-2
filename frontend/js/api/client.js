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

    // --- Ideas ---

    /**
     * Get list of ideas for the current user.
     */
    async getIdeas() {
        return request('/api/ideas');
    },

    /**
     * Create a new idea.
     * @param {Object} data - Idea data
     * @param {string} [data.title] - Idea title (default: "Untitled Idea")
     * @param {string} [data.objective_id] - Optional objective ID
     */
    async createIdea(data = {}) {
        return request('/api/ideas', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * Get an idea by ID.
     * @param {string} ideaId - Idea ID
     */
    async getIdea(ideaId) {
        return request(`/api/ideas/${ideaId}`);
    },

    /**
     * Update an idea.
     * @param {string} ideaId - Idea ID
     * @param {Object} data - Fields to update
     */
    async updateIdea(ideaId, data) {
        return request(`/api/ideas/${ideaId}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    },

    /**
     * Archive (soft delete) an idea.
     * @param {string} ideaId - Idea ID
     */
    async archiveIdea(ideaId) {
        return request(`/api/ideas/${ideaId}`, {
            method: 'DELETE',
        });
    },

    // --- Kernel Files ---

    /**
     * Get a kernel file's content.
     * @param {string} ideaId - Idea ID
     * @param {string} fileType - File type (summary, challenge, approach, coherent_steps)
     */
    async getKernelFile(ideaId, fileType) {
        return request(`/api/ideas/${ideaId}/kernel/${fileType}`);
    },

    /**
     * Update a kernel file's content.
     * @param {string} ideaId - Idea ID
     * @param {string} fileType - File type (summary, challenge, approach, coherent_steps)
     * @param {string} content - New content
     * @param {string} [commitMessage] - Optional commit message
     */
    async updateKernelFile(ideaId, fileType, content, commitMessage = null) {
        const body = { content };
        if (commitMessage) {
            body.commit_message = commitMessage;
        }
        return request(`/api/ideas/${ideaId}/kernel/${fileType}`, {
            method: 'PUT',
            body: JSON.stringify(body),
        });
    },

    /**
     * Get version history for a kernel file.
     * @param {string} ideaId - Idea ID
     * @param {string} fileType - File type
     * @param {number} [limit=50] - Maximum versions to return
     */
    async getKernelFileHistory(ideaId, fileType, limit = 50) {
        return request(`/api/ideas/${ideaId}/kernel/${fileType}/history?limit=${limit}`);
    },

    // --- Agent Chat ---

    /**
     * Send a chat message to an agent.
     * @param {string} ideaId - Idea ID
     * @param {string} fileType - File type (determines which agent)
     * @param {string} message - The message to send
     * @param {string} [sessionId] - Optional session ID to continue conversation
     */
    async sendChatMessage(ideaId, fileType, message, sessionId = null) {
        const body = { message };
        if (sessionId) {
            body.session_id = sessionId;
        }
        return request(`/api/ideas/${ideaId}/kernel/${fileType}/chat`, {
            method: 'POST',
            body: JSON.stringify(body),
        });
    },

    /**
     * Get list of sessions for a kernel file.
     * @param {string} ideaId - Idea ID
     * @param {string} fileType - File type
     */
    async getSessions(ideaId, fileType) {
        return request(`/api/ideas/${ideaId}/kernel/${fileType}/sessions`);
    },

    /**
     * Get a session with its message history.
     * @param {string} ideaId - Idea ID
     * @param {string} sessionId - Session ID
     */
    async getSessionWithMessages(ideaId, sessionId) {
        return request(`/api/ideas/${ideaId}/sessions/${sessionId}`);
    },

    // --- Coherence Agent ---

    /**
     * Send a chat message to the CoherenceAgent.
     * @param {string} ideaId - Idea ID
     * @param {string} message - The message to send
     * @param {string} [sessionId] - Optional session ID to continue conversation
     */
    async sendCoherenceChatMessage(ideaId, message, sessionId = null) {
        const body = { message };
        if (sessionId) {
            body.session_id = sessionId;
        }
        return request(`/api/ideas/${ideaId}/coherence/chat`, {
            method: 'POST',
            body: JSON.stringify(body),
        });
    },

    /**
     * Trigger a coherence evaluation.
     * @param {string} ideaId - Idea ID
     */
    async triggerCoherenceEvaluation(ideaId) {
        return request(`/api/ideas/${ideaId}/coherence/evaluate`, {
            method: 'POST',
        });
    },

    /**
     * Get list of coherence sessions for an idea.
     * @param {string} ideaId - Idea ID
     */
    async getCoherenceSessions(ideaId) {
        return request(`/api/ideas/${ideaId}/coherence/sessions`);
    },

    // --- Context Files ---

    /**
     * Get list of context files for an idea.
     * @param {string} ideaId - Idea ID
     */
    async getContextFiles(ideaId) {
        return request(`/api/ideas/${ideaId}/context`);
    },

    /**
     * Get a context file by ID with content.
     * @param {string} ideaId - Idea ID
     * @param {string} fileId - File ID
     */
    async getContextFileById(ideaId, fileId) {
        return request(`/api/ideas/${ideaId}/context/${fileId}`);
    },

    /**
     * Create a new context file.
     * @param {string} ideaId - Idea ID
     * @param {string} filename - Filename (must end in .md)
     * @param {string} content - Initial content
     */
    async createContextFile(ideaId, filename, content = '') {
        return request(`/api/ideas/${ideaId}/context`, {
            method: 'POST',
            body: JSON.stringify({ filename, content }),
        });
    },

    /**
     * Update a context file's content.
     * @param {string} ideaId - Idea ID
     * @param {string} fileId - File ID
     * @param {string} content - New content
     */
    async updateContextFile(ideaId, fileId, content) {
        return request(`/api/ideas/${ideaId}/context/${fileId}`, {
            method: 'PUT',
            body: JSON.stringify({ content }),
        });
    },

    /**
     * Delete a context file.
     * @param {string} ideaId - Idea ID
     * @param {string} fileId - File ID
     */
    async deleteContextFile(ideaId, fileId) {
        return request(`/api/ideas/${ideaId}/context/${fileId}`, {
            method: 'DELETE',
        });
    },

    /**
     * Send a chat message to the ContextAgent.
     * @param {string} ideaId - Idea ID
     * @param {string} fileId - Context file ID
     * @param {string} message - The message to send
     * @param {string} [sessionId] - Optional session ID to continue conversation
     */
    async sendContextChatMessage(ideaId, fileId, message, sessionId = null) {
        const body = { message };
        if (sessionId) {
            body.session_id = sessionId;
        }
        return request(`/api/ideas/${ideaId}/context/${fileId}/chat`, {
            method: 'POST',
            body: JSON.stringify(body),
        });
    },

    // --- Idea-Objective Links ---

    /**
     * Link an idea to an objective.
     * @param {string} ideaId - Idea ID
     * @param {string} objectiveId - Objective ID
     */
    async linkIdeaToObjective(ideaId, objectiveId) {
        return request(`/api/ideas/${ideaId}/objective`, {
            method: 'POST',
            body: JSON.stringify({ objective_id: objectiveId }),
        });
    },

    /**
     * Unlink an idea from its objective.
     * @param {string} ideaId - Idea ID
     */
    async unlinkIdeaFromObjective(ideaId) {
        return request(`/api/ideas/${ideaId}/objective`, {
            method: 'DELETE',
        });
    },

    // --- Objectives ---

    /**
     * Get list of objectives for the current user's organization.
     */
    async getObjectives() {
        return request('/api/objectives');
    },

    /**
     * Create a new objective (admin only).
     * @param {Object} data - Objective data
     * @param {string} data.title - Objective title
     * @param {string} [data.description] - Optional description
     * @param {string} [data.owner_id] - Optional owner user ID
     * @param {string} [data.timeframe] - Optional timeframe (e.g., 'Q1 2025')
     */
    async createObjective(data) {
        return request('/api/objectives', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * Get an objective by ID.
     * @param {string} objectiveId - Objective ID
     */
    async getObjective(objectiveId) {
        return request(`/api/objectives/${objectiveId}`);
    },

    /**
     * Update an objective (admin only).
     * @param {string} objectiveId - Objective ID
     * @param {Object} data - Fields to update
     */
    async updateObjective(objectiveId, data) {
        return request(`/api/objectives/${objectiveId}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    },

    /**
     * Archive (soft delete) an objective (admin only).
     * @param {string} objectiveId - Objective ID
     */
    async archiveObjective(objectiveId) {
        return request(`/api/objectives/${objectiveId}`, {
            method: 'DELETE',
        });
    },

    /**
     * Get ideas linked to an objective.
     * @param {string} objectiveId - Objective ID
     */
    async getObjectiveIdeas(objectiveId) {
        return request(`/api/objectives/${objectiveId}/ideas`);
    },

    // --- Objective File ---

    /**
     * Get an objective's file content.
     * @param {string} objectiveId - Objective ID
     */
    async getObjectiveFile(objectiveId) {
        return request(`/api/objectives/${objectiveId}/file`);
    },

    /**
     * Update an objective's file content (admin only).
     * @param {string} objectiveId - Objective ID
     * @param {string} content - New content
     */
    async updateObjectiveFile(objectiveId, content) {
        return request(`/api/objectives/${objectiveId}/file`, {
            method: 'PUT',
            body: JSON.stringify({ content }),
        });
    },

    // --- Objective Agent Chat ---

    /**
     * Send a chat message to the ObjectiveAgent.
     * @param {string} objectiveId - Objective ID
     * @param {string} message - The message to send
     * @param {string} [sessionId] - Optional session ID to continue conversation
     */
    async sendObjectiveChatMessage(objectiveId, message, sessionId = null) {
        const body = { message };
        if (sessionId) {
            body.session_id = sessionId;
        }
        return request(`/api/objectives/${objectiveId}/chat`, {
            method: 'POST',
            body: JSON.stringify(body),
        });
    },

    /**
     * Check alignment between an idea and an objective.
     * @param {string} objectiveId - Objective ID
     * @param {string} ideaId - Idea ID
     */
    async checkObjectiveAlignment(objectiveId, ideaId) {
        return request(`/api/objectives/${objectiveId}/alignment/${ideaId}`, {
            method: 'POST',
        });
    },

    /**
     * Get list of sessions for an objective.
     * @param {string} objectiveId - Objective ID
     */
    async getObjectiveSessions(objectiveId) {
        return request(`/api/objectives/${objectiveId}/sessions`);
    },

    // --- Objective Context Files ---

    /**
     * Get list of context files for an objective.
     * @param {string} objectiveId - Objective ID
     */
    async getObjectiveContextFiles(objectiveId) {
        return request(`/api/objectives/${objectiveId}/context`);
    },

    /**
     * Get an objective context file by ID with content.
     * @param {string} objectiveId - Objective ID
     * @param {string} fileId - File ID
     */
    async getObjectiveContextFileById(objectiveId, fileId) {
        return request(`/api/objectives/${objectiveId}/context/${fileId}`);
    },

    /**
     * Create a new objective context file.
     * @param {string} objectiveId - Objective ID
     * @param {string} filename - Filename (must end in .md)
     * @param {string} content - Initial content
     */
    async createObjectiveContextFile(objectiveId, filename, content = '') {
        return request(`/api/objectives/${objectiveId}/context`, {
            method: 'POST',
            body: JSON.stringify({ filename, content }),
        });
    },

    /**
     * Update an objective context file's content.
     * @param {string} objectiveId - Objective ID
     * @param {string} fileId - File ID
     * @param {string} content - New content
     */
    async updateObjectiveContextFile(objectiveId, fileId, content) {
        return request(`/api/objectives/${objectiveId}/context/${fileId}`, {
            method: 'PUT',
            body: JSON.stringify({ content }),
        });
    },

    /**
     * Delete an objective context file.
     * @param {string} objectiveId - Objective ID
     * @param {string} fileId - File ID
     */
    async deleteObjectiveContextFile(objectiveId, fileId) {
        return request(`/api/objectives/${objectiveId}/context/${fileId}`, {
            method: 'DELETE',
        });
    },
};

export default apiClient;
