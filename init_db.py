"""
init_db.py - Database Initialization and Seeding Script
Smart Chatbot for Restaurant Order Automation
"""

import os
import sqlite3
from werkzeug.security import generate_password_hash
from database import DB_PATH, init_schema, execute_insert, execute_db

SAMPLE_CATEGORIES = [
    ("Starters", "starters", "Appetizing vegetarian and non-vegetarian appetizers", 1),
    ("Main Course", "main-course", "Hearty curries, paneer specials, and traditional breads", 2),
    ("Pizza & Pasta", "pizza-pasta", "Stone-baked artisan pizzas and Italian pasta", 3),
    ("Burgers & Fast Food", "burgers-fast-food", "Gourmet burgers, wraps, and crispy sides", 4),
    ("Desserts", "desserts", "Sweet treats, cakes, and authentic delicacies", 5),
    ("Beverages", "beverages", "Refreshing mocktails, coffee, and chilled drinks", 6),
]

SAMPLE_MENU_ITEMS = [
    # Starters (category_id = 1)
    (1, "Paneer Tikka", "Cottage cheese cubes marinated in spiced yogurt and grilled in tandoor", 240.0, 1, 1, "paneer_tikka.jpg", 4.8, 85),
    (1, "Chicken Tikka", "Succulent boneless chicken chunks marinated in tandoori spices", 280.0, 0, 1, "chicken_tikka.jpg", 4.7, 92),
    (1, "Crispy Corn", "Golden sweet corn kernels tossed with peppers, herbs, and spices", 160.0, 1, 1, "crispy_corn.jpg", 4.4, 60),
    (1, "Veg Spring Rolls", "Crispy fried rolls filled with fresh seasonal vegetables and glass noodles", 180.0, 1, 1, "spring_rolls.jpg", 4.3, 55),
    
    # Main Course (category_id = 2)
    (2, "Paneer Butter Masala", "Rich and creamy tomato gravy with tender cottage cheese cubes", 290.0, 1, 1, "paneer_butter_masala.jpg", 4.9, 120),
    (2, "Dal Makhani", "Black lentils slow cooked overnight with butter and dairy cream", 240.0, 1, 1, "dal_makhani.jpg", 4.7, 98),
    (2, "Butter Chicken", "Traditional clay oven chicken in a silky, mildly sweet buttery tomato gravy", 340.0, 0, 1, "butter_chicken.jpg", 4.9, 140),
    (2, "Garlic Naan", "Leavened oven-baked flatbread infused with fresh minced garlic and butter", 60.0, 1, 1, "garlic_naan.jpg", 4.6, 150),

    # Pizza & Pasta (category_id = 3)
    (3, "Paneer Tikka Pizza", "Tandoori spiced paneer cubes, diced red onions, crisp bell peppers, and mozzarella", 320.0, 1, 1, "paneer_pizza.jpg", 4.8, 115),
    (3, "Margherita Pizza", "Classic Italian pizza with tomato passata, fresh basil, and mozzarella", 260.0, 1, 1, "margherita.jpg", 4.5, 75),
    (3, "Farmhouse Veggie Pizza", "Loaded with onions, capsicum, mushrooms, sweetcorn, and black olives", 310.0, 1, 1, "farmhouse.jpg", 4.8, 110),
    (3, "Chicken Pepperoni Pizza", "Signature pizza topped with spicy sliced chicken pepperoni and herbs", 360.0, 0, 1, "pepperoni.jpg", 4.7, 95),
    (3, "Creamy Alfredo Pasta", "Fettuccine pasta in rich parmesan cheese and garlic cream sauce", 250.0, 1, 1, "alfredo.jpg", 4.6, 68),

    # Burgers & Fast Food (category_id = 4)
    (4, "Veggie Supreme Burger", "Crispy spiced potato & vegetable patty with cheddar cheese and fresh lettuce", 140.0, 1, 1, "veg_burger.jpg", 4.4, 88),
    (4, "Crispy Chicken Burger", "Fried chicken breast filet coated in crispy seasoning with spicy mayo", 190.0, 0, 1, "chicken_burger.jpg", 4.7, 105),
    (4, "French Fries", "Golden salted crispy potato fries served with tomato ketchup", 110.0, 1, 1, "fries.jpg", 4.5, 130),
    (4, "Peri Peri Fries", "Crispy fries dusted with our fiery signature peri peri spice blend", 130.0, 1, 1, "peri_fries.jpg", 4.6, 115),
    (4, "Grilled Club Sandwich", "Tri-layered toasted bread with veggies, cheese slice, and tangy sauce (Temporarily Out of Stock)", 150.0, 1, 0, "sandwich.jpg", 4.2, 35),

    # Desserts (category_id = 5)
    (5, "Chocolate Lava Cake", "Warm chocolate cake with a molten, oozing dark chocolate center", 150.0, 1, 1, "lava_cake.jpg", 4.9, 135),
    (5, "Gulab Jamun", "Two warm soft milk dumplings soaked in fragrant cardamom sugar syrup", 90.0, 1, 1, "gulab_jamun.jpg", 4.7, 80),

    # Beverages (category_id = 6)
    (6, "Cold Coffee", "Chilled blended espresso with creamy milk, vanilla ice cream, and chocolate drizzle", 120.0, 1, 1, "cold_coffee.jpg", 4.6, 90),
    (6, "Virgin Mojito", "Muddled fresh mint leaves, lime wedges, simple syrup, and sparkling soda", 130.0, 1, 1, "mojito.jpg", 4.5, 85),
    (6, "Fresh Lime Soda", "Sweet and salted refreshing lime water topped with chilled club soda", 80.0, 1, 1, "lime_soda.jpg", 4.4, 70),
]

