"""
recommendation.py - Smart Food Recommendation Engine
Smart Chatbot for Restaurant Order Automation

Provides personalized, budget-conscious, dietary-specific, and popularity-driven
food recommendations with transparent explanations. Never recommends unavailable dishes.
"""

from database import query_db

class RecommendationEngine:
    """
    Intelligent restaurant food recommendation service.
    Combines budget constraints, dietary preferences, and historical popularity.
    """

    @staticmethod
    def get_recommendations(budget=None, is_veg=None, category_id=None, limit=4):
        """
        Generates recommendations based on customer constraints and popularity metrics.
        
        Args:
            budget (float, optional): Maximum item price threshold.
            is_veg (int, optional): 1 for vegetarian, 0 for non-vegetarian, None for all.
            category_id (int, optional): Category ID filter.
            limit (int): Maximum items to return.
            
        Returns:
            list[dict]: Curated list of recommended dishes with explanations.
        """
        # Base query ensures ONLY available dishes are considered
        sql = "SELECT m.*, c.name as category_name FROM menu_items m JOIN categories c ON m.category_id = c.id WHERE m.is_available = 1"
        params = []

        if budget is not None:
            sql += " AND m.price <= ?"
            params.append(float(budget))

        if is_veg is not None:
            sql += " AND m.is_veg = ?"
            params.append(int(is_veg))

        if category_id is not None:
            sql += " AND m.category_id = ?"
            params.append(int(category_id))

        # Sort by popularity_score DESC, rating DESC
        sql += " ORDER BY m.popularity_score DESC, m.rating DESC LIMIT ?"
        params.append(limit)

        items = query_db(sql, tuple(params))
        if not items:
            # Fallback: relax budget slightly if nothing found
            if budget is not None:
                relaxed_sql = "SELECT m.*, c.name as category_name FROM menu_items m JOIN categories c ON m.category_id = c.id WHERE m.is_available = 1"
                relaxed_params = []
                if is_veg is not None:
                    relaxed_sql += " AND m.is_veg = ?"
                    relaxed_params.append(int(is_veg))
                relaxed_sql += " ORDER BY m.price ASC, m.rating DESC LIMIT ?"
                relaxed_params.append(limit)
                items = query_db(relaxed_sql, tuple(relaxed_params))
            else:
                return []

        # Attach explainability labels
        results = []
        for item in items:
            item_dict = dict(item)
            item_dict['explanation'] = RecommendationEngine._generate_explanation(item_dict, budget, is_veg)
            results.append(item_dict)

        return results

    @staticmethod
    def _generate_explanation(item, budget=None, is_veg=None):
        """Generates a human-friendly rationale for why this item was recommended."""
        reasons = []

        if budget is not None and item['price'] <= budget:
            reasons.append(f"Fits your ₹{int(budget)} budget (₹{int(item['price'])})")

        if item['rating'] >= 4.7:
            reasons.append(f"Customer favorite ({item['rating']}★)")
        elif item['popularity_score'] >= 100:
            reasons.append("Most frequently ordered dish")

        if is_veg == 1:
            reasons.append("100% Pure Vegetarian")
        elif is_veg == 0:
            reasons.append("Signature Non-Veg Specialty")

        if not reasons:
            reasons.append(f"Chef's highlight in {item.get('category_name', 'Menu')}")

        return " • ".join(reasons)

    @staticmethod
    def get_popular_items(limit=6):
        """Returns top popular dishes across the entire menu."""
        return RecommendationEngine.get_recommendations(limit=limit)

    @staticmethod
    def get_veg_specials(limit=4):
        """Returns top vegetarian dishes."""
        return RecommendationEngine.get_recommendations(is_veg=1, limit=limit)
