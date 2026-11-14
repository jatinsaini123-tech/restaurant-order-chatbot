# Smart Chatbot for Restaurant Order Automation Using NLP and Intent Recognition

An intelligent, full-stack, AI-powered restaurant web application built with **Python Flask**, **SQLite**, **scikit-learn**, and **Bootstrap 5**. The system enables customers to explore the menu, ask questions, get budget-friendly recommendations, place orders through natural language, and track delivery status, with real-time shopping cart synchronization and an administrative management dashboard.

---

## 🌟 Key Features

### 1. Customer Ordering Portal
- **Modern Responsive UI**: Clean restaurant branding ("SpiceCraft Bistro"), animated dish cards, and dietary badges (🟢 Veg / 🔴 Non-Veg).
- **Interactive Menu**: Instant search bar, category tabs, and veg/non-veg toggle filters.
- **Cart & Bill Calculation**: Automatic subtotal, 5% restaurant GST, and total calculation with quantity steppers.
- **Checkout & Snapshot Storage**: Form validation (name, 10-digit mobile, address) with historical price snapshots in SQLite.
- **Live Order Tracking**: Visual 6-stage delivery timeline (`Pending` ➔ `Confirmed` ➔ `Preparing` ➔ `Ready` ➔ `Out for Delivery` ➔ `Delivered`) and order cancellation rules.

### 2. NLP AI Chatbot (Genuine Scikit-Learn ML)
- **16 Intent Classifiers**: Greeting, Show menu, Search food, Ask price, Add to cart, Remove from cart, Update quantity, Recommend food, Dietary preference, Check cart, Checkout, Track order, Cancel order, Help, Goodbye, and Unknown intent fallback.
- **Entity Extraction**: Fuzzy and token-overlap food item matching against the live database, number extraction (e.g., "two", "3"), budget parsing ("under 300 rupees"), and order code extraction ("ORD-20261028-101").
- **Live Cart Mutation**: The chatbot directly adds, removes, or modifies items in the customer's session cart in real time without refreshing the page!

### 3. Smart Food Recommendation Engine
- **Budget-Aware**: Filters dishes under user-specified price thresholds (e.g., under ₹150, ₹250, ₹300).
- **Dietary Filter**: Pure vegetarian vs non-vegetarian recommendations.
- **Explainable AI**: Accompanies each recommendation with clear rationales (e.g., "Customer favorite (4.9★)", "Fits your ₹300 budget").
- **Availability Enforcement**: Strictly excludes out-of-stock / unavailable dishes.

### 4. Admin Management Dashboard
- **Secure Authentication**: Hashed password verification (`Werkzeug PBKDF2/SHA256`).
- **Real-Time KPIs**: Total orders, gross revenue, pending orders, and menu count.
- **Interactive Analytics**: Chart.js charts showing revenue by category and volume by order status.
- **Order Management**: Search, filter, and update status dropdowns with instant save.
- **Menu Items CRUD**: Add dishes, edit prices, delete items, and toggle instant "In Stock" / "Sold Out" switches.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (Vanilla ES6+), Bootstrap 5.3, Bootstrap Icons |
| **Backend** | Python 3.10+, Flask 3.1+ |
| **Database** | SQLite3 (parameterized queries, relational foreign keys, historical snapshots) |
| **AI / NLP** | scikit-learn (TF-IDF Vectorizer + Logistic Regression, N-grams), difflib |
| **Charts** | Chart.js 4.4 |
| **Testing** | Python `unittest` test suite |

---

## 📂 Project Structure

```text
semester project 7th/
│
├── app.py                     # Main Flask web application, API routes, and admin portal
├── database.py                # SQLite connection helpers, schema definitions, and transactions
├── init_db.py                 # Database initialization and sample seed data script
├── chatbot_nlp.py             # Scikit-learn TF-IDF & Logistic Regression NLP pipeline
├── chatbot_service.py         # Conversational dialogue controller & cart synchronizer
├── recommendation.py          # Smart budget and dietary recommendation engine
├── requirements.txt           # Project dependencies
├── restaurant.db              # SQLite relational database (auto-generated)
├── intent_model.joblib        # Serialized ML intent classification model
├── README.md                  # Setup commands, demo credentials, and instructions
├── DOCUMENTATION.md           # Comprehensive 17-section academic project report
│
├── static/
│   ├── css/
│   │   └── style.css          # Restaurant theme, floating chatbot styles & animations
│   ├── js/
│   │   ├── cart.js            # Menu rendering, cart state management & checkout validation
│   │   ├── chatbot.js         # Chatbot interactive floating widget & quick replies
│   │   └── admin.js           # Admin Chart.js charts, order status AJAX & menu CRUD
│   └── images/
│       ├── food-placeholder.svg # Local vector fallback image for dishes
│       └── hero-fallback.svg    # Local vector fallback for hero banner
│
├── templates/
│   ├── base.html              # Base master template (navbar, cart drawer, chatbot FAB)
│   ├── index.html             # Customer homepage, food grid, recommendation showcase
│   ├── order_success.html     # Order confirmation invoice & tracking button
│   ├── track.html             # Live delivery progress timeline & order cancellation
│   ├── admin_login.html       # Secure admin login form
│   ├── admin_dashboard.html   # Admin metrics, Chart.js analytics & menu CRUD
│   └── error.html             # User-friendly 404 & 500 error display
│
└── tests/
    └── test_app.py            # Automated test suite (16 test cases, 100% pass rate)
```

