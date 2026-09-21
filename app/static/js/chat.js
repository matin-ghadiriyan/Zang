/* ==================== Zang v0.3 | Realtime Chat ==================== */

(() => {
    'use strict';

    const shell = document.querySelector('.app-shell');
    if (!shell) return;

    const $ = (id) => document.getElementById(id);

    const chatList = $('chat-list');
    const messagesBox = $('messages');
    const conversation = $('conversation');
    const emptyState = $('empty-state');
    const conversationTitle = $('conversation-title');
    const conversationStatus = $('conversation-status');
    const conversationDescription = $('conversation-description');
    const composer = $('composer');
    const readonlyNote = $('channel-readonly-note');
    const messageInput = $('message-input');
    const sendBtn = $('send-btn');
    const copyInviteBtn = $('copy-invite-btn');
    const leaveChatBtn = $('leave-chat-btn');
    const newMessageMarker = $('new-message-marker');

    const replyPreview = $('reply-preview');
    const replyPreviewAuthor = $('reply-preview-author');
    const replyPreviewText = $('reply-preview-text');
    const cancelReplyBtn = $('cancel-reply-btn');

    const newChatBtn = $('new-chat-btn');
    const emptyNewChat = $('empty-new-chat');
    const newChannelBtn = $('new-channel-btn');
    const emptyNewChannel = $('empty-new-channel');
    const findUserBtn = $('find-user-btn');
    const emptyFindUser = $('empty-find-user');

    const searchInput = $('chat-search');
    const sidebar = $('sidebar');
    const overlay = $('overlay');
    const menuToggle = $('menu-toggle');

    const joinChatBtn = $('join-chat-btn');
    const emptyJoinChat = $('empty-join-chat');

    const findUserModal = $('find-user-modal');
    const findUserInput = $('find-user-input');
    const peopleResults = $('people-results');

    const createModal = $('create-chat-modal');
    const createTitleInput = $('create-chat-title-input');
    const createCodesInput = $('create-chat-codes-input');
    const createConfirm = $('create-chat-confirm');

    const channelModal = $('create-channel-modal');
    const channelTitleInput = $('create-channel-title-input');
    const channelDescriptionInput = $('create-channel-description-input');
    const channelCodeInput = $('create-channel-code-input');
    const channelConfirm = $('create-channel-confirm');

    const joinModal = $('join-chat-modal');
    const joinCodeInput = $('join-chat-code-input');
    const joinConfirm = $('join-chat-confirm');

    const messageSearchBtn = $('search-messages-btn');
    const messageSearchModal = $('message-search-modal');
    const messageSearchInput = $('message-search-input');
    const messageSearchResults = $('message-search-results');

    const connectionDot = $('connection-dot');
    const connectionText = $('connection-text');

    const currentUsername = shell.dataset.username;
    const currentUserId = Number(shell.dataset.userId);
    const normalPageTitle = document.title;

    let activeChatId = null;
    let activeChat = null;
    let lastMessageId = 0;
    let sending = false;
    let polling = false;
    let listRefreshing = false;
    let replyTo = null;

    let ws = null;
    let wsConnected = false;
    let reconnectAttempts = 0;
    let reconnectTimer = null;
    let pingTimer = null;
    let typingStopTimer = null;
    let typingStatusTimer = null;
    let readTimer = null;
    let userSearchTimer = null;
    let messageSearchTimer = null;

    /* ---------- UI helpers ---------- */

    function openModal(modal) {
        if (!modal) return;
        modal.hidden = false;
        document.body.classList.add('modal-open');
    }

    function closeModal(modal) {
        if (!modal) return;
        modal.hidden = true;
        if (!document.querySelector('.modal:not([hidden])')) {
            document.body.classList.remove('modal-open');
        }
    }

    document.querySelectorAll('[data-close-modal]').forEach((element) => {
        element.addEventListener('click', () => closeModal(element.closest('.modal')));
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            document.querySelectorAll('.modal:not([hidden])').forEach(closeModal);
            clearReply();
        }
    });

    function openSidebar() {
        sidebar?.classList.add('open');
        overlay?.classList.add('show');
    }

    function closeSidebar() {
        sidebar?.classList.remove('open');
        overlay?.classList.remove('show');
    }

    menuToggle?.addEventListener('click', openSidebar);
    overlay?.addEventListener('click', closeSidebar);

    function setConnectionState(state) {
        if (!connectionDot || !connectionText) return;
        connectionDot.className = `connection-dot ${state}`;
        if (state === 'live') connectionText.textContent = 'اتصال زنده WebSocket';
        else if (state === 'fallback') connectionText.textContent = 'حالت پشتیبان؛ تلاش برای اتصال زنده…';
        else connectionText.textContent = 'در حال اتصال زنده…';
    }

    function kindLabel(chat) {
        if (chat.kind === 'channel') return `کانال • ${chat.members_count} عضو`;
        if (chat.kind === 'direct') return 'گفتگوی مستقیم';
        return `گروه • ${chat.members_count} عضو`;
    }

    function kindIcon(chat) {
        if (chat.kind === 'channel') return '📣';
        if (chat.kind === 'direct') return '👤';
        return '👥';
    }

    function renderChatItem(chat) {
        const button = document.createElement('button');
        button.className = `chat-item ${chat.kind || 'group'}`;
        button.dataset.chatId = chat.id;
        button.dataset.title = chat.title || '';
        button.dataset.kind = chat.kind || 'group';

        const canRename = chat.kind !== 'direct' && Boolean(chat.is_admin || chat.is_owner);
        const canDelete = Boolean(chat.is_owner);
        const unread = Number(chat.unread_count || 0);

        button.innerHTML = `
            <span class="chat-avatar">${kindIcon(chat)}</span>
            <span class="chat-item-body">
                <span class="chat-item-title">${Zang.escapeHtml(chat.title || 'گفتگو')}</span>
                <span class="chat-item-meta">${Zang.escapeHtml(kindLabel(chat))}</span>
            </span>
            ${unread ? `<span class="unread-badge">${unread > 99 ? '99+' : unread}</span>` : ''}
            <span class="chat-item-actions">
                ${canRename ? '<span class="chat-action rename" data-action="rename" title="تغییر نام">✎</span>' : ''}
                ${canDelete ? '<span class="chat-action delete" data-action="delete" title="حذف">×</span>' : ''}
            </span>
        `;

        if (Number(chat.id) === Number(activeChatId)) {
            button.classList.add('active');
        }
        return button;
    }

    function renderChatList(chats) {
        if (!chatList) return;
        const scrollTop = chatList.scrollTop;
        chatList.innerHTML = '';
        chats.forEach((chat) => chatList.appendChild(renderChatItem(chat)));
        chatList.scrollTop = scrollTop;
        filterChatList();

        if (wsConnected) {
            chats.forEach((chat) => wsSend({ type: 'join', chat_id: chat.id }));
        }
    }

    function addChatToList(chat, prepend = true) {
        const existing = chatList.querySelector(`.chat-item[data-chat-id="${chat.id}"]`);
        existing?.remove();
        const item = renderChatItem(chat);
        if (prepend && chatList.firstChild) chatList.insertBefore(item, chatList.firstChild);
        else chatList.appendChild(item);
        if (wsConnected) wsSend({ type: 'join', chat_id: chat.id });
    }

    function setActiveChat(chatId) {
        activeChatId = Number(chatId);
        chatList.querySelectorAll('.chat-item').forEach((item) => {
            item.classList.toggle('active', Number(item.dataset.chatId) === activeChatId);
            if (Number(item.dataset.chatId) === activeChatId) {
                item.querySelector('.unread-badge')?.remove();
            }
        });
    }

    function filterChatList() {
        if (!searchInput || !chatList) return;
        const term = searchInput.value.trim().toLowerCase();
        chatList.querySelectorAll('.chat-item').forEach((item) => {
            const title = (item.dataset.title || '').toLowerCase();
            item.classList.toggle('hidden', term !== '' && !title.includes(term));
        });
    }

    async function refreshChatList() {
        if (listRefreshing) return;
        listRefreshing = true;
        try {
            const data = await Zang.api('/chat/api/chats');
            const chats = data.chats || [];
            renderChatList(chats);
            if (activeChatId) {
                const fresh = chats.find((chat) => Number(chat.id) === activeChatId);
                if (fresh && activeChat) {
                    activeChat = { ...activeChat, ...fresh };
                    applyChatMode(activeChat);
                }
            }
        } catch (_) {
            // Network recovery is handled by the next refresh/reconnect.
        } finally {
            listRefreshing = false;
        }
    }

    /* ---------- WebSocket ---------- */

    function wsSend(payload) {
        if (!wsConnected || !ws || ws.readyState !== WebSocket.OPEN) return false;
        try {
            ws.send(JSON.stringify(payload));
            return true;
        } catch (_) {
            return false;
        }
    }

    function connectWebSocket() {
        clearTimeout(reconnectTimer);
        if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

        setConnectionState('connecting');
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/ws`;

        try {
            ws = new WebSocket(url);
        } catch (_) {
            scheduleReconnect();
            return;
        }

        ws.addEventListener('open', () => {
            wsConnected = true;
            reconnectAttempts = 0;
            setConnectionState('live');

            chatList.querySelectorAll('.chat-item').forEach((item) => {
                wsSend({ type: 'join', chat_id: Number(item.dataset.chatId) });
            });
            if (activeChatId) wsSend({ type: 'join', chat_id: activeChatId });

            clearInterval(pingTimer);
            pingTimer = setInterval(() => wsSend({ type: 'ping' }), 25000);
        });

        ws.addEventListener('message', (event) => {
            let data;
            try { data = JSON.parse(event.data); } catch (_) { return; }
            handleRealtimeEvent(data);
        });

        ws.addEventListener('close', () => {
            wsConnected = false;
            clearInterval(pingTimer);
            setConnectionState('fallback');
            scheduleReconnect();
        });

        ws.addEventListener('error', () => {
            setConnectionState('fallback');
        });
    }

    function scheduleReconnect() {
        clearTimeout(reconnectTimer);
        reconnectAttempts += 1;
        const delay = Math.min(1000 * (2 ** Math.min(reconnectAttempts, 3)), 8000);
        reconnectTimer = setTimeout(connectWebSocket, delay);
    }

    function handleRealtimeEvent(data) {
        const type = data?.type;

        if (type === 'message:new') {
            const message = data.message;
            if (Number(data.chat_id) === activeChatId) {
                appendMessage(message, true);
                if (!document.hidden) scheduleMarkRead(message.id);
            } else if (message?.username !== currentUsername) {
                notifyNewMessage(message, chatTitleFromList(data.chat_id));
            }
            refreshChatList();
            return;
        }

        if (type === 'message:updated' || type === 'message:deleted') {
            if (Number(data.chat_id) === activeChatId && data.message) {
                replaceMessage(data.message);
            }
            return;
        }

        if (type === 'message:read') {
            if (Number(data.chat_id) === activeChatId && Number(data.user_id) !== currentUserId) {
                markReceiptsRead(Number(data.message_id));
            }
            return;
        }

        if (type === 'typing') {
            if (Number(data.chat_id) === activeChatId && Number(data.user_id) !== currentUserId) {
                showTyping(data.username, Boolean(data.typing));
            }
            return;
        }

        if (type === 'presence:snapshot') {
            if (Number(data.chat_id) === activeChatId) {
                updatePresence(data.users || []);
            }
            return;
        }

        if (type === 'chat:list:update') {
            refreshChatList();
            return;
        }

        if (type === 'chat:updated') {
            refreshChatList();
            if (activeChatId && Number(data.chat?.id) === activeChatId) {
                activeChat = { ...activeChat, ...data.chat };
                applyChatMode(activeChat);
            }
            return;
        }

        if (type === 'chat:deleted') {
            const item = chatList.querySelector(`.chat-item[data-chat-id="${data.chat_id}"]`);
            item?.remove();
            if (Number(data.chat_id) === activeChatId) resetConversation();
            return;
        }

        if (type === 'error' && data.message) {
            Zang.toast(data.message, 'error');
        }
    }

    function chatTitleFromList(chatId) {
        const item = chatList.querySelector(`.chat-item[data-chat-id="${chatId}"]`);
        return item?.dataset.title || 'زنگ';
    }

    /* ---------- Presence / typing ---------- */

    function defaultConversationStatus() {
        if (!activeChat) return 'متصل';
        if (activeChat.kind === 'channel') return `${activeChat.members_count} عضو`;
        if (activeChat.kind === 'group') return `${activeChat.members_count} عضو`;
        if (activeChat.kind === 'direct' && activeChat.peer?.last_seen_at) {
            const d = new Date(activeChat.peer.last_seen_at);
            if (!Number.isNaN(d.getTime())) {
                return `آخرین بازدید ${d.toLocaleString('fa-IR')}`;
            }
        }
        return 'گفتگوی مستقیم';
    }

    function updatePresence(users) {
        if (!activeChat) return;
        const others = users.filter((user) => Number(user.id) !== currentUserId);
        if (activeChat.kind === 'direct') {
            conversationStatus.innerHTML = others.length
                ? '<span class="live-dot"></span> آنلاین'
                : Zang.escapeHtml(defaultConversationStatus());
        } else {
            conversationStatus.innerHTML = `<span class="live-dot"></span> ${others.length + 1} آنلاین • ${activeChat.members_count} عضو`;
        }
    }

    function showTyping(username, typing) {
        clearTimeout(typingStatusTimer);
        if (!typing) {
            conversationStatus.textContent = defaultConversationStatus();
            return;
        }
        conversationStatus.textContent = `${username || 'کاربر'} در حال نوشتن…`;
        typingStatusTimer = setTimeout(() => {
            conversationStatus.textContent = defaultConversationStatus();
        }, 1800);
    }

    /* ---------- Messages ---------- */

    function renderMessage(message) {
        const isMine = Number(message.user_id) === currentUserId || message.username === currentUsername;
        const canDelete = isMine || Boolean(activeChat?.is_admin || activeChat?.is_owner);
        const wrapper = document.createElement('div');
        wrapper.className = `message ${isMine ? 'mine' : 'other'}${message.is_deleted ? ' deleted-message' : ''}`;
        wrapper.dataset.messageId = message.id;
        wrapper.dataset.userId = message.user_id || '';
        wrapper.dataset.content = message.content || '';

        const name = Zang.escapeHtml(message.username || 'ناشناس');
        const content = message.is_deleted
            ? '<em>این پیام حذف شده است</em>'
            : Zang.escapeHtml(message.content || '');

        let replyHtml = '';
        if (message.reply_to) {
            const replyText = message.reply_to.is_deleted
                ? 'پیام حذف شده'
                : message.reply_to.content || '';
            replyHtml = `
                <button class="message-reply-context" data-jump-to="${message.reply_to.id}" type="button">
                    <strong>${Zang.escapeHtml(message.reply_to.username || 'کاربر')}</strong>
                    <span>${Zang.escapeHtml(replyText)}</span>
                </button>
            `;
        }

        const edited = message.edited_at && !message.is_deleted
            ? '<span class="edited-label">ویرایش شده</span>'
            : '';
        const receipt = isMine
            ? `<span class="read-receipt ${Number(message.read_by_count || 0) > 1 ? 'read' : ''}">${Number(message.read_by_count || 0) > 1 ? '✓✓' : '✓'}</span>`
            : '';

        const actions = message.is_deleted ? '' : `
            <span class="message-actions">
                <button type="button" data-message-action="reply" title="پاسخ">↩</button>
                ${isMine ? '<button type="button" data-message-action="edit" title="ویرایش">✎</button>' : ''}
                ${canDelete ? '<button type="button" data-message-action="delete" title="حذف">×</button>' : ''}
            </span>
        `;

        wrapper.innerHTML = `
            <span class="message-author">${name}</span>
            ${replyHtml}
            <div class="message-bubble">${content}</div>
            <span class="message-meta">
                <span class="message-time">${Zang.formatTime(message.created_at)}</span>
                ${edited}
                ${receipt}
            </span>
            ${actions}
        `;
        return wrapper;
    }

    function hasMessage(messageId) {
        return Boolean(messagesBox.querySelector(`[data-message-id="${messageId}"]`));
    }

    function appendMessage(message, shouldNotify = false) {
        if (!message || hasMessage(message.id)) return;
        const nearBottom = isNearBottom();
        messagesBox.appendChild(renderMessage(message));
        lastMessageId = Math.max(lastMessageId, Number(message.id) || 0);

        if (nearBottom || Number(message.user_id) === currentUserId) {
            scrollToBottom();
        } else {
            newMessageMarker?.classList.remove('hidden');
        }

        if (shouldNotify && Number(message.user_id) !== currentUserId) {
            notifyNewMessage(message, activeChat?.title || 'زنگ');
        }
    }

    function replaceMessage(message) {
        const current = messagesBox.querySelector(`[data-message-id="${message.id}"]`);
        if (!current) {
            appendMessage(message);
            return;
        }
        current.replaceWith(renderMessage(message));
    }

    function isNearBottom() {
        return messagesBox.scrollHeight - messagesBox.scrollTop - messagesBox.clientHeight < 150;
    }

    function scrollToBottom() {
        messagesBox.scrollTop = messagesBox.scrollHeight;
        newMessageMarker?.classList.add('hidden');
    }

    function markReceiptsRead(messageId) {
        messagesBox.querySelectorAll('.message.mine').forEach((messageEl) => {
            if (Number(messageEl.dataset.messageId) <= messageId) {
                const receipt = messageEl.querySelector('.read-receipt');
                if (receipt) {
                    receipt.textContent = '✓✓';
                    receipt.classList.add('read');
                }
            }
        });
    }

    function notifyNewMessage(message, title) {
        if (document.hidden) document.title = '🔔 پیام جدید | زنگ';
        if ('Notification' in window && Notification.permission === 'granted') {
            try {
                new Notification(title || 'زنگ', {
                    body: `${message.username || 'کاربر'}: ${message.content || 'پیام جدید'}`,
                    icon: '/static/img/zang-logo.svg'
                });
            } catch (_) {}
        }
    }

    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            document.title = normalPageTitle;
            if (activeChatId && lastMessageId) scheduleMarkRead(lastMessageId);
        }
    });
    window.addEventListener('focus', () => {
        document.title = normalPageTitle;
        if (activeChatId && lastMessageId) scheduleMarkRead(lastMessageId);
    });

    /* ---------- Active chat ---------- */

    function applyChatMode(chat) {
        activeChat = chat;
        conversationTitle.textContent = chat.title || 'گفتگو';
        conversationDescription.textContent = chat.description || '';
        conversationStatus.textContent = defaultConversationStatus();

        const canPost = chat.can_post !== false;
        composer.classList.toggle('hidden', !canPost);
        readonlyNote.classList.toggle('hidden', canPost);

        if (chat.invite_code) {
            copyInviteBtn.hidden = false;
            copyInviteBtn.dataset.code = chat.invite_code;
        } else {
            copyInviteBtn.hidden = true;
            delete copyInviteBtn.dataset.code;
        }

        leaveChatBtn.hidden = Boolean(chat.is_owner) || chat.kind === 'direct';
    }

    async function loadChat(chatId) {
        try {
            const data = await Zang.api(`/chat/api/chats/${chatId}`);
            const chat = data.chat;

            setActiveChat(chat.id);
            applyChatMode(chat);
            clearReply();

            messagesBox.innerHTML = '';
            lastMessageId = 0;
            (chat.messages || []).forEach((message) => {
                messagesBox.appendChild(renderMessage(message));
                lastMessageId = Math.max(lastMessageId, Number(message.id) || 0);
            });

            emptyState.classList.add('hidden');
            conversation.classList.remove('hidden');
            scrollToBottom();
            closeSidebar();

            if (wsConnected) wsSend({ type: 'join', chat_id: chat.id });
            if (lastMessageId) scheduleMarkRead(lastMessageId);
        } catch (error) {
            Zang.toast(error.message, 'error');
        }
    }

    function resetConversation() {
        activeChatId = null;
        activeChat = null;
        lastMessageId = 0;
        messagesBox.innerHTML = '';
        conversation.classList.add('hidden');
        emptyState.classList.remove('hidden');
        clearReply();
    }

    /* ---------- Read state ---------- */

    function scheduleMarkRead(messageId) {
        if (!activeChatId || document.hidden) return;
        clearTimeout(readTimer);
        readTimer = setTimeout(() => markRead(messageId), 350);
    }

    async function markRead(messageId) {
        if (!activeChatId || !messageId) return;
        if (wsConnected) {
            wsSend({ type: 'read', chat_id: activeChatId, message_id: messageId });
        } else {
            try {
                await Zang.api(`/chat/api/chats/${activeChatId}/read`, {
                    method: 'POST',
                    body: JSON.stringify({ message_id: messageId })
                });
            } catch (_) {}
        }
        const badge = chatList.querySelector(`.chat-item[data-chat-id="${activeChatId}"] .unread-badge`);
        badge?.remove();
    }

    /* ---------- Polling fallback ---------- */

    async function pollMessagesFallback() {
        if (wsConnected || !activeChatId || polling) return;
        const chatId = activeChatId;
        polling = true;
        try {
            const data = await Zang.api(`/chat/api/chats/${chatId}/messages?after_id=${lastMessageId}`);
            if (chatId !== activeChatId) return;
            if (data.chat) {
                activeChat = { ...activeChat, ...data.chat };
                applyChatMode(activeChat);
            }
            (data.messages || []).forEach((message) => appendMessage(message, true));
            if (data.latest_id) lastMessageId = Math.max(lastMessageId, Number(data.latest_id));
        } catch (_) {
        } finally {
            polling = false;
        }
    }

    setInterval(pollMessagesFallback, 4500);
    setInterval(refreshChatList, 12000);

    /* ---------- Reply / edit / delete ---------- */

    function setReply(messageEl) {
        if (!messageEl) return;
        replyTo = {
            id: Number(messageEl.dataset.messageId),
            username: messageEl.querySelector('.message-author')?.textContent || 'کاربر',
            content: messageEl.dataset.content || ''
        };
        replyPreviewAuthor.textContent = `پاسخ به ${replyTo.username}`;
        replyPreviewText.textContent = replyTo.content.slice(0, 180);
        replyPreview.classList.remove('hidden');
        messageInput.focus();
    }

    function clearReply() {
        replyTo = null;
        replyPreview?.classList.add('hidden');
        if (replyPreviewText) replyPreviewText.textContent = '';
    }

    cancelReplyBtn?.addEventListener('click', clearReply);

    async function editMessage(messageEl) {
        const messageId = Number(messageEl.dataset.messageId);
        const current = messageEl.dataset.content || '';
        const next = window.prompt('متن جدید پیام:', current);
        if (next === null) return;
        const content = next.trim();
        if (!content) return Zang.toast('متن پیام نمی‌تواند خالی باشد', 'error');

        try {
            const data = await Zang.api(`/chat/api/messages/${messageId}`, {
                method: 'PATCH',
                body: JSON.stringify({ content })
            });
            replaceMessage(data.message);
            Zang.toast('پیام ویرایش شد', 'success');
        } catch (error) {
            Zang.toast(error.message, 'error');
        }
    }

    async function deleteMessage(messageEl) {
        const messageId = Number(messageEl.dataset.messageId);
        if (!window.confirm('این پیام حذف شود؟')) return;
        try {
            const data = await Zang.api(`/chat/api/messages/${messageId}`, { method: 'DELETE' });
            replaceMessage(data.message);
        } catch (error) {
            Zang.toast(error.message, 'error');
        }
    }

    messagesBox?.addEventListener('click', (event) => {
        const jump = event.target.closest('[data-jump-to]');
        if (jump) {
            const target = messagesBox.querySelector(`[data-message-id="${jump.dataset.jumpTo}"]`);
            target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            target?.classList.add('message-highlight');
            setTimeout(() => target?.classList.remove('message-highlight'), 1200);
            return;
        }

        const actionButton = event.target.closest('[data-message-action]');
        if (!actionButton) return;
        const messageEl = actionButton.closest('.message');
        const action = actionButton.dataset.messageAction;
        if (action === 'reply') setReply(messageEl);
        if (action === 'edit') editMessage(messageEl);
        if (action === 'delete') deleteMessage(messageEl);
    });

    /* ---------- Send + typing ---------- */

    async function sendMessage(event) {
        event.preventDefault();
        if (sending || !activeChatId) return;
        const content = messageInput.value.trim();
        if (!content) return;

        sending = true;
        sendBtn.disabled = true;
        try {
            const data = await Zang.api(`/chat/api/chats/${activeChatId}/messages`, {
                method: 'POST',
                body: JSON.stringify({
                    content,
                    reply_to_id: replyTo?.id || null
                })
            });
            appendMessage(data.message);
            messageInput.value = '';
            Zang.autoResize(messageInput);
            clearReply();
            wsSend({ type: 'typing', chat_id: activeChatId, typing: false });
        } catch (error) {
            Zang.toast(error.message, 'error');
        } finally {
            sending = false;
            sendBtn.disabled = false;
            messageInput.focus();
        }
    }

    composer?.addEventListener('submit', sendMessage);

    messageInput?.addEventListener('input', () => {
        Zang.autoResize(messageInput);
        if (activeChatId && wsConnected) {
            wsSend({ type: 'typing', chat_id: activeChatId, typing: true });
            clearTimeout(typingStopTimer);
            typingStopTimer = setTimeout(() => {
                wsSend({ type: 'typing', chat_id: activeChatId, typing: false });
            }, 1100);
        }
    });

    messageInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            composer.requestSubmit();
        }
    });

    /* ---------- Create / join / direct ---------- */

    function openCreateModal() {
        createTitleInput.value = '';
        createCodesInput.value = '';
        openModal(createModal);
        createTitleInput.focus();
    }

    async function submitCreateChat() {
        const title = createTitleInput.value.trim() || 'گروه جدید';
        const codes = createCodesInput.value.trim();
        createConfirm.disabled = true;
        try {
            const data = await Zang.api('/chat/api/chats', {
                method: 'POST',
                body: JSON.stringify({ title, codes })
            });
            addChatToList(data.chat, true);
            closeModal(createModal);
            await loadChat(data.chat.id);
            Zang.toast(`گروه ساخته شد${data.invite_code ? ` — کد: ${data.invite_code}` : ''}`, 'success', 6000);
        } catch (error) {
            Zang.toast(error.message, 'error');
        } finally {
            createConfirm.disabled = false;
        }
    }

    function openChannelModal() {
        channelTitleInput.value = '';
        channelDescriptionInput.value = '';
        channelCodeInput.value = '';
        openModal(channelModal);
        channelTitleInput.focus();
    }

    async function submitCreateChannel() {
        const title = channelTitleInput.value.trim();
        if (title.length < 2) return Zang.toast('نام کانال را وارد کن', 'error');
        channelConfirm.disabled = true;
        try {
            const data = await Zang.api('/chat/api/channels', {
                method: 'POST',
                body: JSON.stringify({
                    title,
                    description: channelDescriptionInput.value.trim(),
                    code: channelCodeInput.value.trim()
                })
            });
            addChatToList(data.chat, true);
            closeModal(channelModal);
            await loadChat(data.chat.id);
            Zang.toast(`کانال ساخته شد — کد: ${data.invite_code}`, 'success', 6500);
        } catch (error) {
            Zang.toast(error.message, 'error');
        } finally {
            channelConfirm.disabled = false;
        }
    }

    function openJoinModal() {
        joinCodeInput.value = '';
        openModal(joinModal);
        joinCodeInput.focus();
    }

    async function submitJoinChat() {
        const code = joinCodeInput.value.trim();
        if (!code) return Zang.toast('کد دعوت را وارد کن', 'error');
        joinConfirm.disabled = true;
        try {
            const data = await Zang.api('/chat/api/chats/join', {
                method: 'POST',
                body: JSON.stringify({ code })
            });
            (data.chats || []).forEach((chat) => addChatToList(chat, true));
            closeModal(joinModal);
            if (data.chats?.length) await loadChat(data.chats[0].id);
            Zang.toast('با موفقیت وارد شدی', 'success');
        } catch (error) {
            Zang.toast(error.message, 'error');
        } finally {
            joinConfirm.disabled = false;
        }
    }

    function openFindUserModal() {
        findUserInput.value = '';
        peopleResults.innerHTML = '<div class="search-empty">نام کاربری را وارد کن.</div>';
        openModal(findUserModal);
        findUserInput.focus();
    }

    async function searchPeople() {
        const q = findUserInput.value.trim();
        if (q.length < 2) {
            peopleResults.innerHTML = '<div class="search-empty">حداقل دو حرف بنویس.</div>';
            return;
        }
        try {
            const data = await Zang.api(`/chat/api/users?q=${encodeURIComponent(q)}`);
            const users = data.users || [];
            peopleResults.innerHTML = users.length ? '' : '<div class="search-empty">کاربری پیدا نشد.</div>';
            users.forEach((user) => {
                const row = document.createElement('button');
                row.type = 'button';
                row.className = 'person-result';
                row.dataset.userId = user.id;
                row.innerHTML = `<span class="person-avatar">${Zang.escapeHtml(user.username.charAt(0).toUpperCase())}</span><span><strong>@${Zang.escapeHtml(user.username)}</strong><small>شروع گفتگوی مستقیم</small></span><span>←</span>`;
                peopleResults.appendChild(row);
            });
        } catch (error) {
            peopleResults.innerHTML = `<div class="search-empty">${Zang.escapeHtml(error.message)}</div>`;
        }
    }

    findUserInput?.addEventListener('input', () => {
        clearTimeout(userSearchTimer);
        userSearchTimer = setTimeout(searchPeople, 280);
    });

    peopleResults?.addEventListener('click', async (event) => {
        const row = event.target.closest('[data-user-id]');
        if (!row) return;
        row.disabled = true;
        try {
            const data = await Zang.api(`/chat/api/direct/${row.dataset.userId}`, { method: 'POST' });
            addChatToList(data.chat, true);
            closeModal(findUserModal);
            await loadChat(data.chat.id);
        } catch (error) {
            Zang.toast(error.message, 'error');
        } finally {
            row.disabled = false;
        }
    });

    /* ---------- Rename / delete / leave ---------- */

    async function renameChat(chatId, currentTitle) {
        const title = window.prompt('عنوان جدید:', currentTitle || '');
        if (title === null || !title.trim()) return;
        try {
            const data = await Zang.api(`/chat/api/chats/${chatId}`, {
                method: 'PATCH',
                body: JSON.stringify({ title: title.trim() })
            });
            const item = chatList.querySelector(`.chat-item[data-chat-id="${chatId}"]`);
            item?.replaceWith(renderChatItem(data.chat));
            if (activeChatId === Number(chatId)) applyChatMode({ ...activeChat, ...data.chat });
            Zang.toast('عنوان تغییر کرد', 'success');
        } catch (error) {
            Zang.toast(error.message, 'error');
        }
    }

    async function deleteChat(chatId) {
        if (!window.confirm('این گفتگو و پیام‌هایش حذف شود؟')) return;
        try {
            await Zang.api(`/chat/api/chats/${chatId}`, { method: 'DELETE' });
            chatList.querySelector(`.chat-item[data-chat-id="${chatId}"]`)?.remove();
            if (activeChatId === Number(chatId)) resetConversation();
            Zang.toast('حذف شد', 'success');
        } catch (error) {
            Zang.toast(error.message, 'error');
        }
    }

    async function leaveChat() {
        if (!activeChatId || !window.confirm('این گفتگو را ترک می‌کنی؟')) return;
        try {
            await Zang.api(`/chat/api/chats/${activeChatId}/leave`, { method: 'POST' });
            chatList.querySelector(`.chat-item[data-chat-id="${activeChatId}"]`)?.remove();
            resetConversation();
            Zang.toast('گفتگو را ترک کردی', 'success');
        } catch (error) {
            Zang.toast(error.message, 'error');
        }
    }

    /* ---------- Message search ---------- */

    function openMessageSearch() {
        if (!activeChatId) return;
        messageSearchInput.value = '';
        messageSearchResults.innerHTML = '<div class="search-empty">عبارت جستجو را وارد کن.</div>';
        openModal(messageSearchModal);
        messageSearchInput.focus();
    }

    async function searchMessages() {
        const q = messageSearchInput.value.trim();
        if (!activeChatId || q.length < 2) {
            messageSearchResults.innerHTML = '<div class="search-empty">حداقل دو حرف بنویس.</div>';
            return;
        }
        try {
            const data = await Zang.api(`/chat/api/chats/${activeChatId}/search?q=${encodeURIComponent(q)}`);
            const messages = data.messages || [];
            messageSearchResults.innerHTML = messages.length ? '' : '<div class="search-empty">پیامی پیدا نشد.</div>';
            messages.forEach((message) => {
                const row = document.createElement('button');
                row.type = 'button';
                row.className = 'message-search-result';
                row.dataset.messageId = message.id;
                row.innerHTML = `<strong>${Zang.escapeHtml(message.username || 'کاربر')}</strong><span>${Zang.escapeHtml(message.content || '')}</span>`;
                messageSearchResults.appendChild(row);
            });
        } catch (error) {
            messageSearchResults.innerHTML = `<div class="search-empty">${Zang.escapeHtml(error.message)}</div>`;
        }
    }

    messageSearchInput?.addEventListener('input', () => {
        clearTimeout(messageSearchTimer);
        messageSearchTimer = setTimeout(searchMessages, 280);
    });

    messageSearchResults?.addEventListener('click', (event) => {
        const row = event.target.closest('[data-message-id]');
        if (!row) return;
        closeModal(messageSearchModal);
        const target = messagesBox.querySelector(`[data-message-id="${row.dataset.messageId}"]`);
        target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        target?.classList.add('message-highlight');
        setTimeout(() => target?.classList.remove('message-highlight'), 1200);
    });

    /* ---------- Events ---------- */

    chatList?.addEventListener('click', (event) => {
        const item = event.target.closest('.chat-item');
        if (!item) return;
        const chatId = Number(item.dataset.chatId);
        const action = event.target.closest('[data-action]')?.dataset.action;
        if (action === 'rename') {
            event.stopPropagation();
            renameChat(chatId, item.dataset.title);
            return;
        }
        if (action === 'delete') {
            event.stopPropagation();
            deleteChat(chatId);
            return;
        }
        loadChat(chatId);
    });

    newChatBtn?.addEventListener('click', openCreateModal);
    emptyNewChat?.addEventListener('click', openCreateModal);
    createConfirm?.addEventListener('click', submitCreateChat);

    newChannelBtn?.addEventListener('click', openChannelModal);
    emptyNewChannel?.addEventListener('click', openChannelModal);
    channelConfirm?.addEventListener('click', submitCreateChannel);

    joinChatBtn?.addEventListener('click', openJoinModal);
    emptyJoinChat?.addEventListener('click', openJoinModal);
    joinConfirm?.addEventListener('click', submitJoinChat);

    findUserBtn?.addEventListener('click', openFindUserModal);
    emptyFindUser?.addEventListener('click', openFindUserModal);

    messageSearchBtn?.addEventListener('click', openMessageSearch);
    leaveChatBtn?.addEventListener('click', leaveChat);

    copyInviteBtn?.addEventListener('click', async () => {
        const code = copyInviteBtn.dataset.code;
        if (!code) return;
        try {
            await navigator.clipboard.writeText(code);
            Zang.toast('کد دعوت کپی شد', 'success');
        } catch (_) {
            window.prompt('کد دعوت:', code);
        }
    });

    searchInput?.addEventListener('input', filterChatList);
    newMessageMarker?.addEventListener('click', scrollToBottom);
    messagesBox?.addEventListener('scroll', () => {
        if (isNearBottom()) newMessageMarker?.classList.add('hidden');
    });

    createCodesInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') { event.preventDefault(); submitCreateChat(); }
    });
    channelCodeInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') { event.preventDefault(); submitCreateChannel(); }
    });
    joinCodeInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') { event.preventDefault(); submitJoinChat(); }
    });

    /* ---------- Start ---------- */

    connectWebSocket();
    refreshChatList();

    const firstChat = chatList?.querySelector('.chat-item');
    if (firstChat) loadChat(Number(firstChat.dataset.chatId));
})();
