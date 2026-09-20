/* ==================== Zang | Core ==================== */

const Zang = (() => {
    'use strict';

    /* ---------- Loader ---------- */
    function hideLoader() {
        const loader = document.getElementById('zang-loader');
        if (!loader) return;
        loader.classList.add('is-hidden');
        setTimeout(() => loader.remove(), 450);
    }

    if (document.readyState === 'complete') {
        setTimeout(hideLoader, 220);
    } else {
        window.addEventListener('load', () => setTimeout(hideLoader, 220), { once: true });
    }

    /* ---------- Toast ---------- */
    function toast(message, type = 'info', duration = 3200) {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const el = document.createElement('div');
        el.className = `toast ${type}`;
        el.textContent = message;
        container.appendChild(el);

        setTimeout(() => {
            el.classList.add('hide');
            setTimeout(() => el.remove(), 260);
        }, duration);
    }

    /* ---------- Fetch Helper ---------- */
    async function api(url, options = {}) {
        const config = {
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                throw new Error(data.error || 'خطا در ارتباط با سرور');
            }

            return data;
        } catch (error) {
            if (error instanceof TypeError) {
                throw new Error('اتصال به سرور برقرار نشد');
            }
            throw error;
        }
    }

    /* ---------- Escape HTML ---------- */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /* ---------- Format Time ---------- */
    function formatTime(iso) {
        if (!iso) return '';
        const date = new Date(iso);
        if (isNaN(date.getTime())) return '';

        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${hours}:${minutes}`;
    }

    /* ---------- Auto Resize ---------- */
    function autoResize(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 160) + 'px';
    }

    return { toast, api, escapeHtml, formatTime, autoResize };
})();
