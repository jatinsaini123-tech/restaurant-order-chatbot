"""
chatbot_nlp.py - NLP Intent Classification and Entity Extraction Engine
Smart Chatbot for Restaurant Order Automation

Uses scikit-learn (TF-IDF Vectorizer + Logistic Regression) for genuine ML intent classification,
paired with fuzzy/token-overlap entity extraction for menu items, quantities, budgets, and order codes.
"""

import re
import os
import joblib
import unicodedata
from difflib import SequenceMatcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from database import query_db, DB_PATH

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'intent_model.joblib')

# English number words to integer mapping
WORD_TO_NUM = {
    'one': 1, 'a': 1, 'an': 1, 'single': 1,
    'two': 2, 'couple': 2, 'double': 2,
    'three': 3, 'triple': 3,
    'four': 4,
    'five': 5,
    'six': 6,
    'seven': 7,
    'eight': 8,
    'nine': 9,
    'ten': 10
}

def preprocess_text(text: str) -> str:
    """Cleans, normalizes, and strips punctuation from input text."""
    if not text:
        return ""
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    # Lowercase
    text = text.lower()
    # Replace currency symbols
    text = text.replace('₹', ' rupees ').replace('rs.', ' rupees ').replace('rs', ' rupees ')
    # Keep alphanumeric, spaces, and hyphens (for order codes like ORD-101)
    text = re.sub(r'[^a-z0-9\s\-]', ' ', text)
    # Collapse multiple whitespaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

class IntentClassifier:
    """
    Genuine ML Intent Classifier using TF-IDF and Logistic Regression.
    Trained on restaurant ordering utterances.
    """
    def __init__(self, confidence_threshold=0.20):
        self.confidence_threshold = confidence_threshold
        self.pipeline = None
        self.is_trained = False
        self._load_or_train()

    def train(self, training_data=None):
        """Trains the ML model using intent-phrase pairs from DB or fallback corpus."""
        if not training_data:
            rows = query_db("SELECT intent, user_phrase FROM bot_intent_data")
            if rows:
                training_data = [(r['intent'], r['user_phrase']) for r in rows]
        
        if not training_data:
            raise ValueError("No training data available to train intent classifier.")

        X = [preprocess_text(phrase) for _, phrase in training_data]
        y = [intent for intent, _ in training_data]

        # Pipeline with n-gram TF-IDF vectorizer and calibrated Logistic Regression
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
            ('clf', LogisticRegression(C=3.0, max_iter=1000, random_state=42))
        ])

        self.pipeline.fit(X, y)
        self.is_trained = True

        # Save model for fast future restarts
        try:
            joblib.dump(self.pipeline, MODEL_PATH)
        except Exception as e:
            print(f"Notice: Could not save model to disk ({e}), running in-memory.")

    def _load_or_train(self):
        """Loads serialized model if available, else trains a fresh one."""
        if os.path.exists(MODEL_PATH):
            try:
                self.pipeline = joblib.load(MODEL_PATH)
                self.is_trained = True
                return
            except Exception:
                pass
        self.train()

    def predict(self, text: str):
        """
        Predicts intent and confidence score for a given customer message.
        Returns: (intent, confidence_score)
        """
        clean_text = preprocess_text(text)
        if not clean_text or not self.is_trained:
            return "unknown_intent", 0.0

        probs = self.pipeline.predict_proba([clean_text])[0]
        max_idx = probs.argmax()
        confidence = float(probs[max_idx])
        predicted_intent = str(self.pipeline.classes_[max_idx])

        # If confidence is below threshold, categorize as unknown_intent
        if confidence < self.confidence_threshold:
            return "unknown_intent", round(confidence, 3)

        return predicted_intent, round(confidence, 3)

def singularize(word: str) -> str:
    """Helper to convert plural words to singular form for accurate food matching."""
    w = word.lower()
    if w.endswith('ies'):
        return w[:-3] + 'y'
    elif w.endswith('es') and not w.endswith('ees'):
        return w[:-2]
    elif w.endswith('s') and not w.endswith('ss'):
        return w[:-1]
    return w

