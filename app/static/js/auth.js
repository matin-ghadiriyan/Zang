/* ==================== Zang | Auth Enhancements ==================== */
/* Frontend-only: password visibility toggle + micro-interactions. No backend impact. */

(function () {
    'use strict';

    /* ---------- Password Visibility Toggle ---------- */
    document.querySelectorAll('.pw-toggle').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var targetId = btn.getAttribute('data-target');
            var input = document.getElementById(targetId);
            if (!input) return;

            var show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            input.classList.toggle('pw-visible', show);
            btn.textContent = show ? '🙈' : '👁️';
            btn.setAttribute('aria-label', show ? 'مخفی کردن رمز عبور' : 'نمایش رمز عبور');

            /* keep focus in the field */
            input.focus({ preventScroll: true });
            var len = input.value.length;
            if (input.setSelectionRange) {
                input.setSelectionRange(len, len);
            }
        });
    });

    /* ---------- Client-side hint for register password ---------- */
    var pw = document.getElementById('password');
    var form = document.getElementById('register-form');
    if (pw && form) {
        pw.addEventListener('input', function () {
            var ok = pw.value.length >= 8;
            pw.style.borderColor = pw.value.length === 0
                ? ''
                : (ok ? 'rgba(18, 201, 120, .55)' : 'rgba(239, 51, 64, .55)');
        });
    }
})();
