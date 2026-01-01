/**
 * User Switcher Concept
 *
 * Manages the user dropdown for switching between dev users.
 */

import { apiClient } from '../api/client.js';

export class UserSwitcher {
    constructor() {
        this.currentUser = null;
        this.users = [];
        this.isOpen = false;

        // DOM elements
        this.button = document.getElementById('user-switcher-button');
        this.dropdown = document.getElementById('user-switcher-dropdown');
        this.userNameEl = document.getElementById('current-user-name');

        this._bindEvents();
    }

    /**
     * Initialize the user switcher.
     */
    async init() {
        try {
            // Load users and current user in parallel
            const [usersResponse, currentUser] = await Promise.all([
                apiClient.getUsers(),
                apiClient.getCurrentUser(),
            ]);

            this.users = usersResponse.users;
            this.currentUser = currentUser;

            this._render();
        } catch (error) {
            console.error('Failed to initialize user switcher:', error);
            this.userNameEl.textContent = 'Error loading user';
        }
    }

    /**
     * Toggle dropdown visibility.
     */
    toggle() {
        this.isOpen = !this.isOpen;
        this.dropdown.classList.toggle('open', this.isOpen);
    }

    /**
     * Close the dropdown.
     */
    close() {
        this.isOpen = false;
        this.dropdown.classList.remove('open');
    }

    /**
     * Switch to a different user.
     * @param {string} userId - User ID to switch to
     */
    async switchUser(userId) {
        if (userId === this.currentUser?.id) {
            this.close();
            return;
        }

        try {
            const user = await apiClient.switchUser(userId);
            this.currentUser = user;
            this.close();

            // Reload the page to refresh all data with new user context
            window.location.reload();
        } catch (error) {
            console.error('Failed to switch user:', error);
            alert('Failed to switch user. Please try again.');
        }
    }

    /**
     * Bind event listeners.
     */
    _bindEvents() {
        // Toggle dropdown on button click
        this.button.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.dropdown.contains(e.target) && !this.button.contains(e.target)) {
                this.close();
            }
        });

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.close();
            }
        });
    }

    /**
     * Render the component.
     */
    _render() {
        // Update current user name
        if (this.currentUser) {
            this.userNameEl.textContent = this.currentUser.name;
        }

        // Render user options
        this.dropdown.innerHTML = this.users
            .map(
                (user) => `
                <div class="user-option ${user.id === this.currentUser?.id ? 'active' : ''}"
                     data-user-id="${user.id}">
                    <span class="user-option-name">${user.name}</span>
                    <span class="user-option-meta">${user.title || ''} · ${user.role}</span>
                </div>
            `
            )
            .join('');

        // Bind click events to user options
        this.dropdown.querySelectorAll('.user-option').forEach((option) => {
            option.addEventListener('click', () => {
                const userId = option.dataset.userId;
                this.switchUser(userId);
            });
        });
    }
}

export default UserSwitcher;
