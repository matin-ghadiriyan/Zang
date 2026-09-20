/* ==================== Zang | Chat ==================== */

(() => {
    'use strict';

    const shell = document.querySelector('.app-shell');
    if (!shell) return;

    const chatList = document.getElementById('chat-list');
    const messagesBox = document.getElementById('messages');
    const conversation = document.getElementById('conversation');
    const emptyState = document.getElementById('empty-state');
    const conversationTitle = document.getElementById('conversation-title');
    const conversationStatus = document.getElementById('conversation-status');
    const composer = document.getElementById('composer');
    const readonlyNote = document.getElementById('channel-readonly-note');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const copyInviteBtn = document.getElementById('copy-invite-btn');

    const newChatBtn = document.getElementById('new-chat-btn');
    const emptyNewChat = document.getElementById('empty-new-chat');
    const newChannelBtn = document.getElementById('new-channel-btn');
    const emptyNewChannel = document.getElementById('empty-new-channel');

    const searchInput = document.getElementById('chat-search');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');
    const menuToggle = document.getElementById('menu-toggle');

    const joinChatBtn = document.getElementById('join-chat-btn');
    const emptyJoinChat = document.getElementById('empty-join-chat');

    const createModal = document.getElementById('create-chat-modal');
    const createTitleInput = document.getElementById('create-chat-title-input');
    const createCodesInput = document.getElementById('create-chat-codes-input');
    const createConfirm = document.getElementById('create-chat-confirm');

    const channelModal = document.getElementById('create-channel-modal');
    const channelTitleInput = document.getElementById('create-channel-title-input');
    const channelCodeInput = document.getElementById('create-channel-code-input');
    const channelConfirm = document.getElementById('create-channel-confirm');

    const joinModal = document.getElementById('join-chat-modal');
    const joinCodeInput = document.getElementById('join-chat-code-input');
    const joinConfirm = document.getElementById('join-chat-confirm');

    const currentUsername = shell.dataset.username;
    const normalPageTitle = document.title;

    let activeChatId = null;
    let activeChat = null;
    let lastMessageId = 0;
    let sending = false;
    let polling = false;
    let listPolling = false;

    function openModal(modal) {
        if (!modal) return;
        modal.hidden = false;
        document.body.classList.add('modal-open');
    }

    function closeModal(modal) {
        if (!modal) return;
        modal.hidden = true;
        document.body.classList.remove('modal-open');
    }

    document.querySelectorAll('[data-close-modal]').forEach((element) => {
        element.addEventListener('click', () => closeModal(element.closest('.modal')));
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            document.querySelectorAll('.modal:not([hidden])').forEach(closeModal);
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

    function chatMeta(chat) {
        if (chat.kind === 'channel') {
            return `کانال • ${chat.members_count} عضو • ${chat.messages_count} پیام`;
        }
        return `${chat.messages_count} پیام`;
    }

    function renderChatItem(chat) {
        const button = document.createElement('button');
        button.className = `chat-item${chat.kind === 'channel' ? ' channel' : ''}`;
        button.dataset.chatId = chat.id;
        button.dataset.title = chat.title;
        button.dataset.kind = chat.kind || 'chat';

        const avatar = chat.kind === 'channel'
            ? '📣'
            : Zang.escapeHtml((chat.title || '?').charAt(0));

        const canRename = chat.kind !== 'channel' || chat.is_owner;
        const canDelete = Boolean(chat.is_owner);

        button.innerHTML = `
            <span class="chat-avatar">${avatar}</span>
            <span class="chat-item-body">
                <span class="chat-item-title">${Zang.escapeHtml(chat.title)}</span>
                <span class="chat-item-meta">${Zang.escapeHtml(chatMeta(chat))}</span>
            </span>
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
        const currentScroll = chatList.scrollTop;
        chatList.innerHTML = '';
        chats.forEach((chat) => chatList.appendChild(renderChatItem(chat)));
        chatList.scrollTop = currentScroll;
        filterChatList();
    }

    function addChatToList(chat, prepend = true) {
        const existing = chatList.querySelector(`.chat-item[data-chat-id="${chat.id}"]`);
        if (existing) existing.remove();

        const item = renderChatItem(chat);
        if (prepend && chatList.firstChild) {
            chatList.insertBefore(item, chatList.firstChild);
        } else {
            chatList.appendChild(item);
        }
    }

    function setActiveChat(chatId) {
        activeChatId = Number(chatId);
        chatList.querySelectorAll('.chat-item').forEach((item) => {
            item.classList.toggle('active', Number(item.dataset.chatId) === activeChatId);
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
        if (listPolling) return;
        listPolling = true;
        try {
            const data = await Zang.api('/chat/api/chats');
            renderChatList(data.chats || []);
        } catch (_) {
            // نوبت بعدی دوباره تلاش می‌کند.
        } finally {
            listPolling = false;
        }
    }

    function renderMessage(message) {
        const isMine = message.username === currentUsername;
        const wrapper = document.createElement('div');
        wrapper.className = `message ${isMine ? 'mine' : 'other'}`;
        wrapper.dataset.messageId = message.id;

        const name = Zang.escapeHtml(message.username || 'ناشناس');

        wrapper.innerHTML = `
            <span class="message-author">${name}</span>
            <div class="message-bubble">${Zang.escapeHtml(message.content)}</div>
            <span class="message-time">${Zang.formatTime(message.created_at)}</span>
        `;

        return wrapper;
    }

    function hasMessage(messageId) {
        return Boolean(messagesBox.querySelector(`[data-message-id="${messageId}"]`));
    }

    function appendMessage(message, shouldNotify = false) {
        if (!message || hasMessage(message.id)) return;

        const nearBottom =
            messagesBox.scrollHeight - messagesBox.scrollTop - messagesBox.clientHeight < 120;

        messagesBox.appendChild(renderMessage(message));
        lastMessageId = Math.max(lastMessageId, Number(message.id) || 0);

        if (nearBottom || message.username === currentUsername) {
            scrollToBottom();
        }

        if (shouldNotify && message.username !== currentUsername) {
            notifyNewMessage(message);
        }
    }

    function scrollToBottom() {
        messagesBox.scrollTop = messagesBox.scrollHeight;
    }

    function notifyNewMessage(message) {
        if (document.hidden) {
            document.title = '🔔 پیام جدید | زنگ';
        }

        if ('Notification' in window && Notification.permission === 'granted') {
            try {
                new Notification(activeChat?.title || 'زنگ', {
                    body: `${message.username || 'کاربر'}: ${message.content}`,
                    icon: '/static/img/zang-logo.svg'
                });
            } catch (_) {}
        }
    }

    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) document.title = normalPageTitle;
    });

    window.addEventListener('focus', () => {
        document.title = normalPageTitle;
    });

    function applyChatMode(chat) {
        activeChat = chat;
        const isChannel = chat.kind === 'channel';

        conversationTitle.textContent = chat.title;
        conversationStatus.innerHTML = isChannel
            ? `<span class="live-dot"></span> کانال • ${chat.members_count} عضو`
            : '<span class="live-dot"></span> همگام‌سازی خودکار';

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
    }

    async function loadChat(chatId) {
        try {
            const data = await Zang.api(`/chat/api/chats/${chatId}`);
            const chat = data.chat;

            setActiveChat(chat.id);
            applyChatMode(chat);

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
        } catch (error) {
            Zang.toast(error.message, 'error');
        }
    }

    async function pollMessages() {
        if (!activeChatId || polling) return;

        const chatIdAtStart = activeChatId;
        polling = true;

        try {
            const data = await Zang.api(
                `/chat/api/chats/${chatIdAtStart}/messages?after_id=${lastMessageId}`
            );

            if (chatIdAtStart !== activeChatId) return;

            if (data.chat) applyChatMode(data.chat);

            (data.messages || []).forEach((message) => {
                appendMessage(message, true);
            });

            if (data.latest_id) {
                lastMessageId = Math.max(lastMessageId, Number(data.latest_id));
            }
        } catch (_) {
            // در قطع موقت شبکه، نوبت بعدی دوباره تلاش می‌کند.
        } finally {
            polling = false;
        }
    }

    setInterval(pollMessages, 1500);
    setInterval(refreshChatList, 5000);

    function openCreateModal() {
        createTitleInput.value = '';
        createCodesInput.value = '';
        openModal(createModal);
        createTitleInput.focus();
    }

    async function submitCreateChat() {
        const title = createTitleInput.value.trim() || 'گفتگوی جدید';
        const codes = createCodesInput.value.trim();

        if (!codes) {
            Zang.toast('یک شناسه وارد کن', 'error');
            return;
        }

        createConfirm.disabled = true;
        try {
            const data = await Zang.api('/chat/api/chats', {
                method: 'POST',
                body: JSON.stringify({ title, codes })
            });

            addChatToList(data.chat, true);
            closeModal(createModal);
            await loadChat(data.chat.id);
            Zang.toast('گفتگوی جدید ساخته شد', 'success');
        } catch (error) {
            Zang.toast(error.message, 'error');
        } finally {
            createConfirm.disabled = false;
        }
    }

    function openChannelModal() {
        channelTitleInput.value = '';
        channelCodeInput.value = '';
        openModal(channelModal);
        channelTitleInput.focus();
    }

    async function submitCreateChannel() {
        const title = channelTitleInput.value.trim();
        const code = channelCodeInput.value.trim();

        if (title.length < 2) {
            Zang.toast('نام کانال را وارد کن', 'error');
            return;
        }

        channelConfirm.disabled = true;
        try {
            const data = await Zang.api('/chat/api/channels', {
                method: 'POST',
                body: JSON.stringify({ title, code })
            });

            addChatToList(data.chat, true);
            closeModal(channelModal);
            await loadChat(data.chat.id);

            const inviteCode = data.invite_code || data.chat.invite_code;
            Zang.toast(
                inviteCode
                    ? `کانال ساخته شد — کد عضویت: ${inviteCode}`
                    : 'کانال ساخته شد',
                'success',
                6500
            );
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
        if (!code) {
            Zang.toast('شناسه را وارد کن', 'error');
            return;
        }

        joinConfirm.disabled = true;
        try {
            const data = await Zang.api('/chat/api/chats/join', {
                method: 'POST',
                body: JSON.stringify({ code })
            });

            (data.chats || []).forEach((chat) => addChatToList(chat, true));
            closeModal(joinModal);

            if (data.chats && data.chats.length) {
                await loadChat(data.chats[0].id);
            }

            Zang.toast('با موفقیت وارد شدی', 'success');
        } catch (error) {
            Zang.toast(error.message, 'error');
        } finally {
            joinConfirm.disabled = false;
        }
    }

    async function renameChat(chatId, currentTitle) {
        const title = window.prompt('عنوان جدید:', currentTitle.replace(/^#/, ''));
        if (title === null) return;

        const trimmed = title.trim();
        if (!trimmed) {
            Zang.toast('عنوان نمی‌تواند خالی باشد', 'error');
            return;
        }

        try {
            const data = await Zang.api(`/chat/api/chats/${chatId}`, {
                method: 'PATCH',
                body: JSON.stringify({ title: trimmed })
            });

            const item = chatList.querySelector(`.chat-item[data-chat-id="${chatId}"]`);
            if (item) item.replaceWith(renderChatItem(data.chat));

            if (activeChatId === Number(chatId)) {
                applyChatMode(data.chat);
            }

            Zang.toast('عنوان تغییر کرد', 'success');
        } catch (error) {
            Zang.toast(error.message, 'error');
        }
    }

    async function deleteChat(chatId) {
        if (!window.confirm('این گفتگو/کانال و همه پیام‌هایش حذف شود؟')) return;

        try {
            await Zang.api(`/chat/api/chats/${chatId}`, { method: 'DELETE' });

            const item = chatList.querySelector(`.chat-item[data-chat-id="${chatId}"]`);
            item?.remove();

            if (activeChatId === Number(chatId)) {
                activeChatId = null;
                activeChat = null;
                lastMessageId = 0;
                conversation.classList.add('hidden');
                emptyState.classList.remove('hidden');
            }

            Zang.toast('حذف شد', 'success');
        } catch (error) {
            Zang.toast(error.message, 'error');
        }
    }

    async function sendMessage(event) {
        event.preventDefault();
        if (sending || !activeChatId || activeChat?.can_post === false) return;

        const content = messageInput.value.trim();
        if (!content) return;

        sending = true;
        sendBtn.disabled = true;

        try {
            const data = await Zang.api(`/chat/api/chats/${activeChatId}/messages`, {
                method: 'POST',
                body: JSON.stringify({ content })
            });

            appendMessage(data.message, false);
            messageInput.value = '';
            Zang.autoResize(messageInput);
            refreshChatList();
        } catch (error) {
            Zang.toast(error.message, 'error');
        } finally {
            sending = false;
            sendBtn.disabled = false;
            messageInput.focus();
        }
    }

    copyInviteBtn?.addEventListener('click', async () => {
        const code = copyInviteBtn.dataset.code;
        if (!code) return;

        try {
            await navigator.clipboard.writeText(code);
            Zang.toast(`کد عضویت کپی شد: ${code}`, 'success', 4500);
        } catch (_) {
            window.prompt('کد عضویت کانال:', code);
        }
    });

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

    createCodesInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            submitCreateChat();
        }
    });

    channelCodeInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            submitCreateChannel();
        }
    });

    joinCodeInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            submitJoinChat();
        }
    });

    composer?.addEventListener('submit', sendMessage);
    messageInput?.addEventListener('input', () => Zang.autoResize(messageInput));

    messageInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            composer.requestSubmit();
        }
    });

    searchInput?.addEventListener('input', filterChatList);

    const firstChat = chatList?.querySelector('.chat-item');
    if (firstChat) {
        loadChat(Number(firstChat.dataset.chatId));
    }
})();
