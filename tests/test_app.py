"""
tests/test_app.py - Automated Test Suite
Smart Chatbot for Restaurant Order Automation

Tests:
- Login and authentication
- Menu loading, searching, and filtering
- Cart calculations and live database recalculations
- Quantity updates and removals
- Order placement and historical price snapshotting
- Invalid input validation
- Order tracking and cancellation business rules
- Chatbot intent recognition (ML model)
- Unknown chatbot message fallbacks
- Recommendation engine (budget, veg, availability constraints)
- Admin authorization and role security
- Admin menu management (CRUD)
- Order status updates
"""

import unittest
import json
import os
import sys

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from database import query_db, execute_db, init_schema
from init_db import seed_database
from chatbot_nlp import get_intent_classifier, EntityExtractor
from recommendation import RecommendationEngine

class RestaurantAppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Initializes test database and seeds initial data."""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        seed_database()
        cls.client = app.test_client()
        cls.classifier = get_intent_classifier()

    def setUp(self):
        """Resets orders status and clears session before each test for idempotency."""
        execute_db("UPDATE orders SET status = 'Pending' WHERE order_code = 'ORD-20261028-101'")
        execute_db("UPDATE orders SET status = 'Delivered' WHERE order_code = 'ORD-20261028-103'")
        with self.client.session_transaction() as sess:
            sess.clear()

    # ---------------------------------------------------------
    # 1. MENU LOADING, SEARCHING & FILTERING
    # ---------------------------------------------------------
    def test_homepage_loads(self):
        """Verify homepage renders with status 200."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'SpiceCraft Bistro', res.data)

    def test_api_menu_loading(self):
        """Verify /api/menu returns full list of dishes."""
        res = self.client.get('/api/menu')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertGreater(len(data['items']), 10)

    def test_menu_search_filtering(self):
        """Verify search query filters menu by dish name."""
        res = self.client.get('/api/menu?q=burger')
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        names = [item['name'].lower() for item in data['items']]
        self.assertTrue(all('burger' in name for name in names))

    def test_menu_veg_filtering(self):
        """Verify vegetarian filter only returns veg dishes."""
        res = self.client.get('/api/menu?is_veg=1')
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertTrue(all(item['is_veg'] == 1 for item in data['items']))

    # ---------------------------------------------------------
    # 2. CART OPERATIONS & TAX CALCULATIONS
    # ---------------------------------------------------------
    def test_cart_operations_and_calculations(self):
        """Verify adding, updating quantity, recalculating tax (5%), and clearing cart."""
        # 1. Add item 1 (Paneer Tikka, ₹240) qty 2
        res = self.client.post('/api/cart/add', 
                               data=json.dumps({'item_id': 1, 'quantity': 2}),
                               content_type='application/json')
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['cart']['item_count'], 2)
        self.assertEqual(data['cart']['subtotal'], 480.0)
        # 5% of 480 is 24.0
        self.assertEqual(data['cart']['tax'], 24.0)
        self.assertEqual(data['cart']['total'], 504.0)

        # 2. Update quantity to 3
        res2 = self.client.post('/api/cart/update',
                                data=json.dumps({'item_id': 1, 'quantity': 3}),
                                content_type='application/json')
        data2 = json.loads(res2.data)
        self.assertEqual(data2['cart']['subtotal'], 720.0)
        self.assertEqual(data2['cart']['tax'], 36.0)
        self.assertEqual(data2['cart']['total'], 756.0)

        # 3. Remove item from cart
        res3 = self.client.post('/api/cart/remove',
                                data=json.dumps({'item_id': 1}),
                                content_type='application/json')
        data3 = json.loads(res3.data)
        self.assertEqual(data3['cart']['item_count'], 0)
        self.assertEqual(data3['cart']['total'], 0.0)

    # ---------------------------------------------------------
    # 3. CHECKOUT & ORDER PLACEMENT
    # ---------------------------------------------------------
    def test_checkout_order_placement_and_snapshot(self):
        """Verify successful order placement, unique order code, and item snapshot."""
        # Add item to cart first
        self.client.post('/api/cart/add', data=json.dumps({'item_id': 1, 'quantity': 1}), content_type='application/json')

        checkout_data = {
            'name': 'Aarav Mehta',
            'phone': '9876543210',
            'address': 'Penthouse 10A, Cyber Heights, Sector 62',
            'payment_method': 'Cash on Delivery',
            'special_instructions': 'Call before arrival'
        }
        res = self.client.post('/api/checkout', data=json.dumps(checkout_data), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        order_code = data['order_code']
        self.assertTrue(order_code.startswith('ORD-'))

        # Verify order in database
        order = query_db("SELECT * FROM orders WHERE order_code = ?", (order_code,), one=True)
        self.assertIsNotNone(order)
        self.assertEqual(order['user_name'], 'Aarav Mehta')
        self.assertEqual(order['status'], 'Pending')

        # Verify historical snapshot in order_items
        order_items = query_db("SELECT * FROM order_items WHERE order_id = ?", (order['id'],))
        self.assertEqual(len(order_items), 1)
        self.assertEqual(order_items[0]['item_name'], 'Paneer Tikka')
        self.assertEqual(order_items[0]['item_price'], 240.0)

    def test_checkout_invalid_inputs(self):
        """Verify invalid checkout requests fail with clear error messages."""
        # 1. Empty cart checkout
        res = self.client.post('/api/checkout', 
                               data=json.dumps({'name': 'John', 'phone': '9876543210', 'address': '123 Street'}),
                               content_type='application/json')
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertIn("cart is empty", data['error'].lower())

        # 2. Invalid phone number (less than 10 digits)
        self.client.post('/api/cart/add', data=json.dumps({'item_id': 1, 'quantity': 1}), content_type='application/json')
        res2 = self.client.post('/api/checkout', 
                                data=json.dumps({'name': 'John', 'phone': '12345', 'address': 'Valid Address 123'}),
                                content_type='application/json')
        self.assertEqual(res2.status_code, 400)
        self.assertIn("10-digit phone number", json.loads(res2.data)['error'].lower())

    # ---------------------------------------------------------
    # 4. ORDER TRACKING & CANCELLATION RULES
    # ---------------------------------------------------------
    def test_order_tracking(self):
        """Verify tracking valid and non-existent orders."""
        res = self.client.get('/api/track/ORD-20261028-101')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['order']['order_code'], 'ORD-20261028-101')

        res_404 = self.client.get('/api/track/ORD-INVALID-999')
        self.assertEqual(res_404.status_code, 404)

    def test_order_cancellation_rules(self):
        """Verify cancellation rules: Pending orders can be cancelled, Delivered cannot."""
        # ORD-20261028-101 is Pending -> can be cancelled
        res = self.client.post('/api/order/cancel', 
                               data=json.dumps({'order_code': 'ORD-20261028-101'}),
                               content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(json.loads(res.data)['success'])

        # ORD-20261028-103 is Delivered -> cannot be cancelled
        res_fail = self.client.post('/api/order/cancel', 
                                    data=json.dumps({'order_code': 'ORD-20261028-103'}),
                                    content_type='application/json')
        self.assertEqual(res_fail.status_code, 400)
        self.assertIn("cannot be cancelled", json.loads(res_fail.data)['error'].lower())

    # ---------------------------------------------------------
    # 5. NLP INTENT RECOGNITION & ENTITY EXTRACTION
    # ---------------------------------------------------------
    def test_nlp_intent_recognition(self):
        """Verify ML intent classification across primary customer intents."""
        test_phrases = [
            ("Hello there", "greeting"),
            ("Show me the food menu", "show_menu"),
            ("What is the price of pizza", "ask_price"),
            ("Recommend something under 300 rupees", "recommend_food"),
            ("Do you have vegetarian food", "dietary_preference"),
            ("Track my order", "track_order"),
            ("Help me use this bot", "help"),
            ("Goodbye", "goodbye")
        ]
        for phrase, expected_intent in test_phrases:
            intent, conf = self.classifier.predict(phrase)
            self.assertEqual(intent, expected_intent, f"Failed for phrase '{phrase}': got {intent}")

    def test_nlp_entity_extraction(self):
        """Verify entity extraction for food names, quantities, and budget."""
        # Quantity
        self.assertEqual(EntityExtractor.extract_quantity("I want two burgers"), 2)
        self.assertEqual(EntityExtractor.extract_quantity("Add 3 pizzas"), 3)
        self.assertEqual(EntityExtractor.extract_quantity("One cold coffee"), 1)

        # Budget
        self.assertEqual(EntityExtractor.extract_budget("Recommend food under 300 rupees"), 300.0)
        self.assertEqual(EntityExtractor.extract_budget("budget below 250 rs"), 250.0)

        # Food item matching
        item, score = EntityExtractor.match_food_item("Add one paneer pizza to my cart")
        self.assertIsNotNone(item)
        self.assertIn("Pizza", item['name'])

    def test_chatbot_unknown_intent_fallback(self):
        """Verify meaningless messages trigger fallback response."""
        res = self.client.post('/api/chatbot',
                               data=json.dumps({'message': 'asdlkjf zxcvbnm qwe123456'}),
                               content_type='application/json')
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIn(data['intent'], ['unknown_intent', 'help'])
        self.assertIn("I'm not quite sure", data['reply'])

    # ---------------------------------------------------------
    # 6. SMART FOOD RECOMMENDATION ENGINE
    # ---------------------------------------------------------
    def test_recommendation_engine(self):
        """Verify budget filter, veg filter, and never recommending unavailable items."""
        # Budget filter
        budget_recs = RecommendationEngine.get_recommendations(budget=150.0)
        self.assertTrue(all(r['price'] <= 150.0 for r in budget_recs))

        # Veg filter
        veg_recs = RecommendationEngine.get_recommendations(is_veg=1)
        self.assertTrue(all(r['is_veg'] == 1 for r in veg_recs))

        # Check that unavailable item (Grilled Club Sandwich, is_available=0) is NEVER recommended
        all_recs = RecommendationEngine.get_recommendations(limit=25)
        names = [r['name'] for r in all_recs]
        self.assertNotIn("Grilled Club Sandwich", names)

    # ---------------------------------------------------------
    # 7. ADMIN AUTHENTICATION & MANAGEMENT (CRUD)
    # ---------------------------------------------------------
    def test_admin_authorization_protection(self):
        """Verify protected admin routes require login."""
        # Unauthenticated request to /admin/dashboard redirects to login
        res = self.client.get('/admin/dashboard')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/admin/login', res.headers['Location'])

        # Unauthenticated request to /api/admin/orders returns 401
        res_api = self.client.get('/api/admin/analytics')
        self.assertEqual(res_api.status_code, 401)

    def test_admin_login_and_order_status_update(self):
        """Verify valid admin login and order status update."""
        # 1. Login with demo credentials
        res = self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'})
        self.assertEqual(res.status_code, 302)

        # 2. Update order status to 'Preparing'
        res_update = self.client.post('/api/admin/orders/2/status',
                                      data=json.dumps({'status': 'Preparing'}),
                                      content_type='application/json')
        self.assertEqual(res_update.status_code, 200)
        self.assertTrue(json.loads(res_update.data)['success'])

        order = query_db("SELECT status FROM orders WHERE id = 2", one=True)
        self.assertEqual(order['status'], 'Preparing')

    def test_admin_menu_crud(self):
        """Verify admin can add, edit, toggle availability, and delete a menu item."""
        # Log in first
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'})

        # 1. Add new dish
        new_dish = {
            'name': 'Test Garlic Breadsticks',
            'category_id': 4,
            'price': 140.0,
            'is_veg': 1,
            'is_available': 1,
            'description': 'Crispy golden baked breadsticks',
            'image_url': 'test.jpg'
        }
        res_add = self.client.post('/api/admin/menu/add', data=json.dumps(new_dish), content_type='application/json')
        self.assertEqual(res_add.status_code, 200)
        item_id = json.loads(res_add.data)['id']

        # 2. Toggle availability
        res_toggle = self.client.post(f'/api/admin/menu/{item_id}/toggle-availability')
        self.assertEqual(res_toggle.status_code, 200)
        self.assertEqual(json.loads(res_toggle.data)['is_available'], 0)

        # 3. Edit dish price
        new_dish['price'] = 160.0
        res_edit = self.client.post(f'/api/admin/menu/{item_id}/edit', data=json.dumps(new_dish), content_type='application/json')
        self.assertEqual(res_edit.status_code, 200)

        # 4. Delete dish
        res_del = self.client.post(f'/api/admin/menu/{item_id}/delete')
        self.assertEqual(res_del.status_code, 200)

        # Verify deleted
        deleted_item = query_db("SELECT * FROM menu_items WHERE id = ?", (item_id,), one=True)
        self.assertIsNone(deleted_item)

if __name__ == '__main__':
    unittest.main()
