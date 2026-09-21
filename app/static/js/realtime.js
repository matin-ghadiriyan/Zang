/* ==================== Zang v0.3 | Realtime ==================== */

(() => {
    'use strict';

    const shell = document.querySelector('.app-shell');
    if (!shell || typeof io !== 'function') return;

    const chatList = document.getElementById('chat-list');
    const messagesBox = document.getElementById('messages');
    const composer = document.getElementById('composer');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const conversationStatus = document.getElementById('conversation-status');
    const currentUsername = shell.dataset.username;

    const socket = io({
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 700,
        timeout: 8000
    });

    let joinedChatId = null;
    let typingTimer = null;
    let lastTypingSentAt = 0;
    let statusRestoreTimer = null;

    function activeItem() {
        return chatList?.querySelector('.chat-item.active') || null;
    }

    function activeChatId() {
        const item = activeItem();
        return item ? Number(item.dataset.chatId) : null;
    }

    function setStatus(text, className = '') {
        if (!conversationStatus) return;
        conversationStatus.textContent = text;
        conversationStatus.classList.remove('realtime-ok', 'realtime-warn');
        if (className) conversationStatus.classList.add(className);
    }

    function showTemporaryStatus(text, timeout = 1700) {
        clearTimeout(statusRestoreTimer);
        setStatus(text, 'realtime-ok');
        statusRestoreTimer = setTimeout(() => {
            if (socket.connected) {
                setStatus('● زنده و متصل', 'realtime-ok');
            }
        }, timeout);
    }

    function joinActiveChat() {
        const nextId = activeChatId();
        if (!socket.connected || !nextId || nextId === joinedChatId) return;

        if (joinedChatId) {
            socket.emit('chat:leave', { chat_id: joinedChatId });
        }

        joinedChatId = nextId;
        socket.emit('chat:join', { chat_id: nextId }, (ack) => {
            if (ack && ack.ok === false) {
                Zang.toast(ack.error || 'اتصال زنده به گفتگو برقرار نشد', 'error');
            }
        });
    }

    function reloadActiveChat(chatId) {
        const item = chatList?.querySelector(`.chat-item[data-chat-id="${chatId}"]`);
        if (!item || !item.classList.contains('active')) return;
        item.click();
    }

    function enhanceMessage(messageEl) {
        if (!messageEl || messageEl.dataset.liveEnhanced === '1') return;
        messageEl.dataset.liveEnhanced = '1';

        const bubble = messageEl.querySelector('.message-bubble');
        if (!bubble) return;

        const actions = document.createElement('div');
        actions.className = 'message-live-actions';

        const copyBtn = document.createElement('button');
        copyBtn.type = 'button';
        copyBtn.className = 'message-live-action';
        copyBtn.title = 'کپی پیام';
        copyBtn.textContent = '⧉';
        copyBtn.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(bubble.textContent || '');
                Zang.toast('پیام کپی شد', 'success');
            } catch (_) {
                Zang.toast('کپی پیام ممکن نشد', 'error');
            }
        });
        actions.appendChild(copyBtn);

        if (messageEl.classList.contains('mine')) {
            const editBtn = document.createElement('button');
            editBtn.type = 'button';
            editBtn.className = 'message-live-action';
            editBtn.title = 'ویرایش پیام';
            editBtn.textContent = '✎';
            editBtn.addEventListener('click', () => {
                if (!socket.connected) {
                    Zang.toast('برای ویرایش، اتصال زنده لازم است', 'error');
                    return;
                }

                const current = bubble.textContent || '';
                const content = window.prompt('ویرایش پیام:', current);
                if (content === null) return;

                const trimmed = content.trim();
                if (!trimmed || trimmed === current) return;

                socket.emit('message:edit', {
                    message_id: Number(messageEl.dataset.messageId),
                    content: trimmed
                }, (ack) => {
                    if (!ack?.ok) {
                        Zang.toast(ack?.error || 'ویرایش انجام نشد', 'error');
                    }
                });
            });
            actions.appendChild(editBtn);

            const deleteBtn = document.createElement('button');
            deleteBtn.type = 'button';
            deleteBtn.className = 'message-live-action danger';
            deleteBtn.title = 'حذف پیام';
            deleteBtn.textContent = '×';
            deleteBtn.addEventListener('click', () => {
                if (!socket.connected) {
                    Zang.toast('برای حذف، اتصال زنده لازم است', 'error');
                    return;
                }
                if (!window.confirm('این پیام حذف شود؟')) return;

                socket.emit('message:delete', {
                    message_id: Number(messageEl.dataset.messageId)
                }, (ack) => {
                    if (!ack?.ok) {
                        Zang.toast(ack?.error || 'حذف انجام نشد', 'error');
                    }
                });
            });
            actions.appendChild(deleteBtn);
        }

        messageEl.appendChild(actions);
    }

    function enhanceAllMessages() {
        messagesBox?.querySelectorAll('.message').forEach(enhanceMessage);
    }

    const messageObserver = new MutationObserver(() => enhanceAllMessages());
    if (messagesBox) {
        messageObserver.observe(messagesBox, { childList: true, subtree: true });
        enhanceAllMessages();
    }

    const activeObserver = new MutationObserver(() => {
        const id = activeChatId();
        if (id && id !== joinedChatId) joinActiveChat();
        enhanceAllMessages();
    });

    if (chatList) {
        activeObserver.observe(chatList, {
            subtree: true,
            childList: true,
            attributes: true,
            attributeFilter: ['class']
        });
    }

    socket.on('connect', () => {
        setStatus('● زنده و متصل', 'realtime-ok');
        joinActiveChat();
        document.body.classList.add('zang-realtime');
    });

    socket.on('disconnect', () => {
        setStatus('اتصال زنده قطع شد؛ حالت پشتیبان فعال است', 'realtime-warn');
        joinedChatId = null;
        document.body.classList.remove('zang-realtime');
    });

    socket.on('connect_error', () => {
        setStatus('در حال تلاش برای اتصال زنده…', 'realtime-warn');
    });

    socket.on('message:new', (payload) => {
        const chatId = Number(payload?.chat_id);
        if (!chatId) return;

        if (chatId === activeChatId()) {
            reloadActiveChat(chatId);
        } else {
            document.title = '🔔 پیام جدید | زنگ';
            const author = payload?.message?.username || 'کاربر';
            Zang.toast(`پیام جدید از ${author}`, 'info', 3500);
        }
    });

    socket.on('message:updated', (payload) => {
        const message = payload?.message;
        if (!message) return;

        const el = messagesBox?.querySelector(`[data-message-id="${message.id}"]`);
        const bubble = el?.querySelector('.message-bubble');
        if (bubble) {
            bubble.textContent = message.content;
            showTemporaryStatus('پیام ویرایش شد');
        } else if (Number(payload.chat_id) === activeChatId()) {
            reloadActiveChat(Number(payload.chat_id));
        }
    });

    socket.on('message:deleted', (payload) => {
        const el = messagesBox?.querySelector(`[data-message-id="${payload?.message_id}"]`);
        if (el) {
            el.classList.add('message-removing');
            setTimeout(() => el.remove(), 180);
        }
    });

    socket.on('presence:update', (payload) => {
        if (Number(payload?.chat_id) !== activeChatId()) return;
        const count = Number(payload?.online_count) || 0;
        setStatus(`● ${count} نفر آنلاین`, 'realtime-ok');
    });

    socket.on('typing:update', (payload) => {
        if (Number(payload?.chat_id) !== activeChatId()) return;
        if (payload?.username === currentUsername) return;

        clearTimeout(statusRestoreTimer);
        if (payload?.typing) {
            setStatus(`${payload.username} در حال نوشتن…`, 'realtime-ok');
            statusRestoreTimer = setTimeout(() => {
                setStatus('● زنده و متصل', 'realtime-ok');
            }, 1800);
        }
    });

    composer?.addEventListener('submit', (event) => {
        const chatId = activeChatId();
        const content = messageInput?.value.trim();

        if (!socket.connected || !chatId || !content) return;

        event.preventDefault();
        event.stopImmediatePropagation();
        sendBtn.disabled = true;

        socket.emit('message:send', {
            chat_id: chatId,
            content
        }, (ack) => {
            sendBtn.disabled = false;

            if (!ack?.ok) {
                Zang.toast(ack?.error || 'ارسال پیام انجام نشد', 'error');
                return;
            }

            messageInput.value = '';
            Zang.autoResize(messageInput);
            messageInput.focus();
            socket.emit('typing', { chat_id: chatId, typing: false });
        });
    }, true);

    messageInput?.addEventListener('input', () => {
        const chatId = activeChatId();
        if (!socket.connected || !chatId) return;

        const now = Date.now();
        if (now - lastTypingSentAt > 650) {
            socket.emit('typing', { chat_id: chatId, typing: true });
            lastTypingSentAt = now;
        }

        clearTimeout(typingTimer);
        typingTimer = setTimeout(() => {
            socket.emit('typing', { chat_id: chatId, typing: false });
        }, 1100);
    });

    const brandName = document.querySelector('.sidebar-header .brand-name');
    if (brandName && !document.querySelector('.zang-version-badge')) {
        const badge = document.createElement('span');
        badge.className = 'zang-version-badge';
        badge.textContent = 'v0.3';
        brandName.insertAdjacentElement('afterend', badge);
    }
})();
