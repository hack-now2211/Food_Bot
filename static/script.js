// Initialize global variables
let context = {}; // Stores the conversation context
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-btn');
const chatMessages = document.getElementById('chat-messages');
const suggestionsDiv = document.getElementById('suggestions');
const orderSummaryDiv = document.getElementById('order-summary');

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Focus on input when page loads
    userInput.focus();
    
    // Setup speech recognition
    setupSpeechRecognition();
});

// Send message when send button is clicked
sendButton.addEventListener('click', function() {
    sendMessage();
});

// Send message when Enter key is pressed
userInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Main function to send user message
function sendMessage() {
    const message = userInput.value.trim();
    
    // Don't send empty messages
    if (message === '') return;
    
    // Add user message to chat
    addMessageToChat(message, 'user');
    
    // Clear input field
    userInput.value = '';
    
    // Show typing indicator
    addTypingIndicator();
    
    // Clear suggestions
    suggestionsDiv.innerHTML = '';
    
    // Send to backend
    sendApiRequest(message);
}

// Add a message to the chat UI
function addMessageToChat(message, sender, options = [], menu = [], orderSummary = null) {
    // Remove typing indicator if it exists
    removeTypingIndicator();
    
    // Create message element
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    // Add message content
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = message;
    messageDiv.appendChild(contentDiv);
    
    // Add to chat and scroll to bottom
    chatMessages.appendChild(messageDiv);
    
    // Add options if provided
    if (options && options.length > 0) {
        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'options';
        
        options.forEach(option => {
            const optionChip = document.createElement('div');
            optionChip.className = 'option-chip';
            optionChip.textContent = option;
            optionChip.addEventListener('click', function() {
                handleOptionClick(option);
            });
            optionsDiv.appendChild(optionChip);
        });
        
        messageDiv.appendChild(optionsDiv);
    }
    
    // Add menu if provided
    if (menu && menu.length > 0) {
        const menuDisplay = document.createElement('div');
        menuDisplay.className = 'menu-display';
        
        const menuHeader = document.createElement('h3');
        menuHeader.textContent = 'Menu Items';
        menuDisplay.appendChild(menuHeader);
        
        menu.forEach(item => {
            const menuItem = document.createElement('div');
            menuItem.className = 'menu-item';
            
            const itemName = document.createElement('span');
            itemName.textContent = item.name;
            
            const itemPrice = document.createElement('span');
            itemPrice.textContent = `₹${item.price}`;
            
            menuItem.appendChild(itemName);
            menuItem.appendChild(itemPrice);
            menuDisplay.appendChild(menuItem);
            
            // Add click to order functionality
            menuItem.addEventListener('click', function() {
                handleItemClick(item.name);
            });
        });
        
        messageDiv.appendChild(menuDisplay);
    }
    
    // Show order summary if provided
    if (orderSummary) {
        updateOrderSummaryDisplay(orderSummary);
    } else {
        // Hide order summary
        orderSummaryDiv.style.display = 'none';
    }
    
    // Scroll to the bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Handle option chip clicks
function handleOptionClick(option) {
    userInput.value = option;
    sendMessage();
}

// Handle menu item clicks
function handleItemClick(itemName) {
    userInput.value = `I'd like to order ${itemName}`;
    sendMessage();
}

// Add typing indicator
function addTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot';
    typingDiv.id = 'typing-indicator';
    
    const indicatorDiv = document.createElement('div');
    indicatorDiv.className = 'typing-indicator';
    
    for (let i = 0; i < 3; i++) {
        const dot = document.createElement('span');
        indicatorDiv.appendChild(dot);
    }
    
    typingDiv.appendChild(indicatorDiv);
    chatMessages.appendChild(typingDiv);
    
    // Scroll to the bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Remove typing indicator
function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Update order summary display
function updateOrderSummaryDisplay(orderSummary) {
    if (!orderSummary || !orderSummary.items || orderSummary.items.length === 0) {
        orderSummaryDiv.style.display = 'none';
        return;
    }
    
    // Clear existing content
    orderSummaryDiv.innerHTML = '';
    
    // Create header
    const header = document.createElement('h3');
    header.textContent = 'Your Order';
    orderSummaryDiv.appendChild(header);
    
    // Add each item
    orderSummary.items.forEach(item => {
        const orderItem = document.createElement('div');
        orderItem.className = 'order-item';
        
        const itemInfo = document.createElement('div');
        itemInfo.textContent = `${item.quantity} x ${item.item.charAt(0).toUpperCase() + item.item.slice(1)}`;
        
        const itemPrice = document.createElement('div');
        itemPrice.textContent = `₹${item.price * item.quantity}`;
        
        orderItem.appendChild(itemInfo);
        orderItem.appendChild(itemPrice);
        orderSummaryDiv.appendChild(orderItem);
    });
    
    // Add total
    const orderTotal = document.createElement('div');
    orderTotal.className = 'order-total';
    
    const totalLabel = document.createElement('div');
    totalLabel.textContent = 'Total:';
    
    const totalAmount = document.createElement('div');
    totalAmount.textContent = `₹${orderSummary.total}`;
    
    orderTotal.appendChild(totalLabel);
    orderTotal.appendChild(totalAmount);
    orderSummaryDiv.appendChild(orderTotal);
    
    // Show order summary
    orderSummaryDiv.style.display = 'block';
}

// Function to send API requests to the backend
function sendApiRequest(message) {
    return fetch('/api/process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            context: context
        }),
    })
    .then(response => response.json())
    .then(data => {
        handleResponse(data);
    })
    .catch(error => {
        console.error('Error:', error);
        removeTypingIndicator();
        addMessageToChat("Sorry, there was an error processing your request. Please try again.", 'bot');
    });
}

