/**
 * chatbot.js - Interactive AI Chatbot Controller
 * Smart Chatbot for Restaurant Order Automation
 */

document.addEventListener('DOMContentLoaded', () => {
    initChatbot();
});

function initChatbot() {
    const chatbotFab = document.getElementById('chatbotFab');
    const chatbotWindow = document.getElementById('chatbotWindow');
    const chatbotClose = document.getElementById('chatbotClose');
    const chatbotClear = document.getElementById('chatbotClearHistory');
    const chatbotForm = document.getElementById('chatbotForm');
    const chatbotInput = document.getElementById('chatbotInput');
    const quickRepliesContainer = document.getElementById('chatbotQuickReplies');

    // Toggle Chat Window
    if (chatbotFab && chatbotWindow) {
        chatbotFab.addEventListener('click', () => {
            const isHidden = chatbotWindow.classList.contains('d-none');
            chatbotWindow.classList.toggle('d-none', !isHidden);
            if (isHidden && chatbotInput) {
                chatbotInput.focus();
            }
        });
    }

    if (chatbotClose && chatbotWindow) {
        chatbotClose.addEventListener('click', () => {
            chatbotWindow.classList.add('d-none');
        });
    }

    if (chatbotClear) {
        chatbotClear.addEventListener('click', () => {
            const body = document.getElementById('chatbotBody');
            if (body) {
                body.innerHTML = `
                    <div class="chat-message bot">
                        <div class="msg-bubble">
                            Chat history cleared! 🧹 How can I help you with your order?
                        </div>
                        <small class="msg-time">Just now</small>
                    </div>
                `;
            }
        });
    }

    // Submit user message
    if (chatbotForm && chatbotInput) {
        chatbotForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const text = chatbotInput.value.trim();
            if (!text) return;
            chatbotInput.value = '';
            sendMessageToBot(text);
        });
    }

    // Delegated click for quick reply chips
    if (quickRepliesContainer) {
        quickRepliesContainer.addEventListener('click', (e) => {
            const chip = e.target.closest('.quick-chip');
            if (chip) {
                const query = chip.getAttribute('data-query') || chip.textContent.trim();
                sendMessageToBot(query);
            }
        });
    }
}

// Global helper to open chatbot with pre-filled message from page buttons
function openChatbotWithMessage(msg) {
    const chatbotWindow = document.getElementById('chatbotWindow');
    if (chatbotWindow) {
        chatbotWindow.classList.remove('d-none');
    }
    sendMessageToBot(msg);
}

function sendMessageToBot(messageText) {
    const body = document.getElementById('chatbotBody');
    if (!body) return;

    // 1. Append User Message Bubble
    appendMessageBubble('user', messageText);

    // 2. Append Typing Indicator
    const typingId = 'typing-' + Date.now();
    const typingHtml = `
        <div class="chat-message bot" id="${typingId}">
            <div class="msg-bubble text-muted small py-2 d-flex align-items-center gap-2">
                <span class="spinner-grow spinner-grow-sm text-primary" role="status"></span>
                <span>Thinking...</span>
            </div>
        </div>
    `;
    body.insertAdjacentHTML('beforeend', typingHtml);
    body.scrollTop = body.scrollHeight;

    // 3. Post to Flask API Endpoint
    fetch('/api/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageText })
    })
    .then(res => res.json())
    .then(data => {
        // Remove typing indicator
        const typingEl = document.getElementById(typingId);
        if (typingEl) typingEl.remove();

        if (data.success) {
            // Render Bot Message
            appendMessageBubble('bot', data.reply, data);

            // Sync Cart UI if cart was modified
            if (data.cart && typeof renderCartUI === 'function') {
                renderCartUI(data.cart);
            }

            // Update Quick Replies Chips
            if (data.quick_replies && data.quick_replies.length > 0) {
                renderQuickReplies(data.quick_replies);
            }
        } else {
            appendMessageBubble('bot', "Sorry, I encountered an issue processing your request. Please try again.");
        }
    })
    .catch(err => {
        console.error("Chatbot error:", err);
        const typingEl = document.getElementById(typingId);
        if (typingEl) typingEl.remove();
        appendMessageBubble('bot', "Network error connecting to AI server. Please check your connection.");
    });
}

function appendMessageBubble(sender, text, meta = null) {
    const body = document.getElementById('chatbotBody');
    if (!body) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const formattedText = formatBotText(text);

    let extraHtml = '';

    // If bot returned dish item cards
    if (meta && meta.items && meta.items.length > 0) {
        extraHtml += `<div class="mt-2 d-flex flex-column gap-2">`;
        meta.items.slice(0, 3).forEach(it => {
            extraHtml += `
                <div class="card p-2 bg-light border-0 rounded-3 shadow-none small">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong class="text-dark">${it.name}</strong>
                            <div class="text-primary fw-bold">₹${Math.round(it.price)}</div>
                        </div>
                        <button class="btn btn-xs btn-primary rounded-pill px-2 py-1 small" onclick="addToCart(${it.id}, 1)">
                            + Add
                        </button>
                    </div>
                </div>
            `;
        });
        extraHtml += `</div>`;
    }

    // If bot prompted checkout
    if (meta && meta.action === 'confirm_checkout') {
        extraHtml += `
            <div class="mt-3">
                <button class="btn btn-sm btn-primary rounded-pill w-100 fw-bold" onclick="openCheckoutFromBot()">
                    <i class="bi bi-bag-check me-1"></i> Proceed to Checkout
                </button>
            </div>
        `;
    }

    const messageHtml = `
        <div class="chat-message ${sender}">
            <div class="msg-bubble">
                ${formattedText}
                ${extraHtml}
            </div>
            <small class="msg-time">${timeStr}</small>
        </div>
    `;

    body.insertAdjacentHTML('beforeend', messageHtml);
    body.scrollTop = body.scrollHeight;
}

function renderQuickReplies(replies) {
    const container = document.getElementById('chatbotQuickReplies');
    if (!container) return;

    container.innerHTML = replies.map(r => `
        <span class="badge quick-chip" data-query="${r}">${r}</span>
    `).join('');
}

function openCheckoutFromBot() {
    const modalEl = document.getElementById('checkoutModal');
    if (modalEl) {
        const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
        bsModal.show();
    }
}

function formatBotText(raw) {
    if (!raw) return '';
    // Format bold **text** -> <strong>text</strong>
    let text = raw.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Format italic _text_ or *text* -> <em>text</em>
    text = text.replace(/_([^_]+)_/g, '<em>$1</em>');
    return text;
}
