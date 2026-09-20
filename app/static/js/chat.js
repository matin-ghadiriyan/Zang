/* ==================== Zang | Chat ==================== */

(() => {
    'use strict';

    const shell = document.querySelector('.app-shell');
    if (!shell) return;

    /* ---------- Elements ---------- */
    const chatList = document.getElementById('chat-list');
    const messagesBox = document.getElementById('messages');
    const conversation = document.getElementById('conversation');
    const emptyState = document.getElementById('empty-state');
    const conversationTitle = document.getElementById('conversation-title');
    const composer = document.getElementById('composer');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const emptyNewChat = document.getElementById('empty-new-chat');
    const searchInput = document.getElementById('chat-search');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');
    const menuToggle = document.getElementById('menu-toggle');
    const joinChatBtn = document.getElementById('join-chat-btn');
    const emptyJoinChat = document.getElementById('empty-join-chat');
    const createModal = document.getElementById('create-chat-modal');
    const joinModal = document.getElementById('join-chat-modal');
    const createTitleInput = document.getElementById('create-chat-title-input');
    const createCodesInput = document.getElementById('create-chat-codes-input');
    const createConfirm = document.getElementById('create-chat-confirm');
    const joinCodeInput = document.getElementById('join-chat-code-input');
    const joinConfirm = document.getElementById('join-chat-confirm');

    let activeChatId = null;
    let sending = false;

    /* ---------- Modals ---------- */
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
        element.addEventListener('click', () => {
            closeModal(element.closest('.modal'));
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            document.querySelectorAll('.modal:not([hidden])').forEach(closeModal);
        }
    });

    /* ---------- Sidebar (mobile) ---------- */
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

    /* ---------- Chat List ---------- */
    function renderChatItem(chat) {
        const button = document.createElement('button');
        button.className = 'chat-item';
        button.dataset.chatId = chat.id;
        button.dataset.title = chat.title;

        button.innerHTML = `
            <span class="chat-avatar">${Zang.escapeHtml(chat.title.charAt(0))}</span>
            <span class="chat-item-body">
                <span class="chat-item-title">${Zang.escapeHtml(chat.title)}</span>
                <span class="chat-item-meta">${chat.messages_count} پیام</span>
            </span>
            <span class="chat-item-actions">
                <span class="chat-action rename" data-action="rename" title="تغییر نام">
                    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
                </span>
                <span class="chat-action delete" data-action="delete" title="حذف">
                    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/></svg>
                </span>
            </span>
        `;

        return button;
    }

    function addChatToList(chat, prepend = true) {
        const item = renderChatItem(chat);
        if (prepend && chatList.firstChild) {
            chatList.insertBefore(item, chatList.firstChild);
        } else {
            chatList.appendChild(item);
        }
    }

    function setActiveChat(chatId) {
        activeChatId = chatId;
        chatList.querySelectorAll('.chat-item').forEach((item) => {
            item.classList.toggle('active', Number(item.dataset.chatId) === chatId);
        });
    }

    /* ---------- Messages ---------- */
    const currentUsername = shell.dataset.username;

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

    function appendMessage(message) {
        messagesBox.appendChild(renderMessage(message));
        scrollToBottom();
    }

    function scrollToBottom() {
        messagesBox.scrollTop = messagesBox.scrollHeight;
    }

    /* ---------- Load Chat ---------- */
    async function loadChat(chatId) {
        try {
            const data = await Zang.api(`/chat/api/chats/${chatId}`);
            const chat = data.chat;

            setActiveChat(chat.id);
            conversationTitle.textContent = chat.title;
            messagesBox.innerHTML = '';

            (chat.messages || []).forEach((message) => {
                messagesBox.appendChild(renderMessage(message));
            });

            emptyState.classList.add('hidden');
            conversation.classList.remove('hidden');
            scrollToBottom();
            closeSidebar();
        } catch (error) {
            Zang.toast(error.message, 'error');
        }
    }

    /* ---------- Create Chat ---------- */
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
            Zang.toast('حداقل یک شناسه وارد کن', 'error');
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

    /* ---------- Join Chat ---------- */
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
            Zang.toast('به گفتگو وارد شدی', 'success');
        } catch (error) {
            Zang.toast(error.message, 'error');
        } finally {
            joinConfirm.disabled = false;
        }
    }

    /* ---------- Rename Chat ---------- */
    async function renameChat(chatId, currentTitle) {
        const title = window.prompt('عنوان جدید گفتگو:', currentTitle);
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
            if (item) {
                item.dataset.title = data.chat.title;
                item.querySelector('.chat-item-title').textContent = data.chat.title;
                item.querySelector('.chat-avatar').textContent = data.chat.title.charAt(0);
            }

            if (activeChatId === Number(chatId)) {
                conversationTitle.textContent = data.chat.title;
            }

            Zang.toast('عنوان تغییر کرد', 'success');
        } catch (error) {
            Zang.toast(error.message, 'error');
        }
    }

    /* ---------- Delete Chat ---------- */
    async function deleteChat(chatId) {
        if (!window.confirm('این گفتگو و همه پیام‌هایش حذف شود؟')) return;

        try {
            await Zang.api(`/chat/api/chats/${chatId}`, { method: 'DELETE' });

            const item = chatList.querySelector(`.chat-item[data-chat-id="${chatId}"]`);
            item?.remove();

            if (activeChatId === Number(chatId)) {
                activeChatId = null;
                conversation.classList.add('hidden');
                emptyState.classList.remove('hidden');
            }

            Zang.toast('گفتگو حذف شد', 'success');
        } catch (error) {
            Zang.toast(error.message, 'error');
        }
    }

    /* ---------- Send Message ---------- */
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
                body: JSON.stringify({ content })
            });

            appendMessage(data.message);
            messageInput.value = '';
            Zang.autoResize(messageInput);
        } catch (error) {
            Zang.toast(error.message, 'error');
        } finally {
            sending = false;
            sendBtn.disabled = false;
            messageInput.focus();
        }
    }

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
    createCodesInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') { event.preventDefault(); submitCreateChat(); }
    });

    joinChatBtn?.addEventListener('click', openJoinModal);
    emptyJoinChat?.addEventListener('click', openJoinModal);
    joinConfirm?.addEventListener('click', submitJoinChat);
    joinCodeInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') { event.preventDefault(); submitJoinChat(); }
    });

    composer?.addEventListener('submit', sendMessage);

    messageInput?.addEventListener('input', () => Zang.autoResize(messageInput));

    messageInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            composer.requestSubmit();
        }
    });

    searchInput?.addEventListener('input', () => {
        const term = searchInput.value.trim().toLowerCase();
        chatList.querySelectorAll('.chat-item').forEach((item) => {
            const title = item.dataset.title.toLowerCase();
            item.classList.toggle('hidden', term !== '' && !title.includes(term));
        });
    });

    /* ---------- Auto Open First Chat ---------- */
    const firstChat = chatList?.querySelector('.chat-item');
    if (firstChat) {
        loadChat(Number(firstChat.dataset.chatId));
    }
})();
