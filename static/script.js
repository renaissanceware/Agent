document.addEventListener('DOMContentLoaded', function () {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    const chatContainer = document.getElementById('chatContainer');
    const newChatBtn = document.getElementById('newChatBtn');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatMessages = document.getElementById('chatMessages');

    function showChat() {
        chatContainer.style.display = 'flex';
        chatInput.focus();
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
            })
            .catch(error => {
                console.error('API request error:', error);
                typingIndicator.remove();
                addMessage('Sorry, an error occurred while processing your request. Please try again later.', 'assistant');
            });
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

    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('active');
    });

    newChatBtn.addEventListener('click', () => {
        chatMessages.innerHTML = '';
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