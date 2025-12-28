"""
Shopify App Blocks for Sakura Reviews
====================================

This creates seamless Shopify theme integration
that's superior to Loox's approach
"""

from flask import Flask, jsonify, request
import json

app = Flask(__name__)

@app.route('/app-blocks')
def app_blocks():
    """
    Shopify app blocks configuration
    Superior to Loox with more customization options
    """
    return jsonify({
        "blocks": [
            {
                "type": "sakura_reviews",
                "name": "🌸 Sakura Reviews",
                "description": "AI-powered review widget with multi-platform support",
                "settings": [
                    {
                        "type": "text",
                        "id": "title",
                        "label": "Reviews Title",
                        "default": "Customer Reviews",
                        "info": "Title displayed above the reviews"
                    },
                    {
                        "type": "range",
                        "id": "limit",
                        "label": "Number of Reviews",
                        "min": 5,
                        "max": 100,
                        "step": 5,
                        "default": 20,
                        "info": "Maximum number of reviews to display"
                    },
                    {
                        "type": "select",
                        "id": "theme",
                        "label": "Widget Theme",
                        "options": [
                            {"value": "default", "label": "🌸 Default"},
                            {"value": "minimal", "label": "⚪ Minimal"},
                            {"value": "colorful", "label": "🌈 Colorful"},
                            {"value": "dark", "label": "🌙 Dark Mode"}
                        ],
                        "default": "default",
                        "info": "Choose your preferred theme"
                    },
                    {
                        "type": "checkbox",
                        "id": "show_ai_scores",
                        "label": "Show AI Quality Scores",
                        "default": True,
                        "info": "Display AI-powered quality scores"
                    },
                    {
                        "type": "checkbox",
                        "id": "show_verified_badge",
                        "label": "Show Verified Badges",
                        "default": True,
                        "info": "Display verification badges"
                    },
                    {
                        "type": "checkbox",
                        "id": "show_photos_only",
                        "label": "Show Only Reviews with Photos",
                        "default": False,
                        "info": "Filter to show only photo reviews"
                    },
                    {
                        "type": "select",
                        "id": "sort_by",
                        "label": "Sort Reviews By",
                        "options": [
                            {"value": "newest", "label": "Newest First"},
                            {"value": "oldest", "label": "Oldest First"},
                            {"value": "highest_rated", "label": "Highest Rated"},
                            {"value": "ai_recommended", "label": "AI Recommended"}
                        ],
                        "default": "newest",
                        "info": "How to sort the reviews"
                    },
                    {
                        "type": "color",
                        "id": "accent_color",
                        "label": "Accent Color",
                        "default": "#ff69b4",
                        "info": "Custom accent color for the widget"
                    },
                    {
                        "type": "text",
                        "id": "custom_css",
                        "label": "Custom CSS",
                        "info": "Add custom CSS for advanced styling"
                    }
                ]
            }
        ]
    })

