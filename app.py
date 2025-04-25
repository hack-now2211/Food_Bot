# app.py - Enhanced Flask backend for the NLP Food Ordering System
import re
import nltk
import difflib
import json
import os
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory
from nltk.corpus import wordnet as wn, stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from textblob import TextBlob

# Try to import enhanced modules
try:
    from fuzzywuzzy import fuzz
    fuzzywuzzy_available = True
except ImportError:
    fuzzywuzzy_available = False
    print("fuzzywuzzy not available. Using basic string matching.")

import spacy
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

try:
    import spacy
    spacy_available = True
    nlp = spacy.load("en_core_web_sm")
except ImportError:
    spacy_available = False
    nlp = None
    print("spaCy not available. Using NLTK for NLP processing.")

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')

# Download required NLTK data
try:
    nltk.data.find('corpora/wordnet')
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/omw-1.4')
    nltk.data.find('taggers/averaged_perceptron_tagger')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('wordnet')
    nltk.download('punkt')
    nltk.download('omw-1.4')
    nltk.download('averaged_perceptron_tagger')
    nltk.download('stopwords')

lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

# Enhanced synonym map
synonyms_map = {
    "soda": "coke",
    "cola": "coke",
    "pepsi": "coke",
    "chips": "fries",
    "french fries": "fries",
    "icecream": "ice cream",
    "naan": "butter naan",
    "bread": "garlic bread",
    "water": "mineral water",
    "coffee": "cappuccino",
    "paneer": "paneer tikka",
    "chicken": "chicken biryani",
    "rice": "jeera rice",
    "wrap": "chicken wrap",
    "burger": "cheese burger",
    "mojito": "mango mojito",
    "juice": "orange juice",
    "shake": "chocolate shake"
}

# Load menu data from file
def load_menu_from_file(filename):
    menus = {}
    try:
        with open(filename, 'r') as f:
            content = f.read().strip().split('\n\n')
            for block in content:
                lines = block.strip().split('\n')
                if not lines:
                    continue
                restaurant = lines[0].strip().lower()
                menu_items = {}
                for item in lines[1:]:
                    if ' - ' in item:
                        name, price = item.split(' - ')
                        menu_items[name.lower().strip()] = int(price.strip())
                menus[restaurant] = menu_items
                
        logger.info(f"Successfully loaded menus from {filename}")
        return menus
    except FileNotFoundError:
        logger.warning(f"Menu file '{filename}' not found. Using sample menus.")
        return None
    except Exception as e:
        logger.error(f"Error loading menu: {str(e)}")
        return None

# Try to load menus from file
MENUS = load_menu_from_file('menus.txt') 

def correct_spelling(text):
    """Correct spelling using TextBlob"""
    try:
        blob = TextBlob(text)
        return str(blob.correct())
    except:
        logger.warning("TextBlob spelling correction failed, using original text")
        return text

def normalize_tokens(text):
    """Normalize and clean text tokens"""
    if spacy_available:
        doc = nlp(text.lower())
        return [token.lemma_ for token in doc if not token.is_stop and token.is_alpha]
    else:
        tokens = word_tokenize(text.lower())
        return [lemmatizer.lemmatize(word) for word in tokens 
                if word.isalnum() and word not in stop_words]

# def find_best_match(user_word, menu_items):
#     """Find best match for user word in menu items"""
#     # 1. Exact match
#     if user_word in menu_items:
#         return user_word
    
#     # 2. Check synonyms
#     if user_word in synonyms_map and synonyms_map[user_word] in menu_items:
#         return synonyms_map[user_word]
    
#     # 3. Fuzzy matching with fuzzywuzzy if available
#     if fuzzywuzzy_available:
#         best_match = None
#         best_score = 0
        
#         for item in menu_items:
#             # Check if user word is a substring
#             if user_word in item:
#                 score = 85
#             else:
#                 score = fuzz.ratio(user_word, item)
            
#             if score > best_score and score >= 70:
#                 best_score = score
#                 best_match = item
                
#         if best_match:
#             return best_match
    
#     # 4. Difflib fallback
#     close_matches = difflib.get_close_matches(user_word, menu_items, n=1, cutoff=0.7)
#     if close_matches:
#         return close_matches[0]
    
#     # 5. Word part matching for multi-word items
#     user_word_parts = user_word.split()
#     for item in menu_items:
#         item_parts = item.split()
#         # Check if all parts are in the item
#         if all(part in item_parts for part in user_word_parts):
#             return item
#         # Check if item is a substring
#         if user_word in item:
#             return item
    
