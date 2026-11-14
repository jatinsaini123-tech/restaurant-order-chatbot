"""
chatbot_service.py - Chatbot Dialogue Controller and Cart Synchronizer
Smart Chatbot for Restaurant Order Automation

Coordinates intent classification, entity extraction, database menu lookups,
cart session updates, order status checks, and formatted conversational responses.
"""

from chatbot_nlp import get_intent_classifier, EntityExtractor
from recommendation import RecommendationEngine
from database import query_db, execute_db

TAX_RATE = 0.05  # 5% Restaurant GST

def calculate_cart_totals(cart: dict) -> dict:
    """
    Recalculates cart subtotal, tax, and total from live database prices.
    cart structure: {str(item_id): {'quantity': int, ...}}
    """
    if not cart:
        return {'items': [], 'subtotal': 0.0, 'tax': 0.0, 'total': 0.0, 'item_count': 0}

    item_ids = list(cart.keys())
    placeholders = ','.join('?' for _ in item_ids)
    sql = f"SELECT id, name, price, is_veg, is_available, image_url FROM menu_items WHERE id IN ({placeholders})"
    rows = query_db(sql, tuple(item_ids))
    db_items = {str(r['id']): dict(r) for r in (rows or [])}

    cart_items = []
    subtotal = 0.0
    total_qty = 0

    for item_id, entry in list(cart.items()):
        db_item = db_items.get(str(item_id))
        if not db_item:
            continue
        
        qty = int(entry.get('quantity', 1))
        if qty <= 0:
            continue

        item_subtotal = round(db_item['price'] * qty, 2)
        subtotal += item_subtotal
        total_qty += qty

        cart_items.append({
            'id': db_item['id'],
            'name': db_item['name'],
            'price': db_item['price'],
            'quantity': qty,
            'subtotal': item_subtotal,
            'is_veg': db_item['is_veg'],
            'is_available': db_item['is_available'],
            'image_url': db_item['image_url']
        })

    tax = round(subtotal * TAX_RATE, 2)
    grand_total = round(subtotal + tax, 2)

    return {
        'items': cart_items,
        'subtotal': round(subtotal, 2),
        'tax': tax,
        'total': grand_total,
        'item_count': total_qty
    }