# Intent training phrases for NLP Intent Recognition
INTENT_TRAINING_DATA = [
    # greeting
    ("greeting", "hi"),
    ("greeting", "hello"),
    ("greeting", "hey"),
    ("greeting", "good morning"),
    ("greeting", "good evening"),
    ("greeting", "hey there"),
    ("greeting", "namaste"),
    ("greeting", "is anyone there"),
    ("greeting", "start"),

    # show_menu
    ("show_menu", "show me the menu"),
    ("show_menu", "what is on the menu"),
    ("show_menu", "view food menu"),
    ("show_menu", "open menu"),
    ("show_menu", "list all dishes"),
    ("show_menu", "what can i order"),
    ("show_menu", "show food options"),
    ("show_menu", "display menu"),
    ("show_menu", "food items list"),

    # search_food
    ("search_food", "do you have pizza"),
    ("search_food", "do you have burger"),
    ("search_food", "find pasta"),
    ("search_food", "search for paneer"),
    ("search_food", "is chicken available"),
    ("search_food", "look for desserts"),
    ("search_food", "do you serve fries"),
    ("search_food", "check if you have chocolate lava cake"),

    # ask_price
    ("ask_price", "what is the price of pizza"),
    ("ask_price", "how much is the burger"),
    ("ask_price", "what does paneer tikka cost"),
    ("ask_price", "price of butter chicken"),
    ("ask_price", "how much do fries cost"),
    ("ask_price", "rate of cold coffee"),
    ("ask_price", "cost of margherita pizza"),
    ("ask_price", "tell me price of garlic naan"),

    # add_to_cart
    ("add_to_cart", "add one paneer pizza to my cart"),
    ("add_to_cart", "i want to order two burgers"),
    ("add_to_cart", "add 1 butter chicken to cart"),
    ("add_to_cart", "add two garlic naan"),
    ("add_to_cart", "order one french fries"),
    ("add_to_cart", "put 3 cold coffee in my bag"),
    ("add_to_cart", "add chocolate lava cake"),
    ("add_to_cart", "add one margherita pizza"),
    ("add_to_cart", "order 2 chicken tikka"),
    ("add_to_cart", "add dal makhani to my order"),

    # remove_from_cart
    ("remove_from_cart", "remove one burger"),
    ("remove_from_cart", "delete pizza from cart"),
    ("remove_from_cart", "remove fries from my cart"),
    ("remove_from_cart", "delete cold coffee"),
    ("remove_from_cart", "take out paneer tikka"),
    ("remove_from_cart", "remove garlic naan"),
    ("remove_from_cart", "drop item from cart"),

    # update_quantity
    ("update_quantity", "change burger quantity to 3"),
    ("update_quantity", "update pizza count to 2"),
    ("update_quantity", "make fries 4"),
    ("update_quantity", "increase garlic naan to 5"),
    ("update_quantity", "change quantity of cold coffee to 1"),
    ("update_quantity", "modify quantity of butter chicken"),

    # recommend_food
    ("recommend_food", "recommend something under 300 rupees"),
    ("recommend_food", "recommend food under 200"),
    ("recommend_food", "what is your best seller"),
    ("recommend_food", "suggest something good to eat"),
    ("recommend_food", "what do you recommend"),
    ("recommend_food", "popular dishes"),
    ("recommend_food", "what should i try today"),
    ("recommend_food", "chef special recommendation"),

    # dietary_preference
    ("dietary_preference", "do you have vegetarian food"),
    ("dietary_preference", "show pure veg items"),
    ("dietary_preference", "only vegetarian please"),
    ("dietary_preference", "do you serve non veg"),
    ("dietary_preference", "show non-vegetarian dishes"),
    ("dietary_preference", "is there chicken available"),
    ("dietary_preference", "veg options"),

    # check_cart
    ("check_cart", "what is in my cart"),
    ("check_cart", "show my cart"),
    ("check_cart", "view cart"),
    ("check_cart", "check my order items"),
    ("check_cart", "what is my total bill"),
    ("check_cart", "how much is my current total"),
    ("check_cart", "view my bag"),

    # checkout
    ("checkout", "checkout"),
    ("checkout", "i want to place my order"),
    ("checkout", "finalize my order"),
    ("checkout", "proceed to checkout"),
    ("checkout", "place the order now"),
    ("checkout", "confirm order and pay"),
    ("checkout", "complete my purchase"),

    # track_order
    ("track_order", "track my order"),
    ("track_order", "where is my food"),
    ("track_order", "check order status"),
    ("track_order", "order tracking"),
    ("track_order", "track order ORD-20261028-101"),
    ("track_order", "is my food ready"),
    ("track_order", "status of my delivery"),

    # cancel_order
    ("cancel_order", "cancel my order"),
    ("cancel_order", "i want to cancel order"),
    ("cancel_order", "please cancel order ORD-20261028-101"),
    ("cancel_order", "stop my order"),
    ("cancel_order", "abort food delivery"),

    # help
    ("help", "help"),
    ("help", "help me"),
    ("help", "how do i use this chatbot"),
    ("help", "what can you do"),
    ("help", "bot instructions"),
    ("help", "commands list"),

    # goodbye
    ("goodbye", "bye"),
    ("goodbye", "goodbye"),
    ("goodbye", "see you later"),
    ("goodbye", "thank you bye"),
    ("goodbye", "exit chat"),
    ("goodbye", "have a good day"),
]

