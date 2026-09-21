/* ==================== Zang | Account Panel ==================== */

(() => {
    'use strict';

    const themeOptions = document.getElementById('theme-options');
    if (!themeOptions) return;

    const profileForm = document.getElementById('profile-form');
    const profileUsername = document.getElementById('profile-username');
    const profileEmail = document.getElementById('profile-email');
    const profileSubmit = document.getElementById('profile-submit');

    const passwordForm = document.getElementById('password-form');
    const passwordCurrent = document.getElementById('password-current');
    const passwordNew = document.getElementById('password-new');
    const passwordConfirm = document.getElementById('password-confirm');
    const passwordSubmit = document.getElementById('password-submit');

    const statChats = document.getElementById('stat-chats');
    const statMessages = document.getElementById('stat-messages');

    let currentTheme = 'zang';

    function applyTheme(theme) {
        document.documentElement.dataset.theme = theme;
    }

    function markActiveTheme(theme) {
        currentTheme = theme;
        themeOptions.querySelectorAll('.theme-option').forEach((option) => {
            option.classList.toggle('active', option.dataset.theme === theme);
        });
    }

    async function loadProfile() {
        try {
            const data = await Zang.api('/account/api/profile');
            const user = data.user || {};

            markActiveTheme(user.theme || 'zang');
            applyTheme(user.theme || 'zang');

            if (profileUsername) profileUsername.value = user.username || '';
            if (profileEmail) profileEmail.value = user.email || '';
        } catch (error) {
            Zang.toast(error.message, 'error');
        }
    }

    async function loadStats() {
        try {
            const data = await Zang.api('/chat/api/chats');
            const chats = data.chats || [];
            const messageCount = chats.reduce(
                (total, chat) => total + (Number(chat.messages_count) || 0), 0
            );

            if (statChats) statChats.textContent = chats.length;
            if (statMessages) statMessages.textContent = messageCount;
        } catch (_) {
            // آمار اختیاری است؛ خطا نادیده گرفته می‌شود.
        }
    }

    themeOptions.addEventListener('click', async (event) => {
        const option = event.target.closest('.theme-option');
        if (!option) return;

        const theme = option.dataset.theme;
        if (!theme || theme === currentTheme) return;

        const previous = currentTheme;
        markActiveTheme(theme);
        applyTheme(theme);

        try {
            await Zang.api('/account/api/theme', {
                method: 'PATCH',
                body: JSON.stringify({ theme })
            });
            Zang.toast('تم ذخیره شد', 'success');
        } catch (error) {
            markActiveTheme(previous);
            applyTheme(previous);
            Zang.toast(error.message, 'error');
        }
    });

    profileForm?.addEventListener('submit', async (event) => {
        event.preventDefault();

        const username = profileUsername.value.trim();
        const email = profileEmail.value.trim();

        profileSubmit.disabled = true;
        try {
            await Zang.api('/account/api/profile', {
                method: 'PATCH',
                body: JSON.stringify({ username, email })
            });
            Zang.toast('اطلاعات حساب ذخیره شد', 'success');
        } catch (error) {
            Zang.toast(error.message, 'error');
        } finally {
            profileSubmit.disabled = false;
        }
    });

    passwordForm?.addEventListener('submit', async (event) => {
        event.preventDefault();

        const current = passwordCurrent.value;
        const next = passwordNew.value;
        const confirm = passwordConfirm.value;

        if (next !== confirm) {
            Zang.toast('تکرار رمز عبور مطابقت ندارد', 'error');
            return;
        }

        passwordSubmit.disabled = true;
        try {
            await Zang.api('/account/api/password', {
                method: 'PATCH',
                body: JSON.stringify({
                    current_password: current,
                    new_password: next,
                    confirm_password: confirm
                })
            });

            passwordForm.reset();
            Zang.toast('رمز عبور تغییر کرد', 'success');
        } catch (error) {
            Zang.toast(error.message, 'error');
        } finally {
            passwordSubmit.disabled = false;
        }
    });

    loadProfile();
    loadStats();
})();