---

## 🚀 Quick Setup & Installation

### Prerequisites
- Python 3.10 or higher installed on your machine.
- Web browser (Chrome, Firefox, Edge, Safari).

### Step 1: Clone or Navigate to the Workspace
```powershell
cd "c:\Users\DELL\OneDrive\Desktop\semester project 7th"
```

### Step 2: Install Required Python Packages
```powershell
pip install -r requirements.txt
```
*(Packages installed: `flask`, `werkzeug`, `scikit-learn`, `numpy`, `joblib`)*

### Step 3: Initialize and Seed the Database
```powershell
python init_db.py
```
*This command creates `restaurant.db` with 6 categories, 23 menu dishes, 110 chatbot intent training samples, sample orders, and the default admin account.*

### Step 4: Run the Application
```powershell
python app.py
```
You will see output indicating the server is running:
```text
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
 * Restarting with stat
 * Debugger is active!
```

---

## 🌐 Accessing the Application

1. **Customer Ordering Website**:
   Open your browser and navigate to:  
   👉 **`http://127.0.0.1:5000/`**

2. **Live Order Tracking**:  
   👉 **`http://127.0.0.1:5000/track`**  
   *(Test tracking with sample order code: `ORD-20261028-101`)*

3. **Admin Dashboard Portal**:  
   👉 **`http://127.0.0.1:5000/admin/login`**

---

## 🔑 Demo Admin Credentials

| Parameter | Value |
| :--- | :--- |
| **Username** | `admin` |
| **Password** | `admin123` |
| **Role** | `superadmin` |
| **Security** | Hashed via `werkzeug.security.generate_password_hash` |

### How to Change Admin Password
To change the admin password for production or personal use, run this Python one-liner:
```powershell
python -c "from werkzeug.security import generate_password_hash; from database import execute_db; execute_db('UPDATE admin_users SET password_hash = ? WHERE username = ?', (generate_password_hash('YourNewSecurePassword123'), 'admin')); print('Admin password updated successfully!')"
```

---

## 🧪 Running the Automated Test Suite

The project includes an automated test suite verifying all 13 core requirements:
```powershell
python -m unittest tests/test_app.py
```
Expected output:
```text
................
----------------------------------------------------------------------
Ran 16 tests in 1.092s

OK
```

---

## 💬 Sample Chatbot Test Prompts

Open the floating chatbot widget at the bottom right of the page and try these queries:
1. **Greeting**: `"Hello"` or `"Hi there"`
2. **Show Menu**: `"Show me the menu"` or `"What can I order?"`
3. **Food Search**: `"Do you have burger?"` or `"Search for pasta"`
4. **Price Check**: `"What is the price of pizza?"` or `"How much is Garlic Naan?"`
5. **Add to Cart**: `"Add two burgers"` or `"Add one paneer pizza to my cart"`
6. **Cart Review**: `"What is in my cart?"` or `"What is my total bill?"`
7. **Budget Recommendation**: `"Recommend something under 300 rupees"`
8. **Dietary Filter**: `"Do you have vegetarian food?"` or `"Show pure veg dishes"`
9. **Checkout Prompt**: `"Checkout"` or `"I want to place my order"`
10. **Order Tracking**: `"Track order ORD-20261028-101"`
11. **Order Cancellation**: `"Cancel order ORD-20261028-101"`
12. **Help**: `"Help me"` or `"What can you do?"`

---

## 🔧 Troubleshooting Guide

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `Address already in use (Port 5000)` | Another process is occupying port 5000 | In `app.py`, change `app.run(port=5000)` to `port=5001` or run `netstat -ano \| findstr :5000` to terminate the lingering process. |
| `Permission denied` on SQLite file | Database locked by another tool or process | Close any SQLite browser software and restart `python app.py`. |
| Chatbot model training warning | Model retraining triggered | The system auto-heals and trains a fresh model from `bot_intent_data` in less than 1 second. |
| External food images slow to load | Offline or slow internet connection | Built-in SVG vector fallbacks (`static/images/food-placeholder.svg`) ensure the UI remains functional without internet. |
