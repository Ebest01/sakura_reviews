"""
AI Quality Scoring System
Competitive advantage over Loox - intelligent review quality assessment
"""
import re
from textblob import TextBlob

class ReviewQualityScorer:
    """AI-based review quality scoring"""
    
    # Quality keywords indicating detailed, helpful reviews
    QUALITY_KEYWORDS = [
        'quality', 'perfect', 'excellent', 'amazing', 'love', 'recommend',
        'great', 'fantastic', 'wonderful', 'satisfied', 'happy',
        'exactly', 'described', 'fast shipping', 'good price', 'value'
    ]
    
    # Spam/low-quality indicators
    SPAM_KEYWORDS = [
        'click here', 'buy now', 'discount code', 'promo', 'http://', 'https://'
    ]
    
    def calculate_quality_score(self, review_data):
        """
        Calculate comprehensive quality score (0-10)
        Higher score = better quality review
        """
        score = 0
        text = review_data.get('text', '') or review_data.get('body', '')
        
        if not text:
            return 0
        
        text_lower = text.lower()
        
        # 1. Text length and detail (0-3 points)
        text_len = len(text)
        if text_len > 200:
            score += 3
        elif text_len > 100:
            score += 2
        elif text_len > 50:
            score += 1
        
        # 2. Has images (0-2 points)
        images = review_data.get('images', [])
        if images and len(images) > 0:
            score += 2
        
        # 3. High rating (0-2 points)
        rating = review_data.get('rating', 0)
        if rating >= 5:
            score += 2
        elif rating >= 4:
            score += 1
        
        # 4. Verified purchase (0-1 point)
        if review_data.get('verified', False) or review_data.get('verified_purchase', False):
            score += 1
        
        # 5. Quality keywords present (0-2 points)
        keyword_count = sum(1 for keyword in self.QUALITY_KEYWORDS if keyword in text_lower)
        if keyword_count >= 3:
            score += 2
        elif keyword_count >= 1:
            score += 1
        
        # 6. Sentiment analysis (if TextBlob available)
        try:
            sentiment = self._analyze_sentiment(text)
            if sentiment > 0.5:  # Very positive
                score += 1
        except:
            pass
        
        # Penalties for spam
        spam_count = sum(1 for keyword in self.SPAM_KEYWORDS if keyword in text_lower)
        if spam_count > 0:
            score = max(0, score - (spam_count * 2))
        
        # Ensure score is between 0 and 10
        score = max(0, min(10, score))
        
        return round(score, 1)
    
    def _analyze_sentiment(self, text):
        """Analyze sentiment using TextBlob"""
        try:
            blob = TextBlob(text)
            # Polarity ranges from -1 (negative) to 1 (positive)
            return blob.sentiment.polarity
        except:
            # Fallback: simple keyword-based sentiment
            positive_words = ['good', 'great', 'excellent', 'love', 'perfect', 'happy', 'satisfied']
            negative_words = ['bad', 'poor', 'terrible', 'awful', 'disappointed', 'waste']
            
            text_lower = text.lower()
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            
            if positive_count + negative_count == 0:
                return 0
            
            return (positive_count - negative_count) / (positive_count + negative_count)
    
    def is_recommended(self, review_data):
        """Determine if review should be AI-recommended"""
        score = self.calculate_quality_score(review_data)
        return score >= 7
    
    def calculate_sentiment_score(self, text):
        """Calculate sentiment score (0-1 scale)"""
        sentiment = self._analyze_sentiment(text)
        # Convert from -1...1 to 0...1
        return (sentiment + 1) / 2
    
    def enrich_review(self, review_data):
        """Add AI scoring fields to review data"""
        quality_score = self.calculate_quality_score(review_data)
        text = review_data.get('text', '') or review_data.get('body', '')
        
        review_data['quality_score'] = quality_score
        review_data['ai_recommended'] = quality_score >= 7
        
        if text:
            review_data['sentiment_score'] = self.calculate_sentiment_score(text)
        
        return review_data
    
    def filter_best_reviews(self, reviews, limit=None, min_score=7):
        """
        Filter and sort reviews by quality
        Returns top quality reviews
        """
        # Enrich all reviews with scores
        enriched = [self.enrich_review(review.copy()) for review in reviews]
        
        # Filter by minimum score
        filtered = [r for r in enriched if r.get('quality_score', 0) >= min_score]
        
        # Sort by quality score (descending)
        sorted_reviews = sorted(filtered, key=lambda x: x.get('quality_score', 0), reverse=True)
        
        # Apply limit if specified
        if limit:
            return sorted_reviews[:limit]
        
        return sorted_reviews