@app.route('/app-blocks/sakura_reviews')
def sakura_reviews_block():
    """
    Render the Sakura Reviews app block
    """
    settings = request.args.to_dict()
    
    # Get settings with defaults
    title = settings.get('title', 'Customer Reviews')
    limit = int(settings.get('limit', 20))
    theme = settings.get('theme', 'default')
    show_ai_scores = settings.get('show_ai_scores', 'true').lower() == 'true'
    show_verified = settings.get('show_verified_badge', 'true').lower() == 'true'
    photos_only = settings.get('show_photos_only', 'false').lower() == 'true'
    sort_by = settings.get('sort_by', 'newest')
    accent_color = settings.get('accent_color', '#ff69b4')
    custom_css = settings.get('custom_css', '')
    
    # Generate widget URL
    shop_id = request.args.get('shop_id', 'demo-shop')
    product_id = request.args.get('product_id', 'demo-product')
    
    widget_url = f"https://sakura-reviews.com/widget/{shop_id}/reviews/{product_id}"
    params = {
        'theme': theme,
        'limit': limit,
        'show_ai_scores': show_ai_scores,
        'show_verified': show_verified,
        'photos_only': photos_only,
        'sort_by': sort_by,
        'accent_color': accent_color
    }
    
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    full_widget_url = f"{widget_url}?{query_string}"
    
    # Generate the HTML
    html = f"""
    <!-- Sakura Reviews Widget - Superior to Loox -->
    <section id="sakura-reviews-section" class="sakura-reviews-widget sakura-theme-{theme}">
        <div class="sakura-reviews-header">
            <h2 class="sakura-reviews-title">{title}</h2>
        </div>
        
        <div class="sakura-reviews-container">
            <iframe 
                id="sakuraReviewsFrame"
                src="{full_widget_url}"
                width="100%"
                height="auto"
                frameborder="0"
                scrolling="no"
                style="border: none; overflow: hidden; min-height: 400px;"
                title="Sakura Reviews Widget"
                loading="lazy"
                allow="payment; fullscreen"
            >
                <p>Loading reviews...</p>
            </iframe>
        </div>
    </section>
    
    <style>
    .sakura-reviews-widget {{
        margin: 20px 0;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        background: white;
    }}
    
    .sakura-reviews-header {{
        background: linear-gradient(135deg, {accent_color}, #8b4a8b);
        color: white;
        padding: 20px;
        text-align: center;
    }}
    
    .sakura-reviews-title {{
        font-size: 24px;
        font-weight: 700;
        margin: 0;
    }}
    
    .sakura-reviews-container {{
        position: relative;
        background: white;
    }}
    
    #sakuraReviewsFrame {{
        display: block;
        width: 100%;
        border: none;
    }}
    
    /* Theme variations */
    .sakura-theme-minimal {{
        box-shadow: none;
        border: 1px solid #e2e8f0;
    }}
    
    .sakura-theme-colorful {{
        background: linear-gradient(135deg, #ff69b4, #8b4a8b, #4299e1);
    }}
    
    .sakura-theme-dark {{
        background: #1a202c;
        color: white;
    }}
    
    /* Custom CSS */
    {custom_css}
    </style>
    
    <script>
    // Auto-resize iframe based on content
    window.addEventListener('message', function(event) {{
        if (event.origin !== 'https://sakura-reviews.com') return;
        
        if (event.data.type === 'resize') {{
            const iframe = document.getElementById('sakuraReviewsFrame');
            iframe.style.height = event.data.height + 'px';
        }}
        
        if (event.data.type === 'review_click') {{
            // Track review interactions
            console.log('Review clicked:', event.data.reviewId);
        }}
    }});
    
    // Track widget views
    document.addEventListener('DOMContentLoaded', function() {{
        fetch('/analytics/widget-view', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{
                shop_id: '{shop_id}',
                product_id: '{product_id}',
                theme: '{theme}',
                timestamp: new Date().toISOString()
            }})
        }}).catch(console.error);
    }});
    </script>
    """
    
    return html

@app.route('/app-blocks/sakura_reviews/settings')
def sakura_reviews_settings():
    """
    Settings page for the Sakura Reviews app block
    """
    return """
    <div class="sakura-settings">
        <h3>🌸 Sakura Reviews Settings</h3>
        <p>Configure your review widget to match your store's style.</p>
        
        <div class="settings-grid">
            <div class="setting-group">
                <label>Widget Title</label>
                <input type="text" id="title" value="Customer Reviews" />
            </div>
            
            <div class="setting-group">
                <label>Number of Reviews</label>
                <input type="range" id="limit" min="5" max="100" value="20" />
                <span id="limit-value">20</span>
            </div>
            
            <div class="setting-group">
                <label>Theme</label>
                <select id="theme">
                    <option value="default">🌸 Default</option>
                    <option value="minimal">⚪ Minimal</option>
                    <option value="colorful">🌈 Colorful</option>
                    <option value="dark">🌙 Dark Mode</option>
                </select>
            </div>
            
            <div class="setting-group">
                <label>Accent Color</label>
                <input type="color" id="accent_color" value="#ff69b4" />
            </div>
        </div>
        
        <button onclick="saveSettings()">Save Settings</button>
    </div>
    
    <style>
    .sakura-settings {
        padding: 20px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    .settings-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin: 20px 0;
    }
    
    .setting-group {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .setting-group label {
        font-weight: 600;
        color: #2d3748;
    }
    
    .setting-group input,
    .setting-group select {
        padding: 8px 12px;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        font-size: 14px;
    }
    
    button {
        background: #ff69b4;
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
    }
    
    button:hover {
        background: #e53e3e;
    }
    </style>
    
    <script>
    function saveSettings() {
        const settings = {
            title: document.getElementById('title').value,
            limit: document.getElementById('limit').value,
            theme: document.getElementById('theme').value,
            accent_color: document.getElementById('accent_color').value
        };
        
        // Save to Shopify
        window.parent.postMessage({
            type: 'save_settings',
            settings: settings
        }, '*');
        
        alert('Settings saved!');
    }
    
    // Update limit value display
    document.getElementById('limit').addEventListener('input', function() {
        document.getElementById('limit-value').textContent = this.value;
    });
    </script>
    """

if __name__ == '__main__':
    app.run(debug=True, port=5002)
