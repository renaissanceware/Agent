document.addEventListener('DOMContentLoaded', function () {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    const chatContainer = document.getElementById('chatContainer');
    const newChatBtn = document.getElementById('newChatBtn');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatMessages = document.getElementById('chatMessages');
    const chatHistory = document.querySelector('.chat-history');
    const searchInput = document.querySelector('.sidebar-search input');
    
    // 加载对话历史
    loadConversationHistory();
    
    // 搜索对话
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const conversations = document.querySelectorAll('.chat-history-item');
        conversations.forEach(conv => {
            const text = conv.textContent.toLowerCase();
            conv.style.display = text.includes(searchTerm) ? 'block' : 'none';
        });
    });

    function showChat() {
        chatContainer.style.display = 'flex';
        chatInput.focus();
    }

    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender} ${sender === 'user' ? 'reverse' : ''}`;

        const avatarClass = sender === 'user' ? 'user-message-avatar' : 'assistant-message-avatar';

        messageDiv.innerHTML = `
        <div class="message-avatar ${avatarClass}"></div>
        <div class="message-content">
            <div class="message-body">${text}</div>
        </div>
    `;

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        return messageDiv;
    }

    function addFeedbackButtons(messageElement, conversationId) {
        if (!messageElement.classList.contains('assistant')) return;

        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'feedback-buttons';
        feedbackDiv.innerHTML = `
        <span>Response Satisfaction:</span>
        <div class="star-rating">
            <span class="star" data-rating="5" data-conversation-id="${conversationId}"></span>
            <span class="star" data-rating="4" data-conversation-id="${conversationId}"></span>
            <span class="star" data-rating="3" data-conversation-id="${conversationId}"></span>
            <span class="star" data-rating="2" data-conversation-id="${conversationId}"></span>
            <span class="star" data-rating="1" data-conversation-id="${conversationId}"></span>
        </div>
    `;

        messageElement.appendChild(feedbackDiv);

        const stars = feedbackDiv.querySelectorAll('.star');
        stars.forEach(star => {
            star.addEventListener('click', function () {
                const rating = parseInt(this.dataset.rating);
                const conversationId = this.dataset.conversationId;
                submitFeedback(rating, this, conversationId);
            });
        });
    }

    function submitFeedback(rating, starElement, conversationId) {
        const stars = starElement.parentElement.querySelectorAll('.star');
        stars.forEach(star => {
            star.style.pointerEvents = 'none';
        });

        const starRating = starElement.parentElement;
        starRating.classList.add('selected');

        const selectedRating = parseInt(starElement.dataset.rating);
        stars.forEach(star => {
            const starRatingValue = parseInt(star.dataset.rating);
            if (starRatingValue <= selectedRating) {
                star.classList.add('filled');
            } else {
                star.classList.add('empty');
            }
        });

        fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                rating: rating,
                session_id: conversationId
            })
        })
            .then(response => response.json())
            .then(data => {
                console.log('Feedback submitted:', data);
            })
            .catch(error => {
                console.error('Error submitting feedback:', error);
            });
    }

    function showRecommendedProducts(products) {
        const productsContainer = document.createElement('div');
        productsContainer.className = 'products-container';

        products.forEach(product => {
            const productCard = document.createElement('div');
            productCard.className = 'product-card';

            productCard.innerHTML = `
                        <div class="product-image">
                            <img src="${product.image_url || ''}" alt="${product.name}">
                        </div>
                        <div class="product-info">
                            <h3 class="product-name">${product.name}</h3>
                            <p class="product-description">${product.description}</p>
                            <div class="product-price">${product.price}</div>
                        </div>
                    `;

            productsContainer.appendChild(productCard);
        });

        chatMessages.appendChild(productsContainer);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function getAllProducts() {
        fetch('/api/products')
            .then(response => response.json())
            .then(products => {
                showRecommendedProducts(products);
            })
            .catch(error => {
                console.error('Error getting products:', error);
                addMessage('Sorry, failed to retrieve product information. Please try again later.', 'assistant');
            });
    }

    function loadConversationHistory() {
        // 从服务器获取对话历史
        fetch('/api/conversations')
            .then(response => response.json())
            .then(conversations => {
                const chatHistory = document.querySelector('.chat-history');
                chatHistory.innerHTML = '';
                
                conversations.forEach(conv => {
                    const convItem = document.createElement('div');
                    convItem.className = 'chat-history-item';
                    convItem.dataset.conversationId = conv.conversation_id;
                    
                    // 格式化时间
                    const date = new Date(conv.created_at);
                    const formattedDate = date.toLocaleString();
                    
                    convItem.innerHTML = `
                        <div class="chat-history-item-content">
                            <div class="chat-history-item-title">
                                ${conv.last_message.substring(0, 30)}${conv.last_message.length > 30 ? '...' : ''}
                            </div>
                            <div class="chat-history-item-meta">
                                <span class="chat-history-item-date">${formattedDate}</span>
                            </div>
                        </div>
                        <div class="chat-history-item-actions">
                            <button class="delete-conv-btn" data-conversation-id="${conv.conversation_id}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    `;
                    
                    chatHistory.appendChild(convItem);
                    
                    // 添加点击事件，加载对话详情
                    convItem.addEventListener('click', function(e) {
                        if (!e.target.closest('.delete-conv-btn')) {
                            const convId = this.dataset.conversationId;
                            loadConversation(convId);
                        }
                    });
                    
                    // 添加删除事件
                    const deleteBtn = convItem.querySelector('.delete-conv-btn');
                    deleteBtn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        const convId = this.dataset.conversationId;
                        if (confirm('Are you sure you want to delete this conversation?')) {
                            //deleteConversation(convId);
                        }
                    });
                });
            })
            .catch(error => {
                console.error('Error loading conversation history:', error);
            });
    }

    function loadConversation(conversationId) {
        // 从服务器获取对话详情
        fetch(`/api/conversations/${conversationId}`)
            .then(response => response.json())
            .then(messages => {
                chatMessages.innerHTML = '';
                
                messages.forEach(msg => {
                    addMessage(msg.content, msg.role);
                });
            })
            .catch(error => {
                console.error('Error loading conversation:', error);
            });
    }

    function deleteConversation(conversationId) {
        // 从服务器删除对话
        fetch(`/api/conversations/${conversationId}`, {
            method: 'DELETE'
        })
            .then(response => response.json())
            .then(data => {
                console.log('Conversation deleted:', data);
                // 重新加载对话历史
                loadConversationHistory();
                // 清空当前聊天窗口
                chatMessages.innerHTML = '';
                addMessage('How can I help you today?', 'assistant');
            })
            .catch(error => {
                console.error('Error deleting conversation:', error);
            });
    }

    function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        addMessage(message, 'user');
        chatInput.value = '';

        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'typing-indicator';
        typingIndicator.innerHTML = `
                <div class="message-avatar assistant-message-avatar"></div>
                <div class="message-content">
                    <div class="typing-dots">
                        <div class="dot"></div>
                        <div class="dot"></div>
                        <div class="dot"></div>
                    </div>
                </div>
            `;
        chatMessages.appendChild(typingIndicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question: message })
        })
            .then(response => response.json())
            .then(data => {
                typingIndicator.remove();

                const messageElement = addMessage(data.reply, 'assistant');

                addFeedbackButtons(messageElement, data.conversation_id);

                if (data.products && data.products.length > 0) {
                    showRecommendedProducts(data.products);
                }
                
                // 重新加载对话历史
                loadConversationHistory();
            })
            .catch(error => {
                console.error('API request error:', error);
                typingIndicator.remove();
                addMessage('Sorry, an error occurred while processing your request. Please try again later.', 'assistant');
            });
    }

    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('active');
    });

    newChatBtn.addEventListener('click', () => {
        // 创建新对话
        chatMessages.innerHTML = '';
        // 重置会话
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question: 'Hello' })
        })
        .then(response => response.json())
        .then(data => {
            chatMessages.innerHTML = '';
            addMessage('How can I help you today?', 'assistant');
            // 重新加载对话历史
            loadConversationHistory();
        });
    });

    addMessage('How can I help you today?', 'assistant');

    sendBtn.addEventListener('click', sendMessage);

    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});