class EntityExtractor:
    """
    Extracts structured entities (food items, quantities, budget, dietary tags, order IDs)
    from natural language sentences and matches them against the live database menu.
    """

    @staticmethod
    def extract_quantity(text: str) -> int:
        """
        Extracts quantity from text. Supports numerals ('2', '5') and word numerals ('two', 'three').
        Defaults to 1 if no quantity is mentioned.
        """
        text_lower = text.lower()

        # 1. Regex check for digits before or after item context (e.g. '2 burgers', 'quantity 3', 'make it 4')
        digit_match = re.search(r'\b(\d+)\b', text_lower)
        if digit_match:
            qty = int(digit_match.group(1))
            # If the digit is not a budget/order id (quantities are usually 1 to 20)
            if 1 <= qty <= 20:
                return qty

        # 2. Check for word numerals
        for word, val in WORD_TO_NUM.items():
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, text_lower):
                return val

        return 1

    @staticmethod
    def extract_budget(text: str):
        """
        Extracts budget threshold from expressions like 'under 300', 'below 250 rs', 'less than 500'.
        Returns float budget or None.
        """
        patterns = [
            r'(?:under|below|less\s+than|within|budget(?:\s+of)?|max|maximum)\s*(?:rs\.?|rupees|inr|₹)?\s*(\d+)',
            r'(\d+)\s*(?:rs\.?|rupees|inr|₹)?\s*(?:budget|or\s+less)',
            r'around\s*(\d+)\s*(?:rupees|rs)?'
        ]
        for pat in patterns:
            match = re.search(pat, text.lower())
            if match:
                val = float(match.group(1))
                if val >= 30:  # Reasonable minimum price
                    return val
        return None

    @staticmethod
    def extract_dietary_preference(text: str):
        """
        Detects if user asks specifically for 'veg' or 'non-veg'.
        Returns: 1 for veg, 0 for non-veg, or None if unspecified.
        """
        clean = text.lower()
        if re.search(r'\b(non[-\s]?veg|chicken|meat|egg|fish|mutton)\b', clean):
            return 0  # Non-veg
        if re.search(r'\b(pure[-\s]?veg|vegetarian|only\s+veg|veg)\b', clean):
            return 1  # Veg
        return None

    @staticmethod
    def extract_order_code(text: str):
        """
        Extracts order code from text like 'ORD-20261028-101' or 'ORD-101' or plain digits.
        """
        # Exact standard format: ORD-YYYYMMDD-XXX or ORD-XXXX
        match = re.search(r'\bORD-[A-Za-z0-9\-]+\b', text, re.IGNORECASE)
        if match:
            return match.group(0).upper()
        # Fallback: standalone numeric order id like "order 101"
        match_num = re.search(r'\border\s*(?:id|number|no\.?)?\s*#?\s*(\d+)\b', text, re.IGNORECASE)
        if match_num:
            return f"ORD-{match_num.group(1)}"
        return None

    @staticmethod
    def match_food_item(text: str, menu_items=None):
        """
        Matches customer utterance against the actual database menu items.
        Returns: (matched_menu_item_dict, match_score) or (None, 0.0)
        Never invents an item not in the database.
        """
        if menu_items is None:
            menu_items = query_db("SELECT * FROM menu_items")

        if not menu_items:
            return None, 0.0

        clean_text = preprocess_text(text)
        best_item = None
        best_score = 0.0

        # Stop words to ignore during item matching
        ignore_words = {
            'add', 'order', 'please', 'put', 'in', 'to', 'my', 'cart', 'bag',
            'remove', 'delete', 'take', 'out', 'want', 'i', 'can', 'you', 'give',
            'me', 'show', 'price', 'of', 'how', 'much', 'is', 'the', 'what',
            'cost', 'rate', 'one', 'two', 'three', 'four', 'five', 'a', 'an',
            'some', 'dish', 'item', 'food', 'have'
        }

        # Tokenize query and apply singularization
        query_words = [w for w in clean_text.split() if w not in ignore_words and not w.isdigit()]
        query_singular = [singularize(w) for w in query_words]
        query_str = " ".join(query_singular)

        for item in menu_items:
            clean_item_name = preprocess_text(item['name'])
            item_words = clean_item_name.split()
            item_singular = [singularize(w) for w in item_words]
            item_str = " ".join(item_singular)

            # 1. Exact full name match
            if clean_item_name in clean_text or item_str in query_str:
                score = 1.0 + (len(clean_item_name) / 100.0)
                if score > best_score:
                    best_score = score
                    best_item = item
                continue

            # 2. Token overlap and singular root matching
            matched_tokens = []
            for qw in query_singular:
                if qw in item_singular:
                    matched_tokens.append(qw)
                elif any(qw in iw or iw in qw for iw in item_singular if len(iw) >= 3):
                    matched_tokens.append(qw)

            if matched_tokens:
                # Higher score if multiple tokens matched or item name is fully covered
                token_ratio = len(matched_tokens) / float(max(len(query_singular), 1))
                item_cover = len(matched_tokens) / float(len(item_singular))
                seq_score = SequenceMatcher(None, query_str, item_str).ratio()

                score = (token_ratio * 0.45) + (item_cover * 0.35) + (seq_score * 0.20)
                # Slight tie-breaker for items with higher ratings
                score += (float(item.get('rating', 4.0)) / 100.0)

                if score > best_score and score >= 0.38:
                    best_score = score
                    best_item = item

        final_score = min(best_score, 1.0)
        if final_score >= 0.38:
            return best_item, round(final_score, 2)

        return None, 0.0

# Singleton instances for reuse
classifier_instance = None

def get_intent_classifier():
    """Returns singleton IntentClassifier instance."""
    global classifier_instance
    if classifier_instance is None:
        classifier_instance = IntentClassifier()
    return classifier_instance