#     return None

def resolve_synonym(word):
    """Get synonym for word if exists"""
    return synonyms_map.get(word, word)

def extract_food_entities(text):
    """Extract food entities and quantities from text"""
    quantities = {}
    food_entities = []
    
    # Convert words to numbers
    text = text.lower().replace('one', '1').replace('two', '2').replace('three', '3').replace('four', '4').replace('five', '5')
    
    # Handle patterns like "2 roti" and "1 mineral water" in same request
    # Match patterns like "X item" where X is a number
    quantity_item_pattern = re.compile(r'(\d+)\s+([a-zA-Z\s]+?)(?:,|\s+and|\s+&|\s*$)')
    matches = quantity_item_pattern.findall(text.lower())
    
    for quantity, item in matches:
        item = item.strip()
        quantities[item] = int(quantity)
        food_entities.append(item)
    
    # If no matches found with regex pattern, use NLP-based extraction
    if not food_entities:
        if spacy_available:
            doc = nlp(text)
            
            # Extract quantities with associated entities
            for i, token in enumerate(doc):
                if token.like_num and i + 1 < len(doc):
                    # Find the noun phrase following the number
                    j = i + 1
                    while j < len(doc) and (doc[j].pos_ in ["NOUN", "ADJ"] or doc[j].text in ["of", "and"]):
                        j += 1
                    
                    if j > i + 1:
                        potential_food = " ".join([t.text.lower() for t in doc[i+1:j]])
                        quantities[potential_food] = int(token.text)
                        food_entities.append(potential_food)
            
            # Extract noun chunks as potential food items if no quantities found
            if not food_entities:
                for chunk in doc.noun_chunks:
                    chunk_text = chunk.text.lower()
                    # Skip very short chunks or those containing stop words only
                    if len(chunk_text) > 2 and not all(word in stop_words for word in chunk_text.split()):
                        food_entities.append(chunk_text)
                        # Default quantity is 1
                        if chunk_text not in quantities:
                            quantities[chunk_text] = 1
        else:
            # Fallback to basic tokenization
            tokens = word_tokenize(text.lower())
            
            for i, token in enumerate(tokens):
                if token.isdigit() and i + 1 < len(tokens):
                    # Try to find multi-word food items
                    j = i + 1
                    while j < len(tokens) and tokens[j] not in [',', 'and', '&'] and not tokens[j].isdigit():
                        j += 1
                    
                    if j > i + 1:
                        potential_food = " ".join(tokens[i+1:j])
                        quantities[potential_food] = int(token)
                        food_entities.append(potential_food)
    
    logger.info(f"Extracted food entities: {food_entities}")
    logger.info(f"Extracted quantities: {quantities}")
    
    return food_entities, quantities

def process_order_request(menu, user_input):
    """Process order request and extract items"""
    corrected = correct_spelling(user_input)
    food_entities, quantities = extract_food_entities(corrected)
    
    results = []
    processed_entities = set()
    
    # Process each extracted food entity
    for entity in food_entities:
        if entity in processed_entities:
            continue
        
        # Get quantity if available, default to 1
        quantity = quantities.get(entity, 1)
        
        # Try to find a match in menu
        resolved_entity = resolve_synonym(entity)
        match = find_best_match(resolved_entity, menu.keys())
        
        if match:
            results.append({
                "item": match,
                "price": menu[match],
                "quantity": quantity
            })
            processed_entities.add(entity)
            continue
        
        # If no match found, try to check individual words
        # This is useful for cases like "chicken biryani" where both words might be important
        words = entity.split()
        if len(words) > 1:
            for word in words:
                if word not in stop_words and word not in processed_entities:
                    resolved_word = resolve_synonym(word)
                    word_match = find_best_match(resolved_word, menu.keys())
                    
                    if word_match:
                        results.append({
                            "item": word_match,
                            "price": menu[word_match],
                            "quantity": quantity
                        })
                        processed_entities.add(word)
    
    logger.info(f"Processed order items: {results}")
    return results