class ChatbotService:
    """Handles end-to-end conversation flow, cart mutations, and context management."""

    @staticmethod
    def process_message(user_message: str, session_cart: dict, user_context: dict = None) -> dict:
        """
        Processes a customer message and updates the session cart if applicable.
        
        Args:
            user_message (str): Raw message sent by customer.
            session_cart (dict): Current session cart dict {item_id: {'quantity': N}}.
            user_context (dict): Contextual metadata (e.g. last order ID).

        Returns:
            dict: {
                'reply': str,
                'intent': str,
                'confidence': float,
                'action': str,
                'cart': dict,
                'items': list,
                'quick_replies': list
            }
        """
        if user_context is None:
            user_context = {}

        classifier = get_intent_classifier()
        intent, confidence = classifier.predict(user_message)

        # Entity extraction
        matched_item, match_score = EntityExtractor.match_food_item(user_message)
        quantity = EntityExtractor.extract_quantity(user_message)
        budget = EntityExtractor.extract_budget(user_message)
        dietary_pref = EntityExtractor.extract_dietary_preference(user_message)
        order_code = EntityExtractor.extract_order_code(user_message) or user_context.get('last_order_code')

        # Domain reinforcement: If user explicitly mentions adding/ordering an identified food item
        clean_msg = user_message.lower()
        if matched_item and any(w in clean_msg for w in ['add', 'order', 'want', 'buy', 'get']):
            intent = 'add_to_cart'
        elif matched_item and any(w in clean_msg for w in ['remove', 'delete', 'cancel', 'drop']) and 'order' not in clean_msg:
            intent = 'remove_from_cart'
        elif matched_item and any(w in clean_msg for w in ['price', 'cost', 'rate', 'how much']):
            intent = 'ask_price'
        elif budget is not None or 'recommend' in clean_msg or 'suggest' in clean_msg:
            intent = 'recommend_food'
        elif 'track' in clean_msg:
            intent = 'track_order'
        elif 'cancel' in clean_msg and (order_code or 'order' in clean_msg):
            intent = 'cancel_order'

        # Default response structure
        response = {
            'reply': "",
            'intent': intent,
            'confidence': confidence,
            'action': 'none',
            'cart': None,
            'items': None,
            'quick_replies': ["Show Menu", "Veg Specials", "Recommend Under ₹300", "My Cart", "Track Order"]
        }

        # 1. GREETING
        if intent == 'greeting':
            response['reply'] = (
                "Hello! Welcome to **SpiceCraft Bistro** 🍽️! I am your AI food assistant.\n\n"
                "I can help you browse our menu, suggest dishes based on your budget, "
                "add items to your cart, and track your active orders.\n"
                "What would you like to enjoy today?"
            )
            response['quick_replies'] = ["Show Menu", "Recommend Under ₹300", "Veg Specials", "What's in my cart?"]

        # 2. SHOW MENU
        elif intent == 'show_menu':
            items = query_db(
                "SELECT m.*, c.name as category_name FROM menu_items m JOIN categories c ON m.category_id = c.id WHERE m.is_available = 1 ORDER BY m.category_id, m.price"
            )
            response['reply'] = (
                "Here is our complete menu! You can also tell me to add any dish, "
                "e.g., *'Add 2 Paneer Butter Masala'* or *'Order 1 Margherita Pizza'*."
            )
            response['action'] = 'menu_shown'
            response['items'] = [dict(i) for i in items[:8]] if items else []
            response['quick_replies'] = ["Recommend Under ₹300", "Pure Veg Dishes", "Add Paneer Tikka", "Checkout"]

        # 3. SEARCH FOOD
        elif intent == 'search_food':
            if matched_item:
                avail_str = "✅ In Stock" if matched_item['is_available'] else "❌ Currently Sold Out"
                veg_badge = "🟢 Veg" if matched_item['is_veg'] else "🔴 Non-Veg"
                response['reply'] = (
                    f"Yes! We have **{matched_item['name']}** ({veg_badge}) for **₹{matched_item['price']:.2f}**.\n"
                    f"Status: {avail_str}\n"
                    f"_{matched_item['description']}_\n\n"
                    f"Would you like me to add it to your cart?"
                )
                response['action'] = 'food_found'
                response['items'] = [matched_item]
                if matched_item['is_available']:
                    response['quick_replies'] = [f"Add 1 {matched_item['name']}", f"Add 2 {matched_item['name']}", "Show Menu"]
            else:
                response['reply'] = (
                    "I searched our kitchen, but couldn't find an exact match for that dish. "
                    "Would you like to browse our full menu or check our popular specials?"
                )
                response['quick_replies'] = ["Show Menu", "Popular Dishes", "Veg Specials"]

        # 4. ASK PRICE
        elif intent == 'ask_price':
            if matched_item:
                veg_badge = "🟢 Veg" if matched_item['is_veg'] else "🔴 Non-Veg"
                avail_status = "" if matched_item['is_available'] else " (Note: Currently Sold Out)"
                response['reply'] = (
                    f"The price of **{matched_item['name']}** ({veg_badge}) is **₹{matched_item['price']:.2f}**{avail_status}.\n"
                    f"Rated {matched_item['rating']}★ by our diners. "
                    f"Would you like me to add it to your order?"
                )
                if matched_item['is_available']:
                    response['quick_replies'] = [f"Add 1 {matched_item['name']}", "Show Menu", "My Cart"]
            else:
                response['reply'] = (
                    "Which dish would you like to check the price for? "
                    "For example, ask: *'What is the price of Butter Chicken?'* or *'How much is Garlic Naan?'*"
                )
                response['quick_replies'] = ["Price of Paneer Tikka", "Price of Butter Chicken", "Price of Margherita Pizza"]

        # 5. ADD TO CART
        elif intent == 'add_to_cart':
            if not matched_item:
                response['reply'] = (
                    "Which dish would you like to add? Please specify the name, "
                    "for example: *'Add 2 Paneer Butter Masala'* or *'Order 1 French Fries'*."
                )
                response['quick_replies'] = ["Add 1 Paneer Tikka", "Add 1 Butter Chicken", "Add 2 Garlic Naan"]
            elif not matched_item['is_available']:
                response['reply'] = (
                    f"I'm very sorry, but **{matched_item['name']}** is currently **Sold Out** today. "
                    "Can I recommend another popular choice from the same category?"
                )
                recs = RecommendationEngine.get_recommendations(category_id=matched_item['category_id'], limit=3)
                response['items'] = recs
                response['quick_replies'] = ["Recommend food under 300", "Show Menu"]
            else:
                # Add or update item in session cart
                item_id_str = str(matched_item['id'])
                current_qty = session_cart.get(item_id_str, {}).get('quantity', 0)
                new_qty = current_qty + quantity
                session_cart[item_id_str] = {'quantity': new_qty}

                cart_summary = calculate_cart_totals(session_cart)
                response['action'] = 'cart_updated'
                response['cart'] = cart_summary
                response['reply'] = (
                    f"🛒 Added **{quantity} x {matched_item['name']}** (₹{matched_item['price']:.2f} each) to your cart!\n\n"
                    f"**Cart Summary:** {cart_summary['item_count']} item(s) | Subtotal: ₹{cart_summary['subtotal']:.2f} | "
                    f"**Total (with 5% GST): ₹{cart_summary['total']:.2f}**.\n\n"
                    f"Say *'Checkout'* when you are ready to place your order, or continue adding items."
                )
                response['quick_replies'] = ["Checkout", "View Cart", "Add Garlic Naan", "Show Menu"]

        # 6. REMOVE FROM CART
        elif intent == 'remove_from_cart':
            if not matched_item:
                response['reply'] = (
                    "Which item would you like to remove from your cart? "
                    "For example: *'Remove 1 Burger'* or *'Delete Fries'*."
                )
            else:
                item_id_str = str(matched_item['id'])
                if item_id_str in session_cart:
                    current_qty = session_cart[item_id_str].get('quantity', 1)
                    if current_qty > quantity:
                        session_cart[item_id_str]['quantity'] = current_qty - quantity
                        msg = f"Reduced **{matched_item['name']}** by {quantity}."
                    else:
                        del session_cart[item_id_str]
                        msg = f"Removed **{matched_item['name']}** completely from your cart."

                    cart_summary = calculate_cart_totals(session_cart)
                    response['action'] = 'cart_updated'
                    response['cart'] = cart_summary
                    response['reply'] = (
                        f"🗑️ {msg}\n"
                        f"Updated Cart Total: **₹{cart_summary['total']:.2f}** ({cart_summary['item_count']} items)."
                    )
                else:
                    response['reply'] = (
                        f"**{matched_item['name']}** was not found in your cart. "
                        "You can say *'What is in my cart?'* to see your current selection."
                    )
                    response['quick_replies'] = ["View Cart", "Show Menu"]

        # 7. UPDATE QUANTITY
        elif intent == 'update_quantity':
            if not matched_item:
                response['reply'] = "Which item's quantity would you like to change? E.g. *'Change Burger quantity to 3'*."
            else:
                item_id_str = str(matched_item['id'])
                if quantity <= 0:
                    if item_id_str in session_cart:
                        del session_cart[item_id_str]
                    msg = f"Removed **{matched_item['name']}** from cart."
                else:
                    session_cart[item_id_str] = {'quantity': quantity}
                    msg = f"Updated **{matched_item['name']}** quantity to **{quantity}**."

                cart_summary = calculate_cart_totals(session_cart)
                response['action'] = 'cart_updated'
                response['cart'] = cart_summary
                response['reply'] = (
                    f"✏️ {msg}\n"
                    f"New Cart Total: **₹{cart_summary['total']:.2f}**."
                )
                response['quick_replies'] = ["Checkout", "View Cart", "Show Menu"]

        # 8. RECOMMEND FOOD
        elif intent == 'recommend_food':
            recs = RecommendationEngine.get_recommendations(
                budget=budget,
                is_veg=dietary_pref,
                limit=4
            )
            response['action'] = 'recommendations'
            response['items'] = recs

            budget_txt = f" under ₹{int(budget)}" if budget else ""
            diet_txt = " vegetarian" if dietary_pref == 1 else (" non-vegetarian" if dietary_pref == 0 else "")

            if recs:
                response['reply'] = (
                    f"Here are my top chef-curated{diet_txt} recommendations{budget_txt}:\n\n" +
                    "\n".join([f"• **{r['name']}** (₹{r['price']:.0f}) - _{r['explanation']}_" for r in recs]) +
                    "\n\nWould you like me to add any of these to your cart?"
                )
                response['quick_replies'] = [f"Add 1 {recs[0]['name']}", "Show Menu", "My Cart"]
            else:
                response['reply'] = (
                    f"I couldn't find any items matching your exact budget{budget_txt}. "
                    "Here are our most popular value dishes instead!"
                )
                response['items'] = RecommendationEngine.get_popular_items(limit=3)

        # 9. DIETARY PREFERENCE
        elif intent == 'dietary_preference':
            is_veg = 1 if (dietary_pref == 1 or 'veg' in clean_msg and 'non' not in clean_msg) else 0
            recs = RecommendationEngine.get_recommendations(is_veg=is_veg, limit=4)
            label = "100% Pure Vegetarian" if is_veg == 1 else "Signature Non-Vegetarian"
            response['action'] = 'recommendations'
            response['items'] = recs
            response['reply'] = (
                f"🌱 Showing our best **{label}** specialties:\n\n" +
                "\n".join([f"• **{r['name']}** (₹{r['price']:.0f}) - {r['explanation']}" for r in recs]) +
                "\n\nTell me which one you'd like to taste!"
            )
            if recs:
                response['quick_replies'] = [f"Add 1 {recs[0]['name']}", "Show Menu", "View Cart"]

        # 10. CHECK CART
        elif intent == 'check_cart':
            cart_summary = calculate_cart_totals(session_cart)
            response['action'] = 'cart_updated'
            response['cart'] = cart_summary
            if not cart_summary['items']:
                response['reply'] = (
                    "Your shopping cart is currently empty 🛒.\n"
                    "Explore our menu or ask me for a recommendation to start adding food!"
                )
                response['quick_replies'] = ["Show Menu", "Recommend Under ₹300", "Popular Dishes"]
            else:
                items_text = "\n".join([
                    f"• {it['quantity']} x **{it['name']}** - ₹{it['subtotal']:.2f}"
                    for it in cart_summary['items']
                ])
                response['reply'] = (
                    f"🛒 **Your Shopping Cart:**\n{items_text}\n\n"
                    f"Subtotal: ₹{cart_summary['subtotal']:.2f}\n"
                    f"GST (5%): ₹{cart_summary['tax']:.2f}\n"
                    f"**Grand Total: ₹{cart_summary['total']:.2f}**\n\n"
                    f"Ready to order? Say *'Checkout'* to finalize!"
                )
                response['quick_replies'] = ["Checkout", "Add Garlic Naan", "Show Menu"]

        # 11. CHECKOUT
        elif intent == 'checkout':
            cart_summary = calculate_cart_totals(session_cart)
            if not cart_summary['items']:
                response['reply'] = (
                    "Your cart is empty! Please add some delicious food before proceeding to checkout."
                )
                response['quick_replies'] = ["Show Menu", "Recommend Under ₹300"]
            else:
                response['action'] = 'confirm_checkout'
                response['cart'] = cart_summary
                response['reply'] = (
                    f"📋 You have **{cart_summary['item_count']} item(s)** ready with a total of **₹{cart_summary['total']:.2f}**.\n\n"
                    f"To complete your order, please click the **'Proceed to Checkout'** button below to provide "
                    f"your delivery address and contact number."
                )
                response['quick_replies'] = ["Open Checkout Form", "View Cart", "Cancel"]

        # 12. TRACK ORDER
        elif intent == 'track_order':
            if not order_code:
                response['reply'] = (
                    "Please provide your Order ID to track its status! "
                    "For example: *'Track order ORD-20261028-101'*."
                )
                response['quick_replies'] = ["Track ORD-20261028-101", "Show Menu"]
            else:
                order = query_db("SELECT * FROM orders WHERE order_code = ?", (order_code,), one=True)
                if not order:
                    response['reply'] = (
                        f"❌ I could not find any active order with ID **{order_code}**. "
                        "Please check the spelling or track via the Track Order page."
                    )
                else:
                    status_icons = {
                        'Pending': '⏳ Pending Confirmation',
                        'Confirmed': '✅ Confirmed by Kitchen',
                        'Preparing': '🍳 Chef is Preparing Your Food',
                        'Ready': '📦 Packed and Ready',
                        'Out for Delivery': '🛵 Out for Delivery',
                        'Delivered': '🎉 Delivered! Enjoy your meal',
                        'Cancelled': '❌ Cancelled'
                    }
                    status_text = status_icons.get(order['status'], order['status'])
                    response['action'] = 'order_tracked'
                    response['reply'] = (
                        f"📍 **Order Status for {order['order_code']}**\n\n"
                        f"Customer: {order['user_name']}\n"
                        f"Status: **{status_text}**\n"
                        f"Total Amount: **₹{order['total_amount']:.2f}** ({order['payment_method']})\n"
                        f"Delivery to: {order['user_address']}\n"
                        f"Ordered on: {order['created_at']}"
                    )
                    if order['status'] in ('Pending', 'Confirmed'):
                        response['quick_replies'] = [f"Cancel {order['order_code']}", "Show Menu"]

        # 13. CANCEL ORDER
        elif intent == 'cancel_order':
            if not order_code:
                response['reply'] = (
                    "Which order would you like to cancel? Please specify the Order ID, "
                    "for example: *'Cancel order ORD-20261028-101'*."
                )
            else:
                order = query_db("SELECT * FROM orders WHERE order_code = ?", (order_code,), one=True)
                if not order:
                    response['reply'] = f"Could not find order **{order_code}** to cancel."
                elif order['status'] == 'Cancelled':
                    response['reply'] = f"Order **{order_code}** has already been cancelled."
                elif order['status'] in ('Delivered', 'Out for Delivery'):
                    response['reply'] = (
                        f"⚠️ Order **{order_code}** cannot be cancelled because it is already **{order['status']}**! "
                        "Please contact restaurant support for urgent inquiries."
                    )
                elif order['status'] == 'Preparing':
                    response['reply'] = (
                        f"⚠️ Order **{order_code}** is currently being cooked by the chef. "
                        "For cancellations during preparation, please call our hotline directly."
                    )
                else:
                    # Cancel order in database
                    execute_db("UPDATE orders SET status = 'Cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (order['id'],))
                    response['action'] = 'order_cancelled'
                    response['reply'] = (
                        f"✅ Order **{order_code}** has been successfully **Cancelled**. "
                        "If you were charged, a full refund will be processed to your source account."
                    )
                    response['quick_replies'] = ["Show Menu", "Help"]

        # 14. HELP
        elif intent == 'help':
            response['reply'] = (
                "🤖 **How I Can Assist You:**\n\n"
                "• **Browse Menu:** *'Show me the menu'*, *'Do you have momos?'*\n"
                "• **Order Food:** *'Add 2 Burgers'*, *'Order 1 Paneer Tikka'*\n"
                "• **Check Prices:** *'What is the price of pizza?'*\n"
                "• **Recommendations:** *'Recommend food under 300 rupees'*, *'Pure veg specials'*\n"
                "• **Manage Cart:** *'View cart'*, *'Remove 1 fries'*, *'What is my total bill?'*\n"
                "• **Checkout:** *'Checkout'*, *'Place my order'*\n"
                "• **Track & Cancel:** *'Track order ORD-20261028-101'*, *'Cancel my order'*"
            )

        # 15. GOODBYE
        elif intent == 'goodbye':
            response['reply'] = (
                "Thank you for chatting with **SpiceCraft Bistro**! "
                "Enjoy your meal and have a wonderful day! 👋🍽️"
            )

        # 16. UNKNOWN INTENT / FALLBACK
        else:
            response['reply'] = (
                "I'm not quite sure I caught that. I can help you explore our menu, "
                "check prices, place orders, or track existing deliveries.\n\n"
                "Try saying: *'Show Menu'*, *'Recommend under ₹300'*, or *'What is in my cart?'*"
            )
            response['quick_replies'] = ["Show Menu", "Recommend Under ₹300", "My Cart", "Help"]

        # Always attach fresh cart totals if not explicitly provided
        if response['cart'] is None:
            response['cart'] = calculate_cart_totals(session_cart)

        return response
