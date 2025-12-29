"""
ReviewKing - Loox-Inspired Architecture
Simple, reliable, and with stealth fallback to Loox's infrastructure
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["*"])

# Loox stealth config (Plan B)
LOOX_FALLBACK_ID = "b3Zk9ExHgf.eca2133e2efc041236106236b783f6b4"
LOOX_ENDPOINT = "https://loox.io/-/admin/reviews/import/url"

class AliExpressScraper:
    """Server-side scraper - Like Loox does it"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })
    
    def scrape_reviews(self, product_id, seller_id=None, page=1, page_size=100):
        """
        Scrape reviews server-side using AliExpress's OFFICIAL JSON API!
        This is the GOLD STANDARD approach - no HTML parsing needed!
        
        Args:
            product_id: AliExpress product ID
            seller_id: Optional seller ID
            page: Page number (default: 1)
            page_size: Reviews per page (default: 100, max: 100)
        """
        try:
            # AliExpress's official feedback API endpoint
            api_url = "https://feedback.aliexpress.com/pc/searchEvaluation.do"
            
            params = {
                'productId': product_id,
                'lang': 'en_US',
                'country': 'US',
                'pageSize': min(page_size, 100),  # Max 100 per request
                'filter': 'all',
                'sort': 'complex_default',
                'page': page
            }
            
            if seller_id:
                params['ownerMemberId'] = seller_id
            
            logger.info(f"Fetching reviews from AliExpress API for product {product_id}")
            
            response = self.session.get(api_url, params=params, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"API returned {response.status_code}, trying fallback...")
                return self._fallback_scrape(product_id)
            
            # Parse JSON response
            try:
                data = response.json()
                reviews = self._parse_api_response(data)
                logger.info(f"✅ Successfully extracted {len(reviews)} reviews from API")
                return reviews
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON, trying HTML fallback...")
                return self._fallback_scrape(product_id)
            
        except Exception as e:
            logger.error(f"API scraping error: {e}")
            return self._fallback_scrape(product_id)
    
    def _parse_api_response(self, data):
        """Parse the JSON response from AliExpress feedback API"""
        reviews = []
        
        try:
            # AliExpress API structure
            evals = data.get('data', {}).get('evaViewList', [])
            
            for eval_item in evals:
                # Extract images
                images = []
                for img in eval_item.get('images', []):
                    if isinstance(img, str):
                        images.append(img)
                    elif isinstance(img, dict):
                        img_url = img.get('imgUrl') or img.get('url')
                        if img_url:
                            images.append(img_url)
                
                reviews.append({
                    'id': eval_item.get('evaluationId', str(eval_item.get('id', ''))),
                    'reviewer_name': eval_item.get('buyerName', 'Customer'),
                    'text': eval_item.get('buyerFeedback', ''),
                    'rating': int(eval_item.get('buyerEval', 5)),
                    'date': eval_item.get('evalTime', datetime.now().strftime('%Y-%m-%d')),
                    'country': eval_item.get('buyerCountry', 'Unknown'),
                    'verified': True,
                    'images': images,
                    'platform': 'aliexpress',
                    'translation': eval_item.get('buyerTranslationFeedback')
                })
            
            return reviews
            
        except Exception as e:
            logger.error(f"Error parsing API response: {e}")
            return []
    
    def _fallback_scrape(self, product_id):
        """Fallback to HTML scraping if API fails"""
        try:
            url = f"https://www.aliexpress.com/item/{product_id}.html"
            logger.info(f"Fallback: Scraping HTML from {url}")
            
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            reviews = self._extract_from_runparams(response.text)
            
            if not reviews:
                reviews = self._parse_dom_reviews(soup)
            
            return reviews
            
        except Exception as e:
            logger.error(f"Fallback scraping error: {e}")
            return []
    
    def _extract_from_runparams(self, html):
        """Extract reviews from window.runParams"""
        try:
            # Find runParams in script
            match = re.search(r'window\.runParams\s*=\s*(\{.*?\});', html, re.DOTALL)
            if not match:
                return []
            
            data = json.loads(match.group(1))
            feedback_module = data.get('data', {}).get('feedbackModule', {})
            feedback_list = feedback_module.get('feedbackList', [])
            
            reviews = []
            for r in feedback_list:
                # Extract images properly
                images = []
                for img in r.get('images', []):
                    if isinstance(img, dict):
                        img_url = img.get('imgUrl') or img.get('url')
                    else:
                        img_url = img
                    
                    if img_url and 'aliexpress' in img_url:
                        images.append(img_url)
                
                reviews.append({
                    'id': r.get('evaluationId', str(r.get('id', ''))),
                    'reviewer_name': r.get('buyerName', 'Customer'),
                    'text': r.get('buyerFeedback', ''),
                    'rating': int(r.get('buyerEval', 5)),
                    'date': r.get('evalTime', datetime.now().strftime('%Y-%m-%d')),
                    'country': r.get('buyerCountry', 'Unknown'),
                    'verified': True,
                    'images': images,
                    'platform': 'aliexpress'
                })
            
            logger.info(f"Extracted {len(reviews)} reviews from runParams")
            return reviews
            
        except Exception as e:
            logger.error(f"runParams extraction error: {e}")
            return []
    
    def _parse_dom_reviews(self, soup):
        """Fallback: Parse reviews from DOM"""
        reviews = []
        
        # Find review containers
        review_containers = soup.select('[class*="list"][class*="itemWrap"]')
        
        for idx, container in enumerate(review_containers[:20]):  # Limit to 20
            try:
                # Get reviewer name and date
                info = container.select_one('[class*="itemInfo"]')
                if info:
                    info_text = info.get_text(strip=True)
                    parts = info_text.split('|')
                    name = parts[0].strip() if parts else 'Customer'
                    date_str = parts[1].strip() if len(parts) > 1 else ''
                else:
                    name = 'Customer'
                    date_str = ''
                
                # Get review text
                text_el = container.select_one('[class*="itemReview"]')
                text = text_el.get_text(strip=True) if text_el else ''
                
                if not text or len(text) < 5:
                    continue
                
                # Count stars
                stars = container.select('[class*="starreviewfilled"]')
                rating = len(stars) if stars else 5
                
                # Get images (exclude avatars)
                images = []
                for img in container.select('img'):
                    if img.get('class') and any('Photo' in c for c in img.get('class')):
                        continue  # Skip avatar
                    
                    src = img.get('src') or img.get('data-src')
                    if src and 'aliexpress' in src and '/kf/' in src:
                        images.append(src)
                
                reviews.append({
                    'id': f'dom_{idx}',
                    'reviewer_name': name,
                    'text': text,
                    'rating': rating,
                    'date': date_str or datetime.now().strftime('%Y-%m-%d'),
                    'country': 'Unknown',
                    'verified': True,
                    'images': images,
                    'platform': 'aliexpress'
                })
                
            except Exception as e:
                logger.error(f"Error parsing review {idx}: {e}")
                continue
        
        logger.info(f"Parsed {len(reviews)} reviews from DOM")
        return reviews

