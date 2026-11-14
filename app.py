"""
app.py - Main Flask Application
Smart Chatbot for Restaurant Order Automation Using NLP and Intent Recognition

Provides customer ordering portal, real-time AI chatbot endpoint,
smart recommendation service, and secure admin dashboard.
"""

import os
import re
import random
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, jsonify, session,
    redirect, url_for, flash, abort
)
from werkzeug.security import check_password_hash, generate_password_hash
from database import query_db, execute_db, execute_insert
from chatbot_service import ChatbotService, calculate_cart_totals, TAX_RATE
from recommendation import RecommendationEngine

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'smart-restaurant-secret-key-semester-project-2026')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# ---------------------------------------------------------
# AUTHENTICATION DECORATOR FOR ADMIN
# ---------------------------------------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            if request.path.startswith('/api/admin'):
                return jsonify({'success': False, 'error': 'Unauthorized admin access required.'}), 401
            return redirect(url_for('admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ---------------------------------------------------------
# CONTEXT PROCESSOR & CART HELPERS
# ---------------------------------------------------------
def get_session_cart():
    """Retrieves or initializes user shopping cart from session."""
    if 'cart' not in session or not isinstance(session['cart'], dict):
        session['cart'] = {}
    return session['cart']

@app.context_processor
def inject_global_data():
    """Makes categories and cart item count available to all templates."""
    categories = query_db("SELECT * FROM categories ORDER BY display_order ASC")
    cart = get_session_cart()
    cart_totals = calculate_cart_totals(cart)
    return {
        'all_categories': categories or [],
        'cart_item_count': cart_totals['item_count'],
        'cart_grand_total': cart_totals['total']
    }

# ---------------------------------------------------------
# CUSTOMER FACING ROUTES
# ---------------------------------------------------------
@app.route('/')
def index():
    """Renders the main restaurant homepage and interactive menu."""
    categories = query_db("SELECT * FROM categories ORDER BY display_order ASC")
    featured_items = query_db(
        "SELECT m.*, c.name as category_name FROM menu_items m "
        "JOIN categories c ON m.category_id = c.id "
        "WHERE m.is_available = 1 ORDER BY m.popularity_score DESC LIMIT 6"
    )
    return render_template('index.html', categories=categories, featured_items=featured_items)

@app.route('/api/menu')
def api_menu():
    """Returns menu items with optional category, search, and veg filtering."""
    category_id = request.args.get('category_id')
    search_query = request.args.get('q', '').strip()
    is_veg = request.args.get('is_veg')

    sql = """
        SELECT m.*, c.name as category_name, c.slug as category_slug
        FROM menu_items m
        JOIN categories c ON m.category_id = c.id
        WHERE 1=1
    """
    params = []

    if category_id and category_id != 'all':
        sql += " AND m.category_id = ?"
        params.append(category_id)

    if is_veg is not None and is_veg in ('0', '1'):
        sql += " AND m.is_veg = ?"
        params.append(int(is_veg))

    if search_query:
        sql += " AND (m.name LIKE ? OR m.description LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term])

    sql += " ORDER BY m.is_available DESC, m.category_id ASC, m.price ASC"
    items = query_db(sql, tuple(params))
    return jsonify({'success': True, 'items': items or []})

@app.route('/api/categories')
def api_categories():
    """Returns all food categories."""
    categories = query_db("SELECT * FROM categories ORDER BY display_order ASC")
    return jsonify({'success': True, 'categories': categories or []})

# ---------------------------------------------------------
# CART API ENDPOINTS
# ---------------------------------------------------------
@app.route('/api/cart', methods=['GET'])
def api_get_cart():
    """Returns current session cart with live recalculated totals."""
    cart = get_session_cart()
    cart_summary = calculate_cart_totals(cart)
    return jsonify({'success': True, 'cart': cart_summary})

@app.route('/api/cart/add', methods=['POST'])
def api_add_to_cart():
    """Adds a menu item to the session cart."""
    data = request.get_json() or {}
    item_id = str(data.get('item_id', ''))
    quantity = int(data.get('quantity', 1))

    if not item_id or quantity <= 0:
        return jsonify({'success': False, 'error': 'Invalid item or quantity'}), 400

    # Verify item exists and is in stock
    item = query_db("SELECT * FROM menu_items WHERE id = ?", (item_id,), one=True)
    if not item:
        return jsonify({'success': False, 'error': 'Item not found in menu'}), 404
    if not item['is_available']:
        return jsonify({'success': False, 'error': f"'{item['name']}' is currently sold out."}), 400

    cart = get_session_cart()
    current_qty = cart.get(item_id, {}).get('quantity', 0)
    cart[item_id] = {'quantity': current_qty + quantity}
    session['cart'] = cart
    session.modified = True

    cart_summary = calculate_cart_totals(cart)
    return jsonify({
        'success': True,
        'message': f"Added {quantity} x {item['name']} to cart.",
        'cart': cart_summary
    })

@app.route('/api/cart/update', methods=['POST'])
def api_update_cart():
    """Updates quantity of an item in the session cart."""
    data = request.get_json() or {}
    item_id = str(data.get('item_id', ''))
    quantity = int(data.get('quantity', 0))

    cart = get_session_cart()
    if item_id in cart:
        if quantity <= 0:
            del cart[item_id]
        else:
            cart[item_id]['quantity'] = quantity
        session['cart'] = cart
        session.modified = True

    cart_summary = calculate_cart_totals(cart)
    return jsonify({'success': True, 'cart': cart_summary})

@app.route('/api/cart/remove', methods=['POST'])
def api_remove_from_cart():
    """Removes an item from the session cart."""
    data = request.get_json() or {}
    item_id = str(data.get('item_id', ''))

    cart = get_session_cart()
    if item_id in cart:
        del cart[item_id]
        session['cart'] = cart
        session.modified = True

    cart_summary = calculate_cart_totals(cart)
    return jsonify({'success': True, 'cart': cart_summary})

@app.route('/api/cart/clear', methods=['POST'])
def api_clear_cart():
    """Empties the session cart."""
    session['cart'] = {}
    session.modified = True
    return jsonify({'success': True, 'cart': calculate_cart_totals({})})

# ---------------------------------------------------------
# CHECKOUT & ORDER PLACEMENT
# ---------------------------------------------------------
@app.route('/api/checkout', methods=['POST'])
def api_checkout():
    """
    Validates delivery details, recalculates totals on backend,
    creates historical order snapshots, and stores order in SQLite database.
    """
    cart = get_session_cart()
    cart_summary = calculate_cart_totals(cart)

    if not cart_summary['items']:
        return jsonify({'success': False, 'error': 'Your cart is empty.'}), 400

    data = request.get_json() or {}
    user_name = data.get('name', '').strip()
    user_phone = data.get('phone', '').strip()
    user_address = data.get('address', '').strip()
    payment_method = data.get('payment_method', 'Cash on Delivery').strip()
    special_instructions = data.get('special_instructions', '').strip()

    # Server-side validation
    if len(user_name) < 2:
        return jsonify({'success': False, 'error': 'Please enter a valid customer name.'}), 400
    
    # Phone number validation (at least 10 digits)
    phone_digits = re.sub(r'\D', '', user_phone)
    if len(phone_digits) < 10:
        return jsonify({'success': False, 'error': 'Please enter a valid 10-digit phone number.'}), 400

    if len(user_address) < 8:
        return jsonify({'success': False, 'error': 'Please provide a detailed delivery address.'}), 400

    # Generate unique order code (e.g. ORD-20261028-4821)
    today_str = datetime.now().strftime("%Y%m%d")
    random_suffix = random.randint(1000, 9999)
    order_code = f"ORD-{today_str}-{random_suffix}"

    # Insert into orders table
    order_id = execute_insert(
        """INSERT INTO orders 
           (order_code, user_name, user_phone, user_address, subtotal, tax_amount, total_amount, status, payment_method, special_instructions)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?, ?)""",
        (order_code, user_name, user_phone, user_address,
         cart_summary['subtotal'], cart_summary['tax'], cart_summary['total'],
         payment_method, special_instructions)
    )

    # Insert snapshot of order items with current prices & names
    for it in cart_summary['items']:
        execute_db(
            """INSERT INTO order_items (order_id, menu_item_id, item_name, item_price, quantity, subtotal)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (order_id, it['id'], it['name'], it['price'], it['quantity'], it['subtotal'])
        )
        # Increment popularity score for recommended dishes
        execute_db(
            "UPDATE menu_items SET popularity_score = popularity_score + ? WHERE id = ?",
            (it['quantity'], it['id'])
        )

    # Record or update customer profile in users table
    existing_user = query_db("SELECT id FROM users WHERE phone = ?", (user_phone,), one=True)
    if not existing_user:
        execute_db(
            "INSERT INTO users (name, phone, address) VALUES (?, ?, ?)",
            (user_name, user_phone, user_address)
        )

    # Clear shopping cart and save last order code in session
    session['cart'] = {}
    session['last_order_code'] = order_code
    session.modified = True

    return jsonify({
        'success': True,
        'order_code': order_code,
        'redirect_url': url_for('order_success', order_code=order_code)
    })

@app.route('/order-success/<order_code>')
def order_success(order_code):
    """Renders the order confirmation page with full invoice breakdown."""
    order = query_db("SELECT * FROM orders WHERE order_code = ?", (order_code,), one=True)
    if not order:
        flash("Order not found.", "warning")
        return redirect(url_for('index'))

    items = query_db("SELECT * FROM order_items WHERE order_id = ?", (order['id'],))
    return render_template('order_success.html', order=order, items=items)

# ---------------------------------------------------------
# ORDER TRACKING & CANCELLATION
# ---------------------------------------------------------
@app.route('/track')
def track_page():
    """Renders the order tracking lookup page."""
    order_code = request.args.get('code', session.get('last_order_code', ''))
    order = None
    items = []
    if order_code:
        order = query_db("SELECT * FROM orders WHERE order_code = ?", (order_code.strip(),), one=True)
        if order:
            items = query_db("SELECT * FROM order_items WHERE order_id = ?", (order['id'],))
    return render_template('track.html', order=order, items=items, query_code=order_code)

@app.route('/api/track/<order_code>')
def api_track_order(order_code):
    """Returns order details and current status for tracking."""
    order = query_db("SELECT * FROM orders WHERE order_code = ?", (order_code.strip(),), one=True)
    if not order:
        return jsonify({'success': False, 'error': f"Order '{order_code}' was not found."}), 404

    items = query_db("SELECT * FROM order_items WHERE order_id = ?", (order['id'],))
    return jsonify({
        'success': True,
        'order': dict(order),
        'items': [dict(i) for i in items or []]
    })

@app.route('/api/order/cancel', methods=['POST'])
def api_cancel_order():
    """Cancels an order if eligible (Pending or Confirmed only)."""
    data = request.get_json() or {}
    order_code = data.get('order_code', '').strip()

    if not order_code:
        return jsonify({'success': False, 'error': 'Order code is required.'}), 400

    order = query_db("SELECT * FROM orders WHERE order_code = ?", (order_code,), one=True)
    if not order:
        return jsonify({'success': False, 'error': 'Order not found.'}), 404

    if order['status'] == 'Cancelled':
        return jsonify({'success': False, 'error': 'This order has already been cancelled.'}), 400

    if order['status'] in ('Preparing', 'Ready', 'Out for Delivery', 'Delivered'):
        return jsonify({
            'success': False,
            'error': f"Order cannot be cancelled because it is already '{order['status']}'."
        }), 400

    execute_db(
        "UPDATE orders SET status = 'Cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (order['id'],)
    )
    return jsonify({'success': True, 'message': f"Order {order_code} has been successfully cancelled."})

# ---------------------------------------------------------
# AI CHATBOT API
# ---------------------------------------------------------
@app.route('/api/chatbot', methods=['POST'])
def api_chatbot():
    """
    Receives customer message, detects intent via scikit-learn ML model,
    extracts entities, updates session cart, and returns formatted reply.
    """
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'success': False, 'error': 'Empty message received.'}), 400

    cart = get_session_cart()
    context = {
        'last_order_code': session.get('last_order_code')
    }

    bot_result = ChatbotService.process_message(user_message, cart, context)
    session['cart'] = cart
    session.modified = True

    return jsonify({
        'success': True,
        'reply': bot_result['reply'],
        'intent': bot_result['intent'],
        'confidence': bot_result['confidence'],
        'action': bot_result['action'],
        'cart': bot_result['cart'],
        'items': bot_result.get('items'),
        'quick_replies': bot_result.get('quick_replies', [])
    })

# ---------------------------------------------------------
# RECOMMENDATION API
# ---------------------------------------------------------
@app.route('/api/recommendations')
def api_recommendations():
    """Returns curated food recommendations based on budget and dietary preference."""
    budget = request.args.get('budget', type=float)
    is_veg = request.args.get('is_veg', type=int)
    category_id = request.args.get('category_id', type=int)

    items = RecommendationEngine.get_recommendations(
        budget=budget,
        is_veg=is_veg,
        category_id=category_id,
        limit=6
    )
    return jsonify({'success': True, 'recommendations': items})

# ---------------------------------------------------------
# ADMIN DASHBOARD & SECURITY
# ---------------------------------------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page with Werkzeug password hash verification."""
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        admin = query_db("SELECT * FROM admin_users WHERE username = ?", (username,), one=True)
        if admin and check_password_hash(admin['password_hash'], password):
            session['admin_logged_in'] = True
            session['admin_user'] = admin['username']
            session['admin_role'] = admin['role']
            flash("Welcome to the Admin Portal!", "success")
            next_url = request.args.get('next')
            return redirect(next_url or url_for('admin_dashboard'))
        else:
            error = "Invalid admin username or password. Please try again."

    return render_template('admin_login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    """Clears admin session."""
    session.pop('admin_logged_in', None)
    session.pop('admin_user', None)
    session.pop('admin_role', None)
    flash("You have logged out of the admin panel.", "info")
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Main administrative dashboard with KPIs, order lists, and menu management."""
    # Summary Metrics
    total_orders = query_db("SELECT COUNT(*) as count FROM orders", one=True)['count']
    total_revenue = query_db(
        "SELECT COALESCE(SUM(total_amount), 0.0) as rev FROM orders WHERE status != 'Cancelled'",
        one=True
    )['rev']
    pending_orders = query_db(
        "SELECT COUNT(*) as count FROM orders WHERE status IN ('Pending', 'Confirmed', 'Preparing')",
        one=True
    )['count']
    total_items = query_db("SELECT COUNT(*) as count FROM menu_items", one=True)['count']

    # Orders List
    orders = query_db("SELECT * FROM orders ORDER BY created_at DESC LIMIT 50")
    # Menu Items
    menu_items = query_db(
        "SELECT m.*, c.name as category_name FROM menu_items m "
        "JOIN categories c ON m.category_id = c.id ORDER BY m.category_id, m.name"
    )
    categories = query_db("SELECT * FROM categories ORDER BY display_order ASC")

    return render_template(
        'admin_dashboard.html',
        total_orders=total_orders,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        total_items=total_items,
        orders=orders or [],
        menu_items=menu_items or [],
        categories=categories or []
    )

@app.route('/api/admin/analytics')
@admin_required
def api_admin_analytics():
    """Provides aggregated sales data for Chart.js charts."""
    # 1. Orders by Status
    status_counts = query_db("SELECT status, COUNT(*) as count FROM orders GROUP BY status")
    
    # 2. Revenue by Category
    category_sales = query_db("""
        SELECT c.name as category_name, COALESCE(SUM(oi.subtotal), 0) as total_sales
        FROM categories c
        LEFT JOIN menu_items m ON c.id = m.category_id
        LEFT JOIN order_items oi ON m.id = oi.menu_item_id
        LEFT JOIN orders o ON oi.order_id = o.id AND o.status != 'Cancelled'
        GROUP BY c.id
    """)

    # 3. Top 5 Bestselling Dishes
    top_dishes = query_db("""
        SELECT item_name, SUM(quantity) as total_qty, SUM(subtotal) as total_revenue
        FROM order_items
        GROUP BY item_name
        ORDER BY total_qty DESC
        LIMIT 5
    """)

    return jsonify({
        'success': True,
        'status_counts': status_counts or [],
        'category_sales': category_sales or [],
        'top_dishes': top_dishes or []
    })

@app.route('/api/admin/orders/<int:order_id>/status', methods=['POST'])
@admin_required
def api_admin_update_order_status(order_id):
    """Updates the status of an existing order."""
    data = request.get_json() or {}
    new_status = data.get('status', '').strip()

    valid_statuses = ['Pending', 'Confirmed', 'Preparing', 'Ready', 'Out for Delivery', 'Delivered', 'Cancelled']
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'error': f"Invalid status: {new_status}"}), 400

    execute_db(
        "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_status, order_id)
    )
    return jsonify({'success': True, 'message': f"Order status updated to '{new_status}'."})

@app.route('/api/admin/orders/<int:order_id>/details')
@admin_required
def api_admin_order_details(order_id):
    """Fetches details and items for an order modal."""
    order = query_db("SELECT * FROM orders WHERE id = ?", (order_id,), one=True)
    if not order:
        return jsonify({'success': False, 'error': 'Order not found.'}), 404
    items = query_db("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    return jsonify({
        'success': True,
        'order': dict(order),
        'items': [dict(i) for i in items or []]
    })

# ---------------------------------------------------------
# ADMIN MENU MANAGEMENT (CRUD)
# ---------------------------------------------------------
@app.route('/api/admin/menu/add', methods=['POST'])
@admin_required
def api_admin_add_menu_item():
    """Adds a new menu item."""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    category_id = data.get('category_id')
    price = data.get('price')
    is_veg = int(data.get('is_veg', 1))
    is_available = int(data.get('is_available', 1))
    description = data.get('description', '').strip()
    image_url = data.get('image_url', '').strip() or 'placeholder.jpg'

    if not name or not category_id or price is None or float(price) < 0:
        return jsonify({'success': False, 'error': 'Invalid item name, category, or price.'}), 400

    try:
        new_id = execute_insert(
            """INSERT INTO menu_items (category_id, name, description, price, is_veg, is_available, image_url)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (category_id, name, description, float(price), is_veg, is_available, image_url)
        )
        return jsonify({'success': True, 'message': f"Dish '{name}' added successfully.", 'id': new_id})
    except Exception as e:
        return jsonify({'success': False, 'error': f"Item could not be created ({str(e)})."}), 400

@app.route('/api/admin/menu/<int:item_id>/edit', methods=['POST'])
@admin_required
def api_admin_edit_menu_item(item_id):
    """Updates an existing menu item."""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    category_id = data.get('category_id')
    price = data.get('price')
    is_veg = int(data.get('is_veg', 1))
    is_available = int(data.get('is_available', 1))
    description = data.get('description', '').strip()
    image_url = data.get('image_url', '').strip()

    if not name or price is None or float(price) < 0:
        return jsonify({'success': False, 'error': 'Invalid dish name or price.'}), 400

    execute_db(
        """UPDATE menu_items 
           SET category_id = ?, name = ?, description = ?, price = ?, is_veg = ?, is_available = ?, image_url = ?
           WHERE id = ?""",
        (category_id, name, description, float(price), is_veg, is_available, image_url, item_id)
    )
    return jsonify({'success': True, 'message': f"Dish '{name}' updated successfully."})

@app.route('/api/admin/menu/<int:item_id>/delete', methods=['POST'])
@admin_required
def api_admin_delete_menu_item(item_id):
    """Deletes a menu item."""
    item = query_db("SELECT name FROM menu_items WHERE id = ?", (item_id,), one=True)
    if not item:
        return jsonify({'success': False, 'error': 'Item not found.'}), 404

    execute_db("DELETE FROM menu_items WHERE id = ?", (item_id,))
    return jsonify({'success': True, 'message': f"Dish '{item['name']}' was removed from the menu."})

@app.route('/api/admin/menu/<int:item_id>/toggle-availability', methods=['POST'])
@admin_required
def api_admin_toggle_availability(item_id):
    """Toggles item availability switch between in-stock and sold out."""
    item = query_db("SELECT is_available, name FROM menu_items WHERE id = ?", (item_id,), one=True)
    if not item:
        return jsonify({'success': False, 'error': 'Item not found.'}), 404

    new_status = 0 if item['is_available'] == 1 else 1
    execute_db("UPDATE menu_items SET is_available = ? WHERE id = ?", (new_status, item_id))
    label = "In Stock" if new_status == 1 else "Sold Out"
    return jsonify({
        'success': True,
        'is_available': new_status,
        'message': f"'{item['name']}' is now marked as {label}."
    })

# ---------------------------------------------------------
# ERROR HANDLERS
# ---------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'API endpoint not found'}), 404
    return render_template('error.html', code=404, message="Page Not Found"), 404

@app.errorhandler(500)
def server_error(e):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    return render_template('error.html', code=500, message="Internal Server Error"), 500

if __name__ == '__main__':
    # Local development server
    app.run(host='127.0.0.1', port=5000, debug=True)
