class ChatApp {
    constructor() {
        this.apiUrl = 'http://localhost:8000';
        this.sessionId = this.generateSessionId();
        this.isTyping = false;
        
        this.elements = {
            chatMessages: document.getElementById('chatMessages'),
            chatForm: document.getElementById('chatForm'),
            messageInput: document.getElementById('messageInput'),
            sendButton: document.getElementById('sendButton'),
            typingIndicator: document.getElementById('typingIndicator'),
            status: document.getElementById('status'),
            messageCount: document.getElementById('messageCount')
        };
        
        this.init();
    }
    
    init() {
        this.elements.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.elements.messageInput.addEventListener('input', (e) => this.updateCharCount(e));
        this.elements.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSubmit(e);
            }
        });
        
        // Test API connection
        this.testConnection();
        
        // Focus input
        this.elements.messageInput.focus();
    }
    
    generateSessionId() {
        return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }
    
    async testConnection() {
        try {
            const response = await fetch(`${this.apiUrl}/health`);
            if (response.ok) {
                this.updateStatus('connected');
            } else {
                this.updateStatus('error');
            }
        } catch (error) {
            console.error('Connection test failed:', error);
            this.updateStatus('disconnected');
        }
    }
    
    updateStatus(status) {
        const statusElement = this.elements.status;
        statusElement.className = `status-indicator ${status}`;
        
        const statusText = statusElement.querySelector('.status-text');
        switch(status) {
            case 'connected':
                statusText.textContent = 'Connected';
                break;
            case 'disconnected':
                statusText.textContent = 'Disconnected';
                break;
            case 'error':
                statusText.textContent = 'Error';
                break;
        }
    }
    
    updateCharCount(e) {
        const count = e.target.value.length;
        this.elements.messageCount.textContent = count;
        
        if (count > 950) {
            this.elements.messageCount.style.color = '#e74c3c';
        } else if (count > 800) {
            this.elements.messageCount.style.color = '#f39c12';
        } else {
            this.elements.messageCount.style.color = '#666';
        }
    }
    
    async handleSubmit(e) {
        e.preventDefault();
        
        const message = this.elements.messageInput.value.trim();
        if (!message || this.isTyping) return;
        
        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input and disable form
        this.elements.messageInput.value = '';
        this.updateCharCount({ target: { value: '' } });
        this.setTyping(true);
        
        try {
            const response = await this.sendMessage(message);
            this.addMessage(response.response, 'bot', response.cards, response.suggested_actions);
        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessage('Sorry, I encountered an error. Please try again.', 'bot', [], [], true);
            this.updateStatus('error');
        } finally {
            this.setTyping(false);
        }
    }
    
    async sendMessage(message) {
        const response = await fetch(`${this.apiUrl}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: this.sessionId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    setTyping(typing) {
        this.isTyping = typing;
        this.elements.sendButton.disabled = typing;
        this.elements.messageInput.disabled = typing;
        
        if (typing) {
            this.elements.typingIndicator.style.display = 'block';
            this.scrollToBottom();
        } else {
            this.elements.typingIndicator.style.display = 'none';
            this.elements.messageInput.focus();
        }
    }
    
    addMessage(text, sender, cards = [], suggestedActions = [], isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = sender === 'user' ? '👤' : '🤖';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const messageText = document.createElement('div');
        messageText.className = `message-text ${isError ? 'error-message' : ''}`;
        
        // Format message text (convert markdown-style formatting)
        let formattedText = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
        
        messageText.innerHTML = formattedText;
        
        content.appendChild(messageText);
        
        // Add cards if present
        if (cards && cards.length > 0) {
            const cardGrid = this.createCardGrid(cards);
            content.appendChild(cardGrid);
        }
        
        // Add suggested actions if present
        if (suggestedActions && suggestedActions.length > 0) {
            const actionsDiv = this.createSuggestedActions(suggestedActions);
            content.appendChild(actionsDiv);
        }
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        // Insert before typing indicator
        this.elements.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    createCardGrid(cards) {
        const cardGrid = document.createElement('div');
        cardGrid.className = 'card-grid';
        
        cards.forEach(card => {
            const cardItem = document.createElement('div');
            cardItem.className = 'card-item';
            
            cardItem.innerHTML = `
                <div class="card-name">${card.name}</div>
                <div class="card-details">
                    <div><strong>Set:</strong> ${card.set_name}</div>
                    <div><strong>Condition:</strong> ${card.condition}</div>
                    <div><strong>Rarity:</strong> ${card.rarity}</div>
                    <div><strong>In Stock:</strong> ${card.quantity}</div>
                    ${card.description ? `<div style="margin-top: 8px; font-style: italic;">${card.description}</div>` : ''}
                </div>
                <div class="card-price">$${card.price_cad.toFixed(2)} CAD</div>
            `;
            
            cardGrid.appendChild(cardItem);
        });
        
        return cardGrid;
    }
    
    createSuggestedActions(actions) {
        const actionsContainer = document.createElement('div');
        actionsContainer.className = 'suggested-actions';
        
        actions.forEach(action => {
            const button = document.createElement('button');
            button.className = 'action-button';
            button.textContent = action.action;
            button.title = action.description;
            
            button.addEventListener('click', () => {
                if (action.action === 'Contact support') {
                    this.addMessage('How can I get in touch with your support team?', 'user');
                    this.handleSubmit({ preventDefault: () => {} });
                } else if (action.action.includes('Search')) {
                    this.elements.messageInput.value = 'Show me more cards';
                    this.elements.messageInput.focus();
                }
            });
            
            actionsContainer.appendChild(button);
        });
        
        return actionsContainer;
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
        }, 100);
    }
}

// Initialize the chat app when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});