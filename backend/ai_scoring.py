"""
AI Quality Scoring System
Competitive advantage over Loox - intelligent review quality assessment
"""
import re
from textblob import TextBlob

# VADER sentiment analysis
try:
    import nltk
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    # Download VADER lexicon if not already downloaded
    try:
        nltk.data.find('vader_lexicon')
    except LookupError:
        nltk.download('vader_lexicon', quiet=True)
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    SentimentIntensityAnalyzer = None

class ReviewQualityScorer:
    """AI-based review quality scoring"""
    
    def __init__(self):
        """Initialize VADER analyzer if available"""
        if VADER_AVAILABLE and SentimentIntensityAnalyzer:
            self.vader = SentimentIntensityAnalyzer()
        else:
            self.vader = None
    
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
    
    def _detect_repetitive_text(self, text):
        """
        Detect if text is repetitive (like the example: same sentence repeated 4 times)
        Returns True if text appears to be repetitive spam
        """
        if not text or len(text) < 20:
            return False
        
        # Split into sentences
        sentences = re.split(r'[.!?]\s+', text.strip())
        if len(sentences) < 2:
            return False
        
        # Check if sentences are very similar (normalize and compare)
        normalized_sentences = [s.strip().lower() for s in sentences if s.strip()]
        if len(normalized_sentences) < 2:
            return False
        
        # Check for duplicate sentences (more than 2 identical sentences = repetitive)
        sentence_counts = {}
        for sent in normalized_sentences:
            sentence_counts[sent] = sentence_counts.get(sent, 0) + 1
        
        # If any sentence appears more than 2 times, it's repetitive
        max_count = max(sentence_counts.values())
        if max_count >= 3:
            return True
        
        # Also check if text is just the same phrase repeated (like "10pcs is not 10 sets, but 5 sets")
        # Split by periods, commas, or line breaks
        phrases = re.split(r'[.,;\n]+', text.lower().strip())
        phrase_counts = {}
        for phrase in phrases:
            phrase = phrase.strip()
            if len(phrase) > 10:  # Only count meaningful phrases
                phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        
        if phrase_counts:
            max_phrase_count = max(phrase_counts.values())
            if max_phrase_count >= 3:
                return True
        
        return False
    
    def calculate_quality_score(self, review_data):
        """
        Calculate comprehensive quality score (0-10)
        Higher score = better quality review
        
        Improved algorithm: Star rating is now heavily weighted
        - 5-star reviews get base score 5-7 (depending on detail)
        - 4-star reviews get base score 3-5
        - Lower ratings get base score based on detail level
        """
        text = review_data.get('text', '') or review_data.get('body', '')
        rating = review_data.get('rating', 0)
        
        if not text:
            # No text = very low score
            return 1.0
        
        # Normalize AliExpress rating (0-100) to 1-5 scale
        if rating > 5:
            rating_normalized = max(1, min(5, int((rating / 100) * 5)))
        else:
            rating_normalized = max(1, min(5, int(rating)))
        
        text_lower = text.lower()
        
        # BASE SCORE: Star rating is the foundation
        # Ensures high-star reviews ALWAYS score higher than low-star reviews
        # Even a basic 5-star (6/10) beats the best 1-star (2/10 max)
        if rating_normalized == 5:
            score = 6  # 5-star: 6-10/10 (range: +0 to +4 from bonuses)
        elif rating_normalized == 4:
            score = 5  # 4-star: 5-9/10 (range: +0 to +4 from bonuses)
        elif rating_normalized == 3:
            score = 4  # 3-star: 4-8/10 (range: +0 to +4 from bonuses)
        elif rating_normalized == 2:
            score = 1  # 2-star: 1-3/10 (range: +0 to +2, capped at 3)
        else:  # 1-star
            score = 0  # 1-star: 0-2/10 (range: +0 to +2, capped at 2)
        
        # Text detail bonus (0-3 points)
        # Detailed reviews get bonus regardless of rating
        text_len = len(text)
        if text_len > 150:
            score += 3
        elif text_len > 80:
            score += 2
        elif text_len > 40:
            score += 1
        
        # Has images (0-2 points)
        images = review_data.get('images', [])
        if images and len(images) >= 2:
            score += 2
        elif images and len(images) >= 1:
            score += 1
        
        # Verified purchase (0-1 point)
        if review_data.get('verified', False) or review_data.get('verified_purchase', False):
            score += 1
        
        # Quality keywords present (0-2 points)
        keyword_count = sum(1 for keyword in self.QUALITY_KEYWORDS if keyword in text_lower)
        if keyword_count >= 2:
            score += 2
        elif keyword_count >= 1:
            score += 1
        
        # VADER sentiment analysis - validate alignment with star rating
        vader_sentiment = None
        vader_compound = None
        if self.vader:
            try:
                vader_scores = self.vader.polarity_scores(text)
                vader_compound = vader_scores['compound']  # Range: -1 (negative) to +1 (positive)
                
                # Check sentiment alignment with star rating
                # 5-star should be positive (compound >= 0.05)
                # 4-star should be neutral-positive (compound >= -0.05)
                # 3-star and below can be any sentiment
                
                if rating_normalized == 5:
                    # 5-star reviews MUST have positive sentiment to reach high scores
                    if vader_compound < 0.05:
                        # Mismatch: 5-star but not positive sentiment - penalize
                        score = max(score - 2, 6)  # Can't go below base 5-star score of 6
                    elif vader_compound >= 0.5:
                        # Very positive sentiment - bonus
                        score += 1
                elif rating_normalized == 4:
                    # 4-star reviews should be neutral to positive
                    if vader_compound < -0.1:
                        # Very negative sentiment for 4-star - penalize slightly
                        score = max(score - 1, 5)  # Can't go below base 4-star score
                elif rating_normalized <= 2:
                    # Negative reviews (1-2 star) should have negative/neutral sentiment
                    if vader_compound > 0.3:
                        # Very positive sentiment for negative review - might be spam
                        score = max(score - 1, 0)
                
            except Exception as e:
                # VADER failed, fall back to TextBlob
                pass
        
        # TextBlob sentiment bonus (if VADER not available or as supplement)
        if vader_compound is None:
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
        
        # Penalty for repetitive text (like the example review)
        if self._detect_repetitive_text(text):
            score = max(score - 3, 0)  # Heavy penalty for repetitive spam
        
        # Penalty for very short reviews with high rating (might be spam)
        # But keep it above 2-star max (3/10) - a short 5-star is still better than detailed negative
        if rating_normalized == 5 and text_len < 20:
            score = max(4, score - 2)  # Reduce to 4/10 minimum (still better than 2-star max of 3/10)
        
        # Cap 4-star reviews at 9/10 (as per user requirement)
        # Even perfect 4-star reviews can't reach 10/10
        if rating_normalized == 4:
            score = min(9, score)
        
        # Cap negative reviews: even with all bonuses, they can't exceed their maximum
        # 2-star reviews: max 3/10 (basic 4-star is 5/10, so always lower)
        if rating_normalized == 2:
            score = min(3, score)
        
        # 1-star reviews: max 2/10 (basic 3-star is 4/10, so always lower)
        if rating_normalized == 1:
            score = min(2, score)
        
        # 5-star reviews need positive sentiment to reach 10/10
        # If sentiment is neutral/negative but still high score, cap at 9/10
        if rating_normalized == 5 and score >= 9:
            if self.vader:
                try:
                    vader_scores = self.vader.polarity_scores(text)
                    if vader_scores['compound'] < 0.05:  # Not clearly positive
                        score = min(9, score)  # Cap at 9/10 for neutral/negative 5-star
                except:
                    pass
        
        # Ensure score is between 0 and 10
        score = max(0, min(10, score))
        
        return round(score, 1)
    
    def _analyze_sentiment(self, text):
        """Analyze sentiment using VADER (preferred) or TextBlob (fallback)"""
        # Try VADER first (more accurate)
        if self.vader:
            try:
                vader_scores = self.vader.polarity_scores(text)
                return vader_scores['compound']  # Range: -1 to +1
            except:
                pass
        
        # Fallback to TextBlob
        try:
            blob = TextBlob(text)
            # Polarity ranges from -1 (negative) to 1 (positive)
            return blob.sentiment.polarity
        except:
            # Final fallback: simple keyword-based sentiment
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
        """Calculate sentiment score (0-1 scale) using VADER if available"""
        if self.vader:
            try:
                vader_scores = self.vader.polarity_scores(text)
                compound = vader_scores['compound']  # -1 to +1
                # Convert from -1...1 to 0...1
                return (compound + 1) / 2
            except:
                pass
        
        # Fallback to TextBlob
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

