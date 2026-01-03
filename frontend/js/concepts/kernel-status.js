/**
 * KernelStatus Concept
 *
 * Renders the kernel completion progress indicator (●●○○ format).
 */

export class KernelStatus {
    /**
     * @param {HTMLElement} containerEl - Container element to render into
     * @param {number} completionCount - Number of completed kernel files (0-4)
     */
    constructor(containerEl, completionCount = 0) {
        this.container = containerEl;
        this.completionCount = completionCount;
        this.render();
    }

    /**
     * Update the completion count and re-render.
     * @param {number} count - New completion count
     */
    update(count) {
        this.completionCount = count;
        this.render();
    }

    /**
     * Render the progress indicator.
     */
    render() {
        const dots = [];
        for (let i = 0; i < 4; i++) {
            const filled = i < this.completionCount;
            dots.push(`<span class="kernel-dot ${filled ? 'filled' : ''}"></span>`);
        }

        this.container.innerHTML = `
            <div class="kernel-status">
                <div class="kernel-dots">${dots.join('')}</div>
                <span class="kernel-count">${this.completionCount}/4 complete</span>
            </div>
        `;
    }
}