def find_best_match(user_word, menu_items):
    """Find best match for user word in menu items"""
    # 1. Exact match
    if user_word in menu_items:
        return user_word
    
    # 2. Check synonyms
    if user_word in synonyms_map and synonyms_map[user_word] in menu_items:
        return synonyms_map[user_word]
    
    # 3. Fuzzy matching with fuzzywuzzy if available
    if fuzzywuzzy_available:
        best_match = None
        best_score = 0
        
        for item in menu_items:
            # Check if user word is a substring
            if user_word in item:
                score = 85
            else:
                score = fuzz.ratio(user_word, item)
            
            if score > best_score and score >= 75:  # Increased threshold from 70 to 75 for more precision
                best_score = score
                best_match = item
                
        if best_match:
            return best_match
    
    # 4. Difflib fallback
    close_matches = difflib.get_close_matches(user_word, menu_items, n=1, cutoff=0.75)  # Increased cutoff from 0.7 to 0.75
    if close_matches:
        return close_matches[0]
    
    # 5. Word part matching for multi-word items
    user_word_parts = user_word.split()
    for item in menu_items:
        item_parts = item.split()
        # Check if all parts are in the item
        if all(part in item_parts for part in user_word_parts):
            return item
        # Check if item is a substring
        if user_word in item:
            return item
    
    return None

def get_food_type(user_input):
    """Determine food type based on input text"""
    tokens = normalize_tokens(user_input)
    text_set = set(tokens)
    
    fast_keywords = {"burger", "pizza", "fries", "wrap", "snack", "sandwich", 
                    "mojito", "fast", "quick", "shake", "coke", "cola"}
    meal_keywords = {"biryani", "roti", "paneer", "dal", "naan", "curry", 
                    "rice", "dinner", "lunch", "meal", "platter", "thali"}
    
    fast_match = len(fast_keywords & text_set)
    meal_match = len(meal_keywords & text_set)
    
    if fast_match > meal_match:
        return "fast food"
    elif meal_match > fast_match:
        return "meals"
    else:
        # Check for restaurant names as fallback
        if any(rest in user_input.lower() for rest in ["tasty", "bites"]):
            return "fast food"
        elif any(rest in user_input.lower() for rest in ["desi", "delight"]):
            return "meals"
        return "general"

def get_restaurant_by_food_type(food_type, menus):
    """Get restaurants that match the food type"""
    if food_type == "fast food":
        return [r for r in menus if "tasty bites" in r or "fast" in r]
    elif food_type == "meals":
        return [r for r in menus if "desi delight" in r or "meal" in r]
    else:
        return list(menus.keys())