def seed_database(db_file=None):
    """Seeds the database with initial categories, menu items, admin, and training data."""
    print("Initializing database schema...")
    init_schema(db_file)
    
    conn = sqlite3.connect(db_file or DB_PATH)
    cursor = conn.cursor()

    # 1. Seed Admin User
    admin_user = cursor.execute("SELECT id FROM admin_users WHERE username = 'admin'").fetchone()
    if not admin_user:
        hashed_pwd = generate_password_hash("admin123")
        cursor.execute(
            "INSERT INTO admin_users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", hashed_pwd, "superadmin")
        )
        print("-> Default admin user created: admin / admin123")

    # 2. Seed Categories
    for name, slug, desc, order in SAMPLE_CATEGORIES:
        cursor.execute(
            """INSERT OR IGNORE INTO categories (name, slug, description, display_order)
               VALUES (?, ?, ?, ?)""",
            (name, slug, desc, order)
        )
    print(f"-> Seeded {len(SAMPLE_CATEGORIES)} food categories.")

    # 3. Seed Menu Items
    for item in SAMPLE_MENU_ITEMS:
        cat_id, name, desc, price, is_veg, is_avail, img, rating, pop = item
        cursor.execute(
            """INSERT OR IGNORE INTO menu_items 
               (category_id, name, description, price, is_veg, is_available, image_url, rating, popularity_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cat_id, name, desc, price, is_veg, is_avail, img, rating, pop)
        )
    print(f"-> Seeded {len(SAMPLE_MENU_ITEMS)} menu items.")

    # 4. Seed Intent Training Phrases
    cursor.execute("DELETE FROM bot_intent_data")
    for intent, phrase in INTENT_TRAINING_DATA:
        cursor.execute(
            "INSERT INTO bot_intent_data (intent, user_phrase) VALUES (?, ?)",
            (intent, phrase)
        )
    print(f"-> Seeded {len(INTENT_TRAINING_DATA)} chatbot intent training samples.")

    # 5. Seed Sample Orders for Admin Analytics
    existing_orders = cursor.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    if existing_orders == 0:
        sample_orders = [
            ("ORD-20261028-101", "Rahul Sharma", "9876543210", "Flat 402, Sunshine Apartments, MG Road", 480.0, 24.0, 504.0, "Pending", "Cash on Delivery", "Extra spicy please"),
            ("ORD-20261028-102", "Priya Patel", "9812345678", "House 12, Rose Colony, Sector 4", 650.0, 32.5, 682.5, "Preparing", "UPI on Delivery", "Leave at door"),
            ("ORD-20261028-103", "Amit Verma", "9765432109", "Tech Park Building 3, Cyber City", 730.0, 36.5, 766.5, "Delivered", "Card on Delivery", "Ring bell"),
            ("ORD-20261028-104", "Sneha Gupta", "9654321870", "B-14 Green View Enclave", 290.0, 14.5, 304.5, "Out for Delivery", "Cash on Delivery", "Quick delivery requested"),
        ]
        
        for order in sample_orders:
            cursor.execute(
                """INSERT INTO orders (order_code, user_name, user_phone, user_address, subtotal, tax_amount, total_amount, status, payment_method, special_instructions)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                order
            )
            order_id = cursor.lastrowid
            # Seed corresponding order items
            if order[0] == "ORD-20261028-101":
                cursor.execute("INSERT INTO order_items (order_id, menu_item_id, item_name, item_price, quantity, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
                               (order_id, 1, "Paneer Tikka", 240.0, 2, 480.0))
            elif order[0] == "ORD-20261028-102":
                cursor.execute("INSERT INTO order_items (order_id, menu_item_id, item_name, item_price, quantity, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
                               (order_id, 2, "Chicken Tikka", 280.0, 1, 280.0))
                cursor.execute("INSERT INTO order_items (order_id, menu_item_id, item_name, item_price, quantity, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
                               (order_id, 10, "Farmhouse Veggie Pizza", 310.0, 1, 310.0))
                cursor.execute("INSERT INTO order_items (order_id, menu_item_id, item_name, item_price, quantity, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
                               (order_id, 8, "Garlic Naan", 60.0, 1, 60.0))
            elif order[0] == "ORD-20261028-103":
                cursor.execute("INSERT INTO order_items (order_id, menu_item_id, item_name, item_price, quantity, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
                               (order_id, 7, "Butter Chicken", 340.0, 1, 340.0))
                cursor.execute("INSERT INTO order_items (order_id, menu_item_id, item_name, item_price, quantity, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
                               (order_id, 11, "Chicken Pepperoni Pizza", 360.0, 1, 360.0))
                cursor.execute("INSERT INTO order_items (order_id, menu_item_id, item_name, item_price, quantity, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
                               (order_id, 21, "Fresh Lime Soda", 80.0, 1, 80.0))
            elif order[0] == "ORD-20261028-104":
                cursor.execute("INSERT INTO order_items (order_id, menu_item_id, item_name, item_price, quantity, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
                               (order_id, 5, "Paneer Butter Masala", 290.0, 1, 290.0))
        print(f"-> Seeded {len(sample_orders)} sample orders with itemized historical snapshots.")

    conn.commit()
    conn.close()
    print("Database initialization completed successfully!")

if __name__ == "__main__":
    seed_database()