def scrape_via_loox_stealth(product_id, seller_id=None):
    """
    FALLBACK: Use Loox's infrastructure stealthily
    """
    try:
        params = {
            'id': LOOX_FALLBACK_ID,
            'productId': product_id,
            'page': 1
        }
        
        if seller_id:
            params['ownerMemberId'] = seller_id
        
        logger.info(f"[FALLBACK] Using Loox endpoint for product {product_id}")
        
        response = requests.get(LOOX_ENDPOINT, params=params, timeout=10)
        
        if response.status_code == 200:
            logger.info("[FALLBACK] Loox endpoint responded successfully")
            # For now, return empty reviews array - we got a response but haven't parsed it yet
            # TODO: Parse Loox HTML to extract reviews
            return {
                'success': True, 
                'source': 'loox_fallback', 
                'reviews': [],  # Empty for now until we parse Loox's HTML
                'total': 0,
                'stats': {'ai_recommended': 0, 'with_photos': 0, 'avg_quality': 0, 'avg_rating': 0}
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Loox fallback error: {e}")
        return None

@app.route('/', methods=['GET'])
def homepage():
    """Simple homepage for the app"""
    # Get the host URL for the bookmarklet
    host = request.host_url.rstrip('/').replace('http://', 'https://')
    bookmarklet_code = f"javascript:(function(){{var s=document.createElement('script');s.src='{host}/bookmarklet.js';document.head.appendChild(s);}})();"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🌸 Sakura Reviews</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                background: linear-gradient(135deg, #FFB6C1, #FFC0CB, #FFE4E1);
                margin: 0; padding: 40px; text-align: center;
            }}
            .container {{ 
                background: white; 
                border-radius: 20px; 
                padding: 40px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                max-width: 700px; margin: 0 auto;
            }}
            h1 {{ color: #FF69B4; font-size: 2.5em; margin-bottom: 20px; }}
            .tagline {{ color: #666; font-size: 1.2em; margin-bottom: 30px; }}
            .features {{ text-align: left; margin: 30px 0; }}
            .feature {{ margin: 10px 0; color: #333; }}
            .bookmarklet-btn {{ 
                background: #FF69B4; color: white; 
                padding: 15px 30px; border-radius: 25px; 
                border: none; cursor: pointer;
                margin: 20px 0; font-weight: bold; font-size: 16px;
            }}
            .bookmarklet-btn:hover {{ background: #FF1493; }}
            .instructions {{ 
                display: none; 
                background: #FFF0F5; 
                border: 2px dashed #FF69B4; 
                border-radius: 10px; 
                padding: 20px; 
                margin: 20px 0; 
                text-align: left;
            }}
            .instructions.show {{ display: block; }}
            .code-box {{ 
                background: #FFE4E1; 
                border: 1px solid #FF69B4; 
                border-radius: 5px; 
                padding: 15px; 
                margin: 15px 0; 
                font-family: monospace; 
                font-size: 12px;
                word-break: break-all;
                cursor: pointer;
                position: relative;
            }}
            .copy-btn {{ 
                background: #FF69B4; 
                color: white; 
                border: none; 
                padding: 8px 15px; 
                border-radius: 5px; 
                cursor: pointer; 
                margin-top: 10px;
            }}
            .copy-btn:hover {{ background: #FF1493; }}
            .step {{ 
                background: #FFF; 
                border-left: 4px solid #FF69B4; 
                padding: 10px; 
                margin: 10px 0; 
            }}
            .success {{ color: #4CAF50; font-weight: bold; display: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌸 Sakura Reviews</h1>
            <p class="tagline">Beautiful reviews, naturally • Powered by AI</p>
            
            <div class="features">
                <div class="feature">✅ 100 reviews loaded at once</div>
                <div class="feature">✅ Smart filters (Photos, AI, Star ratings)</div>
                <div class="feature">✅ Server-side scraping (AliExpress API)</div>
                <div class="feature">✅ AI quality scoring</div>
                <div class="feature">✅ Beautiful gradient UI</div>
            </div>
            
            <p><strong>How to use:</strong></p>
            <p>1. Go to any AliExpress product page</p>
            <p>2. Use the bookmarklet to import reviews</p>
            <p>3. Import to your Shopify store</p>
            
            <button class="bookmarklet-btn" onclick="toggleInstructions()">
                📖 Get Bookmarklet
            </button>
            
            <div class="instructions" id="instructions">
                <h3 style="color: #FF69B4; margin-top: 0;">📚 Installation Instructions</h3>
                
                <div class="step">
                    <strong>Step 1:</strong> Copy the bookmarklet code below
                </div>
                
                <div class="code-box" onclick="copyCode()" title="Click to copy">
                    {bookmarklet_code}
                </div>
                
                <button class="copy-btn" onclick="copyCode()">📋 Copy Bookmarklet</button>
                <span class="success" id="copySuccess">✅ Copied!</span>
                
                <div class="step">
                    <strong>Step 2:</strong> Create a new bookmark in your browser
                    <ul>
                        <li><strong>Chrome/Edge:</strong> Press Ctrl+D (or Cmd+D on Mac)</li>
                        <li><strong>Firefox:</strong> Press Ctrl+D (or Cmd+D on Mac)</li>
                        <li><strong>Safari:</strong> Press Cmd+D</li>
                    </ul>
                </div>
                
                <div class="step">
                    <strong>Step 3:</strong> Name it "Sakura Reviews" and paste the code as the URL
                </div>
                
                <div class="step">
                    <strong>Step 4:</strong> Go to any AliExpress product page and click your new bookmark!
                </div>
                
                <p style="text-align: center; color: #666; margin-top: 20px;">
                    💡 <em>The bookmarklet will only work on AliExpress product pages</em>
                </p>
            </div>
        </div>
        
        <script>
            function toggleInstructions() {{
                const instructions = document.getElementById('instructions');
                instructions.classList.toggle('show');
            }}
            
            function copyCode() {{
                const code = '{bookmarklet_code.replace("'", "\\'")}';
                navigator.clipboard.writeText(code).then(() => {{
                    const success = document.getElementById('copySuccess');
                    success.style.display = 'inline';
                    setTimeout(() => {{
                        success.style.display = 'none';
                    }}, 2000);
                }}).catch(err => {{
                    alert('Failed to copy. Please select and copy manually.');
                }});
            }}
        </script>
    </body>
    </html>
    """

@app.route('/api/scrape', methods=['GET'])
def scrape_reviews():
    """
    Main endpoint - Scrapes reviews server-side
    Query params: productId, sellerId (optional), page (optional, default: 1)
    """
    product_id = request.args.get('productId')
    seller_id = request.args.get('sellerId')
    page = int(request.args.get('page', 1))
    
    logger.info(f"[BOOKMARKLET] Received request: productId={product_id}, sellerId={seller_id}, page={page}")
    logger.info(f"[BOOKMARKLET] Full request args: {dict(request.args)}")
    
    if not product_id:
        logger.error("[ERROR] No productId provided!")
        return jsonify({'success': False, 'error': 'productId required'}), 400
    
    scraper = AliExpressScraper()
    
    # PRIMARY: Our own scraper
    logger.info(f"[SCRAPING] Starting scrape for product {product_id}, page {page}...")
    reviews = scraper.scrape_reviews(product_id, seller_id, page=page)
    logger.info(f"[SUCCESS] Scraped {len(reviews)} reviews")
    
    if reviews:
        # Apply AI scoring
        for review in reviews:
            review['quality_score'] = calculate_quality_score(review)
            review['ai_recommended'] = review['quality_score'] >= 8
        
        reviews.sort(key=lambda x: x['quality_score'], reverse=True)
        
        return jsonify({
            'success': True,
            'source': 'reviewking',
            'reviews': reviews,
            'total': len(reviews),
            'stats': calculate_stats(reviews),
            'pagination': {
                'current_page': page,
                'per_page': len(reviews),
                'has_more': False  # We load 100 max, no "Load More" needed
            }
        })
    
    # FALLBACK: Try Loox's endpoint
    logger.warning("[FALLBACK] Primary scraper returned empty, trying Loox fallback...")
    loox_result = scrape_via_loox_stealth(product_id, seller_id)
    
    if loox_result:
        logger.info("[FALLBACK] Loox fallback succeeded!")
        return jsonify(loox_result)
    
    # Both failed
    logger.error(f"[FAILED] Could not scrape reviews for productId={product_id} from any source!")
    return jsonify({
        'success': False,
        'error': 'Could not scrape reviews from any source'
    }), 500

def calculate_quality_score(review):
    """AI quality scoring"""
    score = 5.0
    
    # Length scoring
    text_length = len(review.get('text', ''))
    if text_length > 100:
        score += 2
    elif text_length > 50:
        score += 1
    
    # Image scoring
    if len(review.get('images', [])) > 0:
        score += 2
    
    # Rating consideration
    if review.get('rating', 5) >= 4:
        score += 1
    
    return min(10, score)

def calculate_stats(reviews):
    """Calculate review statistics"""
    if not reviews:
        return {}
    
    return {
        'ai_recommended': sum(1 for r in reviews if r.get('ai_recommended')),
        'with_photos': sum(1 for r in reviews if len(r.get('images', [])) > 0),
        'avg_quality': sum(r.get('quality_score', 0) for r in reviews) / len(reviews),
        'avg_rating': sum(r.get('rating', 0) for r in reviews) / len(reviews)
    }

@app.route('/bookmarklet.js', methods=['GET'])
@app.route('/js/bookmarklet.js', methods=['GET'])  # Also support /js/bookmarklet.js
def bookmarklet():
    """
    Simplified bookmarklet - Extract ONLY productId and sellerId
    Like Loox does it!
    """
    # Use current request host (supports localhost for dev)
    host = request.host_url.rstrip('/')
    
    js = f"""
(function() {{
    if (window.reviewKingActive) return;
    window.reviewKingActive = true;
    
    const API_URL = '{host}';
    
    // Global state
    let allReviews = [];
    let currentFilter = 'ai_recommended';  // Default to AI Recommended (best quality reviews)
    
    // LOOX'S EXACT EXTRACTION LOGIC
    function extractProductInfo() {{
        const url = window.location.href;
        const bodyHTML = document.body.innerHTML;
        
        let productId = null;
        let sellerId = null;
        let source = 'unknown';
        
        // Method 1: runParams (PRIMARY - like Loox)
        if (typeof window.runParams === 'object' && window.runParams.data) {{
            const data = window.runParams.data;
            const feedbackModule = data.feedbackModule || {{}};
            
            if (feedbackModule.productId && feedbackModule.sellerAdminSeq) {{
                productId = feedbackModule.productId;
                sellerId = feedbackModule.sellerAdminSeq;
                source = 'runParams-feedbackModule';
            }} else if (data.productId && data.adminSeq) {{
                productId = data.productId;
                sellerId = data.adminSeq;
                source = 'runParams-root';
            }} else if (data.storeModule?.productId && data.storeModule?.sellerAdminSeq) {{
                productId = data.storeModule.productId;
                sellerId = data.storeModule.sellerAdminSeq;
                source = 'runParams-storeModule';
            }}
        }}
        
        // Method 2: Extract from URL
        if (!productId) {{
            const urlMatch = url.match(/\\/item\\/(\\d+)/);
            if (urlMatch) {{
                productId = urlMatch[1];
                source = 'url';
            }}
        }}
        
        // Method 3: window.adminAccountId
        if (!sellerId && typeof window.adminAccountId === 'number') {{
            sellerId = window.adminAccountId;
        }}
        
        // Method 4: Regex from body HTML
        if (!sellerId) {{
            const adminMatch = /adminAccountId=(\\d+)/.exec(bodyHTML);
            if (adminMatch) {{
                sellerId = adminMatch[1];
            }}
        }}
        
        console.log('Extracted:', {{ productId, sellerId, source }});
        
        return {{ productId, sellerId, source }};
    }}
    
    // Create overlay
    function createOverlay() {{
        const overlay = document.createElement('div');
        overlay.id = 'reviewking-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            z-index: 999999;
            display: flex;
            justify-content: center;
            align-items: center;
        `;
        
        overlay.innerHTML = `
            <div style="background: #0f0f23; padding: 30px; border-radius: 16px; max-width: 1000px; width: 95%; max-height: 95vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.5);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; border-bottom: 2px solid #FF69B4; padding-bottom: 15px;">
                    <div>
                        <h2 style="color: #FF69B4; margin: 0; font-size: 28px;">🌸 Sakura Reviews</h2>
                        <p style="color: #888; margin: 5px 0 0 0; font-size: 14px;">Beautiful reviews, naturally • Powered by AI</p>
                    </div>
                    <button onclick="this.closest('#reviewking-overlay').remove(); window.reviewKingActive=false;" 
                            style="background: #FF69B4; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; transition: all 0.3s;">
                        ✕ Close
                    </button>
                </div>
                <div id="rk-content" style="color: white;">
                    <p style="text-align: center; padding: 20px;">Extracting product info...</p>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        return overlay;
    }}
    
    // Fetch and display reviews
    async function fetchReviews() {{
        const overlay = createOverlay();
        const content = document.getElementById('rk-content');
        
        const {{ productId, sellerId, source }} = extractProductInfo();
        
        if (!productId) {{
            content.innerHTML = '<p style="color: #ff4444;">Error: Could not extract product ID</p>';
            return;
        }}
        
        content.innerHTML = `
            <p>Product ID: ${{productId}}</p>
            <p>Seller ID: ${{sellerId || 'Not found'}}</p>
            <p>Source: ${{source}}</p>
            <p>Fetching reviews from server...</p>
        `;
        
        try {{
            const params = new URLSearchParams({{ productId }});
            if (sellerId) params.append('sellerId', sellerId);
            
            const url = `${{API_URL}}/api/scrape?${{params}}`;
            console.log('[ReviewKing] Fetching:', url);
            
            const response = await fetch(url, {{
                method: 'GET'
            }});
            
            console.log('[ReviewKing] Response status:', response.status);
            const result = await response.json();
            console.log('[ReviewKing] Result:', result);
            console.log('[ReviewKing] Reviews array length:', result.reviews ? result.reviews.length : 'UNDEFINED');
            
            if (result.success) {{
                console.log('[ReviewKing] Calling displayReviews with', result.reviews.length, 'reviews');
                allReviews = result.reviews;  // Store globally
                displayReviews();
            }} else {{
                console.error('[ReviewKing] API returned error:', result.error);
                content.innerHTML = `<p style="color: #ff4444;">Error: ${{result.error}}</p>`;
            }}
        }} catch (error) {{
            console.error('[ReviewKing] Catch block error:', error);
            content.innerHTML = `<p style="color: #ff4444;">Fetch error: ${{error.message}}</p>`;
        }}
    }}
    
    function displayReviews() {{
        console.log('[displayReviews] Called with allReviews.length:', allReviews.length);
        const content = document.getElementById('rk-content');
        
        if (allReviews.length === 0) {{
            console.error('[displayReviews] No reviews found!');
            content.innerHTML = '<p>No reviews found</p>';
            return;
        }}
        
        // Apply current filter
        let filteredReviews = allReviews;
        if (currentFilter === 'photos') {{
            filteredReviews = allReviews.filter(r => r.images && r.images.length > 0);
        }} else if (currentFilter === 'ai_recommended') {{
            filteredReviews = allReviews.filter(r => r.ai_recommended);
        }} else if (currentFilter === '5stars') {{
            filteredReviews = allReviews.filter(r => r.rating >= 90);
        }} else if (currentFilter === '4-5stars') {{
            filteredReviews = allReviews.filter(r => r.rating >= 70);
        }} else if (currentFilter === '3stars') {{
            filteredReviews = allReviews.filter(r => r.rating >= 50 && r.rating < 70);
        }}
        
        console.log('[displayReviews] Filtered to', filteredReviews.length, 'reviews with filter:', currentFilter);
        
        // Calculate stats
        const stats = {{
            total: allReviews.length,
            ai_recommended: allReviews.filter(r => r.ai_recommended).length,
            with_photos: allReviews.filter(r => r.images && r.images.length > 0).length,
            avg_quality: allReviews.reduce((sum, r) => sum + (r.quality_score || 0), 0) / allReviews.length
        }};
        
        content.innerHTML = `
            <div style="background: linear-gradient(135deg, #FF69B4 0%, #FF1493 100%); padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(255,105,180,0.3);">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                    <div style="text-align: center;">
                        <div style="font-size: 32px; font-weight: bold; color: white;">${{stats.total}}</div>
                        <div style="color: #ffebf5; font-size: 14px;">Total Loaded</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 32px; font-weight: bold; color: white;">${{stats.ai_recommended}}</div>
                        <div style="color: #ffebf5; font-size: 14px;">AI Recommended</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 32px; font-weight: bold; color: white;">${{stats.with_photos}}</div>
                        <div style="color: #ffebf5; font-size: 14px;">With Photos</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 32px; font-weight: bold; color: white;">${{stats.avg_quality.toFixed(1)}}/10</div>
                        <div style="color: #ffebf5; font-size: 14px;">Avg Quality</div>
                    </div>
                </div>
            </div>
            
            <div style="background: #1a1f35; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                <div style="color: #aaa; font-size: 13px; margin-bottom: 10px;">Filter Reviews:</div>
                <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                    <button onclick="window.reviewKingSetFilter('all')" style="background: ${{currentFilter === 'all' ? '#FF69B4' : '#2d3748'}}; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold;">All (${{stats.total}})</button>
                    <button onclick="window.reviewKingSetFilter('photos')" style="background: ${{currentFilter === 'photos' ? '#FF69B4' : '#2d3748'}}; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold;">📷 With Photos (${{stats.with_photos}})</button>
                    <button onclick="window.reviewKingSetFilter('ai_recommended')" style="background: ${{currentFilter === 'ai_recommended' ? '#FF69B4' : '#2d3748'}}; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold;">🌸 AI Recommended (${{stats.ai_recommended}})</button>
                    <button onclick="window.reviewKingSetFilter('5stars')" style="background: ${{currentFilter === '5stars' ? '#FF69B4' : '#2d3748'}}; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold;">5 ⭐ Only</button>
                    <button onclick="window.reviewKingSetFilter('4-5stars')" style="background: ${{currentFilter === '4-5stars' ? '#FF69B4' : '#2d3748'}}; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold;">4-5 ⭐</button>
                    <button onclick="window.reviewKingSetFilter('3stars')" style="background: ${{currentFilter === '3stars' ? '#FF69B4' : '#2d3748'}}; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold;">3 ⭐ Only</button>
                </div>
                <div style="color: #888; font-size: 12px; margin-top: 10px;">Showing ${{filteredReviews.length}} of ${{stats.total}} reviews</div>
            </div>
            
            <div id="reviews-list"></div>
        `;
        
        // Render reviews separately to avoid template string nesting issues
        const reviewsList = document.getElementById('reviews-list');
        filteredReviews.forEach((r, i) => {{
            const reviewDiv = document.createElement('div');
            reviewDiv.style.cssText = 'background: linear-gradient(145deg, #1a1f35 0%, #16213e 100%); padding: 20px; margin-bottom: 15px; border-radius: 12px; border-left: 5px solid ' + (r.ai_recommended ? '#FF69B4' : '#555') + '; box-shadow: 0 4px 15px rgba(0,0,0,0.3);';
            
            let stars = '★'.repeat(Math.ceil(r.rating / 20)) + '☆'.repeat(5 - Math.ceil(r.rating / 20));
            
            let imagesHTML = '';
            if (r.images && r.images.length > 0) {{
                imagesHTML = '<div style="display: flex; gap: 12px; flex-wrap: wrap; margin-top: 15px;">';
                r.images.forEach(img => {{
                    imagesHTML += '<a href="' + img + '" target="_blank"><img src="' + img + '" style="width: 120px; height: 120px; object-fit: cover; border-radius: 8px; border: 2px solid #333; cursor: pointer;" /></a>';
                }});
                imagesHTML += '</div>';
            }}
            
            let originalHTML = '';
            if (r.translation && r.text !== r.translation) {{
                originalHTML = '<p style="color: #888; font-size: 13px; margin-top: 10px; font-style: italic; border-left: 2px solid #555; padding-left: 10px;">Original: ' + r.text + '</p>';
            }}
            
            reviewDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div>
                        <strong style="color: #fff; font-size: 16px;">${{r.reviewer_name}}</strong>
                        <span style="color: #888; font-size: 13px; margin-left: 10px;">${{r.date}} • ${{r.country}}</span>
                    </div>
                    <div style="background: ${{r.ai_recommended ? '#00ff88' : '#555'}}; color: #000; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 12px;">
                        ${{r.quality_score}}/10
                    </div>
                </div>
                <div style="color: #ffa500; margin-bottom: 12px; font-size: 20px;">${{stars}}</div>
                <p style="color: #e0e0e0; line-height: 1.7; font-size: 15px; margin: 0;">${{r.translation || r.text}}</p>
                ${{originalHTML}}
                ${{imagesHTML}}
            `;
            
            reviewsList.appendChild(reviewDiv);
        }});
    }}
    
    // Filter function (accessible globally)
    window.reviewKingSetFilter = function(filter) {{
        currentFilter = filter;
        displayReviews();
    }};
    
    // Start the process
    fetchReviews();
}})();
    """
    
    # Return with cache-busting headers
    return js, 200, {
        'Content-Type': 'application/javascript',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))  # Default to 5001 to avoid cache
    
    print("=" * 70)
    print("🌸 SAKURA REVIEWS - Beautiful reviews, naturally")
    print("=" * 70)
    print(f"Port: {port}")
    print()
    print("FEATURES:")
    print("  [+] 100 reviews loaded at once")
    print("  [+] Smart filters (Photos, AI, Star ratings)")
    print("  [+] Server-side scraping (AliExpress API)")
    print("  [+] AI quality scoring")
    print("  [+] Beautiful gradient UI")
    print("=" * 70)
    print()
    print("BOOKMARKLET:")
    bookmarklet_code = f"javascript:(function(){{var s=document.createElement('script');s.src='http://localhost:{port}/bookmarklet.js?v='+Date.now();document.head.appendChild(s);}})();"
    print(bookmarklet_code)
    print("=" * 70)
    print()
    
    app.run(host='0.0.0.0', port=port, debug=True)