# API routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/api/process', methods=['POST'])
def process_message():
    try:
        data = request.json
        user_message = data.get('message', '')
        context = data.get('context', {})
        
        logger.info(f"Processing message: '{user_message}' with context: {context}")
        
        # Get current conversation state
        state = context.get('state', 'welcome')
        restaurant = context.get('restaurant', '')
        order = context.get('order', [])
        menus = MENUS
        
        response = {
            'message': '',
            'context': {
                'state': state,
                'restaurant': restaurant,
                'order': order
            },
            'options': [],
            'menu': [],
            'order_summary': None
        }
        
        # State machine for conversation flow
        if state == 'welcome':
            food_type = get_food_type(user_message)
            options = get_restaurant_by_food_type(food_type, menus)
            
            response['message'] = f"I found these restaurants for {food_type} cuisine. Which one would you like to order from?"
            response['options'] = [r.title() for r in options]
            response['context']['state'] = 'select_restaurant'
            
        elif state == 'select_restaurant':
            # Find best restaurant match
            selected = user_message.lower().strip()
            matched_restaurant = None
            
            # Try exact match
            for rest in menus:
                if selected in rest or rest in selected:
                    matched_restaurant = rest
                    break
            
            # Try fuzzy match
            if not matched_restaurant and fuzzywuzzy_available:
                for rest in menus:
                    if fuzz.ratio(selected, rest) > 70:
                        matched_restaurant = rest
                        break
            
            if matched_restaurant:
                restaurant = matched_restaurant
                response['context']['restaurant'] = restaurant
                response['context']['state'] = 'ordering'
                response['message'] = f"Great choice! Here's the menu from {restaurant.title()}. What would you like to order?"
                response['menu'] = [{"name": item.title(), "price": price} for item, price in menus[restaurant].items()]
            else:
                response['message'] = "I don't recognize that restaurant. Please select one from the list."
                options = list(menus.keys())
                response['options'] = [r.title() for r in options]
                
        elif state == 'ordering':
            if any(word in user_message.lower() for word in ['done', 'finished', 'complete', 'checkout']):
                if order:
                    response['context']['state'] = 'checkout'
                    response['message'] = "Here's your order summary. Would you like to proceed to checkout?"
                    
                    # Calculate totals
                    total = sum(item['price'] * item['quantity'] for item in order)
                    response['order_summary'] = {
                        'items': order,
                        'total': total
                    }
                else:
                    response['message'] = "Your order is empty. What would you like to order?"
            else:
                new_items = process_order_request(menus[restaurant], user_message)
                if new_items:
                    order.extend(new_items)
                    response['context']['order'] = order
                    item_names = [f"{item['quantity']} x {item['item'].title()}" for item in new_items]
                    response['message'] = f"Added {', '.join(item_names)} to your order. Anything else or type 'done' to finish?"
                else:
                    response['message'] = "I didn't recognize any items from our menu. Could you try again or type 'done' to finish your order?"
                
        elif state == 'checkout':
            if any(word in user_message.lower() for word in ['yes', 'proceed', 'ok', 'sure', 'confirm']):
                response['context']['state'] = 'payment'
                response['message'] = "Great! Please choose your payment method:"
                response['options'] = ['Credit Card', 'Debit Card', 'UPI', 'Cash on Delivery']
            elif any(word in user_message.lower() for word in ['no', 'cancel', 'back']):
                response['context']['state'] = 'ordering'
                response['message'] = "No problem. You can continue ordering or type 'done' when you're finished."
            else:
                response['message'] = "Would you like to proceed to checkout? Please respond with yes or no."
                
        elif state == 'payment':
            payment_methods = ['credit card', 'debit card', 'upi', 'cash on delivery']
            selected_method = None
            
            for method in payment_methods:
                if method in user_message.lower():
                    selected_method = method
                    break
            
            if selected_method:
                response['context']['state'] = 'delivery'
                response['context']['payment_method'] = selected_method
                response['message'] = "Please provide your delivery address."
            else:
                response['message'] = "Please select a valid payment method: Credit Card, Debit Card, UPI, or Cash on Delivery."
                response['options'] = ['Credit Card', 'Debit Card', 'UPI', 'Cash on Delivery']
                
        elif state == 'delivery':
            # Simple validation: Check if the message has enough words to be an address
            if len(user_message.split()) >= 3:
                response['context']['state'] = 'confirmation'
                response['context']['address'] = user_message
                
                # Calculate order total
                total = sum(item['price'] * item['quantity'] for item in order)
                
                # Generate order ID
                import random
                order_id = f"ORDER{random.randint(10000, 99999)}"
                response['context']['order_id'] = order_id
                
                payment_method = response['context'].get('payment_method', 'selected payment method')
                
                response['message'] = f"Thank you! Your order (ID: {order_id}) has been placed successfully with {restaurant.title()}. Your total is ₹{total}. Payment will be made via {payment_method}. Your food will be delivered to your address within 30-45 minutes."
                
                # Reset order but keep restaurant and state for potential reordering
                response['context']['state'] = 'new_order'
            else:
                response['message'] = "Please provide a valid delivery address with street name, area, and city."
                
        elif state == 'new_order':
            if any(word in user_message.lower() for word in ['new', 'another', 'more', 'again']):
                response['context']['state'] = 'ordering'
                response['context']['order'] = []
                response['message'] = f"Sure! Let's start a new order with {restaurant.title()}. What would you like to order?"
                response['menu'] = [{"name": item.title(), "price": price} for item, price in menus[restaurant].items()]
            elif any(word in user_message.lower() for word in ['bye', 'thank', 'thanks', 'quit', 'exit']):
                response['context']['state'] = 'welcome'
                response['context']['restaurant'] = ''
                response['context']['order'] = []
                response['message'] = "Thank you for ordering with us! Feel free to start a new order anytime. Just tell me what you're looking for."
            else:
                response['message'] = "Would you like to place another order or are you done for now?"
                response['options'] = ['New Order', 'Exit']
        
        # Default welcome message for new sessions
        else:
            response['context']['state'] = 'welcome'
            response['message'] = "Welcome to NLP Food Ordering System! What would you like to eat today?"
            
        return jsonify(response)
            
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({
            'message': "Sorry, there was an error processing your request. Please try again.",
            'context': {
                'state': 'welcome',
                'restaurant': '',
                'order': []
            }
        })

if __name__ == '__main__':
    port=int(os.environ.get("PORT", 5000))
    debug=os.environ.get("DEBUG", "false").lower() == "true"
    app.run(debug=debug, port=port, host='0.0.0.0')