// Function to handle API responses
function handleResponse(data) {
    // Update context with the new state
    context = data.context;
    
    // Add bot message to chat
    addMessageToChat(data.message, 'bot', data.options, data.menu, data.order_summary);
}

// Setup Speech Recognition for voice input
function setupSpeechRecognition() {
    if ('webkitSpeechRecognition' in window) {
        const recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        
        const micButton = document.createElement('button');
        micButton.id = 'mic-btn';
        micButton.innerHTML = '<i class="fas fa-microphone"></i>';
        
        const inputContainer = document.querySelector('.input-container');
        inputContainer.appendChild(micButton);
        
        let isListening = false;
        
        micButton.addEventListener('click', function() {
            if (!isListening) {
                recognition.start();
                micButton.innerHTML = '<i class="fas fa-spinner fa-pulse"></i>';
                micButton.classList.add('active');
                isListening = true;
            } else {
                recognition.stop();
                micButton.innerHTML = '<i class="fas fa-microphone"></i>';
                micButton.classList.remove('active');
                isListening = false;
            }
        });
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            userInput.value = transcript;
            micButton.innerHTML = '<i class="fas fa-microphone"></i>';
            micButton.classList.remove('active');
            isListening = false;
            
            // Auto-send the message after voice input
            setTimeout(() => sendMessage(), 300);
        };
        
        recognition.onend = function() {
            micButton.innerHTML = '<i class="fas fa-microphone"></i>';
            micButton.classList.remove('active');
            isListening = false;
        };
        
        recognition.onerror = function(event) {
            console.error('Speech recognition error', event.error);
            micButton.innerHTML = '<i class="fas fa-microphone"></i>';
            micButton.classList.remove('active');
            isListening = false;
        };
    }
}

// Enhanced NLP order processing for client-side item recognition
// This function can provide immediate feedback while waiting for server response
function simulateOrderProcessing(message, restaurant) {
    const results = [];
    const lowerMessage = message.toLowerCase();
    
    // Define menu items based on restaurant
    let menuItems = {};
    if (restaurant === 'tasty bites') {
        menuItems = {
            'burger': 120,
            'pizza': 200,
            'french fries': 80,
            'fries': 80,
            'cheese burger': 150,
            'chicken wrap': 160,
            'chocolate shake': 90,
            'mango mojito': 70
        };
    } else if (restaurant === 'desi delight') {
        menuItems = {
            'chicken biryani': 180,
            'paneer tikka': 160,
            'butter naan': 40,
            'dal makhani': 120,
            'jeera rice': 90,
            'paneer butter masala': 150,
            'roti': 20
        };
    }
    
    // Extract quantities and items from user message
    const words = lowerMessage.split(/\s+/);
    let i = 0;
    
    while (i < words.length) {
        let quantity = 1;
        let itemFound = null;
        
        // Check if current word is a number (potential quantity)
        if (!isNaN(words[i]) && parseInt(words[i]) > 0) {
            quantity = parseInt(words[i]);
            i++;
        }
        
        // Try to find matching menu items (could be single or multi-word)
        for (let len = 3; len > 0; len--) {
            if (i + len <= words.length) {
                const potentialItem = words.slice(i, i + len).join(' ');
                if (menuItems.hasOwnProperty(potentialItem)) {
                    itemFound = potentialItem;
                    i += len;
                    break;
                }
            }
        }
        
        // Check single word items with basic synonym handling
        if (!itemFound && menuItems.hasOwnProperty(words[i])) {
            itemFound = words[i];
            i++;
        } else if (!itemFound) {
            // Handle some common synonyms
            const synonyms = {
                'soda': 'chocolate shake',
                'cola': 'chocolate shake',
                'chips': 'fries',
                'naan': 'butter naan',
                'paneer': 'paneer tikka',
                'biryani': 'chicken biryani',
                'mojito': 'mango mojito',
            };
            
            if (synonyms.hasOwnProperty(words[i]) && menuItems.hasOwnProperty(synonyms[words[i]])) {
                itemFound = synonyms[words[i]];
                i++;
            } else {
                i++;
            }
        }
        
        if (itemFound) {
            results.push({
                item: itemFound.charAt(0).toUpperCase() + itemFound.slice(1),
                price: menuItems[itemFound],
                quantity: quantity
            });
        }
    }
    
    return results;
}

// Add common food suggestions
function addCommonSuggestions() {
    const suggestions = [
        "I want to order food",
        "Show me fast food options",
        "I'd like some Indian food",
        "Order a pizza",
        "I want a burger"
    ];
    
    suggestionsDiv.innerHTML = '';
    
    suggestions.forEach(suggestion => {
        const chip = document.createElement('div');
        chip.className = 'suggestion-chip';
        chip.textContent = suggestion;
        chip.addEventListener('click', function() {
            userInput.value = suggestion;
            sendMessage();
        });
        suggestionsDiv.appendChild(chip);
    });
}

// Show initial suggestions when page loads
addCommonSuggestions();