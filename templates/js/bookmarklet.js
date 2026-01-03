// [SSR MODE] INIT v" + Date.now() + "
// ReviewKing Enhanced Bookmarklet - Superior to Loox
(function() {
    // Check if overlay already exists
    const existingOverlay = document.getElementById('reviewking-overlay');
    if (existingOverlay) {
        console.log('[REVIEWKING] Already active, skipping...');
        return;
    }
    
    const API_URL = '{{ host }}';
    
    class ReviewKingClient {
        constructor() {
            // Assign to window FIRST so onclick handlers can reference it
            window.reviewKingClient = this;
            
            this.sessionId = Math.random().toString(36).substr(2, 9);
            this.selectedProduct = null;
            this.searchTimeout = null;
            this.allReviews = [];  // Store all reviews
            this.reviews = [];  // Filtered reviews for display
            this.currentFilter = 'all';  // Current filter
            this.selectedCountry = 'all';  // Country filter
            this.showTranslations = true;  // Translation toggle (default ON)
            this.modalProductId = null;  // Store product ID clicked in modal
            this.modalClickHandler = null;  // Store event handler for cleanup
            this.currentIndex = 0;  // Initialize current review index
            this.pagination = { has_next: false, page: 1 };  // Initialize pagination
            this.stats = { with_photos: 0, ai_recommended: 0, reviews_45star: 0, reviews_3star: 0 };  // Initialize stats
            this.isImporting = false;  // Track bulk import progress
            this.init();
        }
        
        init() {
            // Check if we're on SSR/modal page
            const isModalPage = this.isModalPage();
            
            if (isModalPage) {
                // ⚡️ SSR page - setup modal detection and user guidance
                // CRITICAL: This calls setupModalListener() which adds the "Get Reviews" button
                // DO NOT REMOVE THIS CALL - it's essential for SSR functionality
                this.setupModalListener();
                return;
            }
            
            // Normal product page - detect product from URL
            this.productData = this.detectProduct();
            if (!this.productData.productId) {
                alert('Could not detect product on this page. Please open a product page.');
                return;
            }
            this.createOverlay();
            this.loadReviews();
        }
        
        isModalPage() {
            // ⚡️ CRITICAL: This method determines if we're on SSR page
            // If returns true, setupModalListener() is called which adds the "Get Reviews" button
            // Check if we're on a modal/immersive page (not a regular product page)
            const url = window.location.href;
            
            // If it's a direct product page (/item/xxxxx.html), it's NOT modal mode
            if (url.includes('/item/') && /\d{13,}\.html/.test(url)) {
                return false;
            }
            
            // Otherwise, check for modal/SSR page indicators
            return url.includes('_immersiveMode=true') || 
                   url.includes('disableNav=YES') ||
                   url.includes('/ssr/');
        }
        
        detectProductFromModal() {
            console.log('[MODAL MODE] Detecting product from currently open modal...');
            
            // Simple approach: Check hidden input field that stores the clicked product ID
            const hiddenInput = document.getElementById('sakura-reviews-product-id');
            if (hiddenInput && hiddenInput.value) {
                console.log('[MODAL MODE] ✅ Found product ID in hidden field:', hiddenInput.value);
                return hiddenInput.value;
            }
            
            console.log('[MODAL MODE] ❌ No product ID found in hidden field');
            return null;
        }
        
        // ====================================================================
        // ⚡️ CRITICAL SSR BUTTON CODE - DO NOT REMOVE OR MODIFY ⚡️
        // ====================================================================
        // This code adds "Get Reviews" button to AliExpress SSR modal pages.
        // It was developed over 16+ hours and is essential functionality.
        // Location: Lines ~1861-2167 in app_enhanced.py
        // Backup: See SSR_BUTTON_CODE_BACKUP.py for complete code reference
        // ====================================================================
        
        setupModalListener() {
            console.log('[SSR MODE] Setting up Sakura Reviews for AliExpress SSR page...');
            
            // Check if AliExpress modal is currently open (try multiple selectors)
            const modalSelectors = [
                '.comet-v2-modal-mask.comet-v2-fade-appear-done.comet-v2-fade-enter-done',
                '.comet-v2-modal-mask',
                '.comet-modal-mask',
                '[class*="modal-mask"]',
                '.comet-v2-modal-wrap',
                '.comet-modal-wrap'
            ];
            
            let modalFound = false;
            for (const selector of modalSelectors) {
                const element = document.querySelector(selector);
                if (element) {
                    console.log('[SSR MODE] ✅ Found modal with selector:', selector);
                    modalFound = true;
                    break;
                }
            }
            
            if (modalFound) {
                console.log('[SSR MODE] ✅ AliExpress modal is open - activating Sakura Reviews');
                
                // Show activation message
                alert('🌸 Sakura Reviews is now activated!\n\nClick on any product to add the "Get Reviews Now" button.');
                
                // Close the modal after user clicks OK
                setTimeout(() => {
                    const closeButton = document.querySelector('button[aria-label="Close"].comet-v2-modal-close') ||
                                     document.querySelector('.comet-v2-modal-close') ||
                                     document.querySelector('[aria-label*="Close"]');
                    if (closeButton) {
                        closeButton.click();
                    }
                }, 100);
                
                // Setup click listener for products
                this.setupProductClickListener();
                
            } else {
                console.log('[SSR MODE] No modal currently open - setting up listener for when user clicks product');
                // Even if modal isn't open, set up listener for when user clicks a product
                this.setupProductClickListener();
                
                // Show helpful message
                alert('🌸 Sakura Reviews\n\nClick on any product in the search results to add the "Get Reviews" button to its modal.');
            }
        }
        
        setupProductClickListener() {
            console.log('[SSR MODE] Setting up product click listener...');
            
            // Remove existing listener if it exists
            if (this.modalClickHandler) {
                document.body.removeEventListener('click', this.modalClickHandler, true);
            }
            
            // Listen for clicks on products
            this.modalClickHandler = (event) => {
                // Try multiple ways to find the product element
                let productElement = event.target.closest('.productContainer');
                if (!productElement) {
                    // Try other common product container classes
                    productElement = event.target.closest('[data-product-id]') ||
                                  event.target.closest('.product-item') ||
                                  event.target.closest('[id^="1005"]');
                }
                
                if (productElement) {
                    // Try to get product ID from various sources
                    let productId = productElement.id || 
                                  productElement.getAttribute('data-product-id') ||
                                  productElement.getAttribute('data-spm-data');
                    
                    // Extract product ID if it's in a data attribute
                    if (productId && productId.includes('productId')) {
                        try {
                            const parsed = JSON.parse(productId);
                            productId = parsed.productId;
                        } catch (e) {
                            // Try regex extraction
                            const match = productId.match(/productId['":]?[\s]*(\d+)/);
                            if (match) productId = match[1];
                        }
                    }
                    
                    // Validate product ID (AliExpress IDs are usually 13+ digits starting with 1005)
                    if (productId && /^1005\d{9,}$/.test(String(productId))) {
                        console.log('[SSR MODE] ✅ Product clicked:', productId);
                        // Store product ID and add "Get Reviews Now" button to the NEW modal
                        this.addSakuraButton(productId);
                    } else {
                        console.log('[SSR MODE] ⚠️ Product element found but ID not valid:', productId);
                    }
                }
            };
            
            // Attach listener to body with capture phase (runs on EVERY click)
            document.body.addEventListener('click', this.modalClickHandler, true);
            console.log('[SSR MODE] ✅ Product click listener attached - will trigger on every product click');
        }
        
        
        addSakuraButton(productId) {
            console.log('[SSR MODE] Adding Sakura button for product:', productId);
            
            // Store the product ID for later use
            this.currentProductId = productId;
            
            // Try multiple times to add the button as the modal loads
            const tryAddButton = (attempt = 1) => {
                // Try multiple selectors for the review tab
                const selectors = [
                    '#nav-review',
                    '[data-spm="nav-review"]',
                    '.comet-tabs-nav-item[data-spm="nav-review"]',
                    '.nav-review',
                    'a[href*="#nav-review"]',
                    '.product-tabs-nav a[href*="review"]'
                ];
                
                let navReview = null;
                for (const selector of selectors) {
                    navReview = document.querySelector(selector);
                    if (navReview) {
                        console.log(`[SSR MODE] ✅ Found review tab with selector: ${selector} (attempt ${attempt})`);
                        break;
                    }
                }
                
                if (navReview) {
                    // Remove any existing Sakura button
                    const existingButton = navReview.querySelector('.sakura-reviews-btn');
                    if (existingButton) {
                        console.log('[SSR MODE] Removing existing button');
                        existingButton.remove();
                    }
                    
                    // Create the button
                    const btn = this.createSakuraButtonElement(productId);
                    
                    // Try to insert at the beginning of nav-review
                    if (navReview.firstChild) {
                        navReview.insertBefore(btn, navReview.firstChild);
                    } else {
                        navReview.appendChild(btn);
                    }
                    
                    console.log('[SSR MODE] ✅ Sakura "Get Reviews" button added successfully');
                } else if (attempt < 10) {
                    console.log(`[SSR MODE] ⏳ Review tab not found, retry ${attempt + 1}/10...`);
                    setTimeout(() => tryAddButton(attempt + 1), 300);
                } else {
                    console.log('[SSR MODE] ❌ Review tab not found after 10 attempts - trying alternative locations');
                    // Try adding to modal body as fallback
                    const modalBody = document.querySelector('.comet-v2-modal-body') || 
                                     document.querySelector('.product-detail-wrap') ||
                                     document.querySelector('.product-main');
                    if (modalBody) {
                        const btn = this.createSakuraButtonElement(productId);
                        modalBody.insertBefore(btn, modalBody.firstChild);
                        console.log('[SSR MODE] ✅ Button added to modal body as fallback');
                    }
                }
            };
            
            // Start trying immediately and also after delays
            tryAddButton();
            setTimeout(() => tryAddButton(4), 600);
            setTimeout(() => tryAddButton(7), 1500);
        }
        
        createSakuraButtonElement(productId) {
            const btn = document.createElement('button');
            btn.className = 'sakura-reviews-btn';
            btn.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 285.75 285.75" style="flex-shrink: 0;">
                        <g transform="matrix(2.022 0 0 2.022 13.745 -293.54)">
                            <g transform="translate(6.3237 14.723)" fill="#fbc1ea">
                                <path d="m47.885 146.2c-0.2975 4e-3 -0.5912 0.11045-0.87966 0.33699-5.9498 4.6713-11.203 14.597-9.9297 22.903 2.8966 18.896 14.067 26.707 20.463 26.707 6.3959 0 17.566-7.8114 20.463-26.707 1.2732-8.3058-3.98-18.232-9.9297-22.903-3.0769-2.4158-6.6808 8.9461-10.533 8.9461-3.4911 0-6.7777-9.3315-9.6535-9.2831z"/>
                                <path d="m109.16 176.88c-0.0961-0.28158-0.28774-0.52813-0.59233-0.73247-6.2812-4.2151-17.345-6.1439-24.85-2.3663-17.076 8.5939-21.053 21.631-19.076 27.714 1.9764 6.0828 12.857 14.293 31.723 11.208 8.2927-1.3557 16.109-9.4191 18.714-16.521 1.3467-3.6728-10.573-3.5894-11.763-7.2531-1.0788-3.3203 6.7804-9.3296 5.8456-12.05z"/>
                                <path d="m99.014 244.43c0.2381-0.17845 0.41337-0.43686 0.51358-0.78969 2.0678-7.2763 0.48339-18.394-5.4287-24.365-13.45-13.584-27.078-13.338-32.253-9.5786-5.1743 3.7594-9.62 16.645-0.85683 33.634 3.852 7.4679 13.936 12.41 21.495 12.692 3.9092 0.14579 0.14652-11.164 3.2631-13.429 2.8244-2.052 10.968 3.5655 13.266 1.836z"/>
                                <path d="m31.684 255.78c0.24329 0.1713 0.54322 0.25813 0.90974 0.24442 7.5592-0.28196 17.643-5.2244 21.495-12.692 8.7632-16.989 4.3175-29.875-0.85683-33.634-5.1743-3.7594-18.803-4.0057-32.253 9.5786-5.9121 5.9712-7.4965 17.089-5.4287 24.365 1.0694 3.7629 10.663-3.3106 13.78-1.0463 2.8244 2.052-0.0016 11.533 2.3534 13.184z"/>
                                <path d="m-0.044487 195.24c-0.087736 0.28432-0.077638 0.5964 0.048675 0.94074 2.6041 7.1021 10.421 15.165 18.714 16.521 18.866 3.0843 29.747-5.1256 31.723-11.208 1.9764-6.0828-2.0008-19.12-19.076-27.714-7.5058-3.7775-18.569-1.8487-24.85 2.3663-3.2483 2.1798 6.4438 9.1184 5.2533 12.782-1.0788 3.3203-10.969 3.5624-11.812 6.3124z"/>
                            </g>
                            <g transform="matrix(.33942 0 0 -.33942 44.333 286.73)" fill="#ee379a">
                                <path d="m48.763 148.47c-0.27045 4e-3 -0.53745 0.10041-0.79969 0.30635-5.4089 4.2466-10.185 13.27-9.027 20.821 2.6332 17.178 12.788 24.279 18.603 24.279 5.8144 0 15.969-7.1012 18.603-24.279 1.1575-7.5507-3.6182-16.574-9.027-20.821-2.7972-2.1961-6.0735 8.1328-9.5756 8.1328-3.1738 0-6.1616-8.4832-8.7759-8.4392z"/>
                                <path d="m107.39 178.31c-0.0874-0.25598-0.26158-0.48012-0.53848-0.66588-5.7102-3.8319-15.768-5.5854-22.591-2.1512-15.523 7.8126-19.139 19.665-17.342 25.195 1.7968 5.5298 11.688 12.993 28.839 10.189 7.5388-1.2325 14.645-8.5628 17.012-15.019 1.2242-3.3389-9.6116-3.263-10.694-6.5937-0.98074-3.0184 6.164-8.4814 5.3142-10.954z"/>
                                <path d="m97.122 243.28c0.21645-0.16223 0.37579-0.39715 0.46689-0.7179 1.8798-6.6148 0.43945-16.722-4.9352-22.15-12.227-12.349-24.617-12.125-29.321-8.7078-4.704 3.4176-8.7455 15.132-0.77894 30.577 3.5018 6.789 12.669 11.282 19.541 11.538 3.5538 0.13254 0.1332-10.15 2.9664-12.208 2.5676-1.8655 9.9711 3.2414 12.06 1.6691z"/>
                                <path d="m32.156 253.6c0.22118 0.15573 0.49384 0.23467 0.82704 0.2222 6.872-0.25632 16.039-4.7495 19.541-11.538 7.9665-15.445 3.925-27.159-0.77894-30.577-4.704-3.4176-17.093-3.6415-29.321 8.7078-5.3746 5.4283-6.815 15.536-4.9352 22.15 0.97214 3.4208 9.6939-3.0097 12.527-0.95122 2.5676 1.8655-0.0015 10.485 2.1394 11.986z"/>
                                <path d="m2.2688 195c-0.07976 0.25847-0.07058 0.54218 0.04425 0.85522 2.3673 6.4564 9.4735 13.787 17.012 15.019 17.151 2.8039 27.043-4.6596 28.839-10.189 1.7968-5.5298-1.8189-17.382-17.342-25.195-6.8235-3.4341-16.881-1.6807-22.591 2.1512-2.953 1.9817 5.858 8.2894 4.7758 11.62-0.98075 3.0184-9.9721 3.2385-10.738 5.7385z"/>
                            </g>
                        </g>
                    </svg>
                    <span>Get Reviews</span>
                </div>
            `;
            btn.style.cssText = `
                background: white;
                color: #8B4A8B;
                border: 3px solid #ff69b4;
                padding: 12px 24px;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                margin: 16px 0;
                display: block;
                width: 100%;
                transition: all 0.2s;
                box-shadow: 0 2px 8px rgba(255, 105, 180, 0.2);
                position: relative;
                overflow: visible;
            `;
            
            // Add hover effects
            btn.addEventListener('mouseenter', () => {
                btn.style.background = '#ff69b4';
                btn.style.color = 'white';
                btn.style.transform = 'translateY(-1px)';
                btn.style.boxShadow = '0 4px 12px rgba(255, 105, 180, 0.4)';
                btn.style.borderColor = '#ff1493';
            });
            
            btn.addEventListener('mouseleave', () => {
                btn.style.background = 'white';
                btn.style.color = '#8B4A8B';
                btn.style.transform = 'translateY(0)';
                btn.style.boxShadow = '0 2px 8px rgba(255, 105, 180, 0.2)';
                btn.style.borderColor = '#ff69b4';
            });
            
            // Add click handler
            btn.addEventListener('click', () => {
                this.handleProductClick(productId);
            });
            
            return btn;
        }
        // ====================================================================
        // ✅ END OF CRITICAL SSR BUTTON CODE
        // If you see this marker, the SSR button code is intact.
        // ====================================================================
        
        handleProductClick(productId) {
            console.log('[SSR MODE] Processing product click:', productId);
            
            // Store the product data
            this.productData = {
                platform: 'aliexpress',
                productId: productId,
                url: window.location.href
            };
            
            // Create overlay and load reviews
            this.createOverlay();
            this.loadReviews();
        }
        
        detectProduct() {
            const url = window.location.href;
            const hostname = window.location.hostname;
            
            let platform = 'unknown', productId = null;
            
            // Try multiple methods for AliExpress
            if (hostname.includes('aliexpress')) {
                platform = 'aliexpress';
                
                // Method 1: Extract from URL (supports .html extension)
                const urlMatch = url.match(/\/item\/(\d+)(?:\.html)?/);
                if (urlMatch) {
                    productId = urlMatch[1];
                    console.log('[DETECT] Product ID from URL:', productId);
                }
                
                // Method 2: Try window.runParams (AliExpress global data)
                if (!productId && typeof window.runParams === 'object' && window.runParams.data) {
                    const data = window.runParams.data;
                    if (data.feedbackModule && data.feedbackModule.productId) {
                        productId = data.feedbackModule.productId;
                        console.log('[DETECT] Product ID from runParams.feedbackModule:', productId);
                    } else if (data.productId) {
                        productId = data.productId;
                        console.log('[DETECT] Product ID from runParams.data:', productId);
                    } else if (data.storeModule && data.storeModule.productId) {
                        productId = data.storeModule.productId;
                        console.log('[DETECT] Product ID from runParams.storeModule:', productId);
                    }
                }
                
                // Method 3: Try to find in page meta/data attributes
                if (!productId) {
                    const metaProductId = document.querySelector('meta[property="product:id"]') || 
                                       document.querySelector('meta[name="product:id"]');
                    if (metaProductId) {
                        productId = metaProductId.getAttribute('content');
                        console.log('[DETECT] Product ID from meta tag:', productId);
                    }
                }
            } else if (hostname.includes('amazon')) {
                platform = 'amazon';
                const match = url.match(/\/dp\/([A-Z0-9]{10})/);
                if (match) productId = match[1];
            } else if (hostname.includes('ebay')) {
                platform = 'ebay';
                const match = url.match(/\/itm\/(\d+)/);
                if (match) productId = match[1];
            } else if (hostname.includes('walmart')) {
                platform = 'walmart';
                const match = url.match(/\/ip\/[^\/]+\/(\d+)/);
                if (match) productId = match[1];
            }
            
            console.log('[DETECT] Final result:', { platform, productId, url });
            return { platform, productId, url };
        }
        
        createOverlay() {
            // Remove any existing overlay first to prevent duplicates
            const existingOverlay = document.getElementById('reviewking-overlay');
            if (existingOverlay) {
                console.log('[REVIEWKING] Removing existing overlay to prevent duplicates');
                existingOverlay.remove();
            }
            
            const div = document.createElement('div');
            div.id = 'reviewking-overlay';
            div.innerHTML = `
                <style>
                    #reviewking-overlay {
                        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                        background: rgba(0,0,0,0.90); z-index: 999999;
                        display: flex; align-items: center; justify-content: center;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    }
                    #reviewking-panel {
                        background: #1e1e2e; border-radius: 16px; width: 90vw; max-width: 750px;
                        max-height: 90vh; display: flex; flex-direction: column;
                        box-shadow: 0 25px 80px rgba(0,0,0,0.5);
                    }
                    #reviewking-header {
                        background: #1e1e2e;
                        color: white; padding: 20px 28px; border-radius: 16px 16px 0 0;
                        display: flex; justify-content: space-between; align-items: center;
                        border-bottom: 1px solid #2d2d3d;
                    }
                    #reviewking-close {
                        background: #FF2D85; border: none; color: white;
                        font-size: 13px; padding: 10px 24px; border-radius: 8px;
                        cursor: pointer; display: flex; align-items: center; justify-content: center;
                        font-weight: 700; line-height: 1; gap: 6px;
                        transition: all 0.2s;
                    }
                    #reviewking-close:hover { background: #E0186F; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(255, 45, 133, 0.4); }
                    #reviewking-content {
                        flex: 1; padding: 24px 28px; overflow-y: auto;
                        background: #1e1e2e;
                        scrollbar-width: thin;
                        scrollbar-color: #4a4a5e #1e1e2e;
                    }
                    #reviewking-content::-webkit-scrollbar {
                        width: 8px;
                    }
                    #reviewking-content::-webkit-scrollbar-track {
                        background: #1e1e2e;
                    }
                    #reviewking-content::-webkit-scrollbar-thumb {
                        background: #4a4a5e;
                        border-radius: 4px;
                    }
                    #reviewking-content::-webkit-scrollbar-thumb:hover {
                        background: #5a5a6e;
                    }
                    .rk-btn {
                        padding: 12px 20px; border: none; border-radius: 8px;
                        font-size: 13px; font-weight: 600; cursor: pointer;
                        transition: all 0.2s ease;
                        white-space: nowrap;
                    }
                    .rk-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
                    .rk-btn:active { transform: translateY(0); }
                    .rk-btn-primary {
                        background: #667eea; color: white;
                    }
                    .rk-btn-primary:hover { background: #5568d3; }
                    .rk-btn-secondary {
                        background: #2d2d3d; color: #e5e7eb;
                        border: 1px solid #3d3d4d;
                    }
                    .rk-btn-secondary:hover { background: #3d3d4d; border-color: #4d4d5d; }
                    .rk-badge {
                        display: inline-block; padding: 4px 10px; border-radius: 12px;
                        font-size: 10px; font-weight: 700; text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }
                    .rk-badge-success { background: #10b981; color: white; }
                    .rk-badge-info { background: #3b82f6; color: white; }
                    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
                </style>
                <div id="reviewking-panel">
                    <div id="reviewking-header">
                        <div style="flex: 1;">
                            <h2 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.03em; color: #FF2D85;">🌸 Sakura Reviews</h2>
                            <p style="margin: 8px 0 0; opacity: 0.7; font-size: 13px; font-weight: 500; color: #9ca3af;">
                                Beautiful reviews, naturally • Powered by AI
                            </p>
                        </div>
                        <button id="reviewking-close">✕ Close</button>
                    </div>
                    <div id="reviewking-content">
                        <div style="text-align: center; padding: 40px;">
                            <div style="width: 48px; height: 48px; border: 4px solid #e5e7eb;
                                border-top-color: #667eea; border-radius: 50%; margin: 0 auto 16px;
                                animation: spin 1s linear infinite;"></div>
                            <p style="color: #6b7280; margin: 0;">Loading reviews with AI analysis...</p>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(div);
            
            // Attach close button event listener
            const closeBtn = document.getElementById('reviewking-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    this.close();
                });
            }
        }
        
        setupProductSearch() {
            const searchInput = document.getElementById('product-search-input');
            const dropdown = document.getElementById('product-dropdown');
            
            // Check if elements exist
            if (!searchInput || !dropdown) {
                console.log('Product search elements not found yet');
                return;
            }
            
            // Add search input event listener (only once)
            if (searchInput.hasAttribute('data-listener-attached')) {
                return;
            }
            searchInput.setAttribute('data-listener-attached', 'true');
            
            searchInput.addEventListener('input', (e) => {
                const query = e.target.value.trim();
                
                // Clear previous timeout
                if (this.searchTimeout) {
                    clearTimeout(this.searchTimeout);
                }
                
                const dropdownElement = document.getElementById('product-dropdown');
                if (!dropdownElement) return;
                
                if (query.length < 2) {
                    dropdownElement.style.display = 'none';
                    return;
                }
                
                // Debounce search
                this.searchTimeout = setTimeout(() => {
                    this.searchProducts(query);
                }, 300);
            });
            
            // Hide dropdown when clicking outside (only once)
            if (!document.body.hasAttribute('data-dropdown-listener')) {
                document.body.setAttribute('data-dropdown-listener', 'true');
            document.addEventListener('click', (e) => {
                    const dropdownElement = document.getElementById('product-dropdown');
                    if (dropdownElement && !e.target.closest('#product-search-input') && !e.target.closest('#product-dropdown')) {
                        dropdownElement.style.display = 'none';
                }
            });
            }
        }
        
        async searchProducts(query) {
            const dropdown = document.getElementById('product-dropdown');
            
            if (!dropdown) {
                console.error('Dropdown element not found');
                return;
            }
            
            try {
                dropdown.innerHTML = '<div style="padding: 12px; color: #666;">Searching...</div>';
                dropdown.style.display = 'block';
                
                const response = await fetch(`${API_URL}/shopify/products/search?q=${encodeURIComponent(query)}`);
                const result = await response.json();
                
                if (result.success && result.products.length > 0) {
                    dropdown.innerHTML = result.products.map(product => `
                        <div class="product-option" data-product-id="${product.id}" 
                             data-product-title="${product.title}"
                             style="padding: 12px; border-bottom: 1px solid #f0f0f0; cursor: pointer; 
                                    display: flex; align-items: center; gap: 12px;"
                             onmouseover="this.style.background='#f8f9fa'" 
                             onmouseout="this.style.background='white'"
                             onclick="window.reviewKingClient.selectProduct('${product.id}', '${product.title.replace(/'/g, "\\'")}', '${product.image || ""}')">
                            ${product.image ? `<img src="${product.image}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;">` : '<div style="width: 40px; height: 40px; background: #f0f0f0; border-radius: 4px;"></div>'}
                            <div>
                                <div style="font-weight: 500; color: #333; font-size: 14px;">${product.title}</div>
                                <div style="font-size: 12px; color: #666;">ID: ${product.id}</div>
                            </div>
                        </div>
                    `).join('');
                } else {
                    dropdown.innerHTML = '<div style="padding: 12px; color: #666;">No products found</div>';
                }
            } catch (error) {
                dropdown.innerHTML = '<div style="padding: 12px; color: #e74c3c;">Search failed. Check Shopify API configuration.</div>';
            }
        }
        
        selectProduct(productId, productTitle, productImage) {
            this.selectedProduct = { id: productId, title: productTitle, image: productImage || null };
            
            // Hide dropdown and clear input
            const dropdown = document.getElementById('product-dropdown');
            const searchInput = document.getElementById('product-search-input');
            const selectedDiv = document.getElementById('selected-product');
            
            if (dropdown) dropdown.style.display = 'none';
            if (searchInput) searchInput.value = '';
            
            if (!selectedDiv) {
                console.error('Selected product div not found');
                return;
            }
            
            // Show selected product with thumbnail
            selectedDiv.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        ${productImage ? `<img src="${productImage}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 6px; flex-shrink: 0;">` : '<div style="width: 50px; height: 50px; background: rgba(255,255,255,0.2); border-radius: 6px; flex-shrink: 0;"></div>'}
                        <div>
                            <div style="font-weight: 500;">✔ Target Product Selected</div>
                            <div style="opacity: 0.8; font-size: 12px;">${productTitle}</div>
                        </div>
                    </div>
                    <button onclick="window.reviewKingClient.clearProduct()" 
                            style="background: rgba(255,255,255,0.2); border: none; color: white; 
                                   padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                        Change
                    </button>
                </div>
            `;
            selectedDiv.style.display = 'block';
            
            // Refresh current review display to show import buttons
            if (this.reviews && this.reviews.length > 0) {
                this.displayReview();
            }
        }
        
        clearProduct() {
            this.selectedProduct = null;
            
            const selectedDiv = document.getElementById('selected-product');
            if (selectedDiv) {
                selectedDiv.style.display = 'none';
            }
            
            // Refresh current review display to hide import buttons
            if (this.reviews && this.reviews.length > 0) {
                this.displayReview();
            }
        }
        
        async loadReviews(page = 1) {
            try {
                console.log('Loading reviews...', { productId: this.productData.productId, platform: this.productData.platform });
                
                // IMPROVED: Try client-side scraping first (from app_ultimate.py)
                const scrapedData = this.scrapePageData();
                
                const params = new URLSearchParams({
                    productId: this.productData.productId,
                    platform: this.productData.platform,
                    page: page,
                    per_page: 150,  // Load 150 reviews to account for duplicates
                    id: this.sessionId
                });
                
                const url = `${API_URL}/admin/reviews/import/url?${params}`;
                console.log('Fetching:', url);
                
                // Use GET request (like v12) - server always does server-side scraping
                const response = await fetch(url, {
                    method: 'GET'
                });
                
                console.log('Response status:', response.status);
                
                const result = await response.json();
                console.log('Result:', result);
                
                // Save session_id if returned (for caching)
                if (result.session_id) {
                    this.sessionId = result.session_id;
                    console.log(`Session saved: ${this.sessionId.substring(0, 8)}...`);
                }
                
                if (result.success) {
                    this.allReviews = result.reviews;  // Store all reviews
                    this.currentIndex = 0;
                    this.pagination = result.pagination;
                    
                    // Calculate stats on client side (like v12) - more reliable
                    // Normalize property names from server
                    const serverStats = result.stats || {};
                    const avgQuality = serverStats.average_quality || serverStats.avg_quality || 0;
                    const avgRating = serverStats.average_rating || serverStats.avg_rating || 0;
                    
                    // Calculate rating counts (normalize AliExpress 0-100 to 1-5 scale) - like v12
                    const reviews45star = this.allReviews.filter(r => {
                        const rating = r.rating > 5 ? Math.ceil((r.rating / 100) * 5) : r.rating;
                        return rating === 4 || rating === 5;
                    });
                    const reviews3star = this.allReviews.filter(r => {
                        const rating = r.rating > 5 ? Math.ceil((r.rating / 100) * 5) : r.rating;
                        return rating === 3;
                    });
                    
                    // Store server stats (like v12 - only basic fields)
                    this.stats = {
                        ...this.stats,  // Keep existing stats (with defaults)
                        total: this.allReviews.length,
                        with_photos: this.allReviews.filter(r => r.images && r.images.length > 0).length,
                        ai_recommended: this.allReviews.filter(r => r.ai_recommended).length,
                        average_quality: avgQuality,
                        average_rating: avgRating
                    };
                    console.log('All reviews loaded:', this.allReviews.length);
                    
                    // Smart fallback: If AI recommended has < 3 reviews, show All with smart sorting
                    const aiRecommendedCount = this.allReviews.filter(r => r.ai_recommended).length;
                    if (this.currentFilter === 'ai_recommended' && aiRecommendedCount < 3) {
                        console.log(`[Smart Fallback] Only ${aiRecommendedCount} AI recommended reviews, falling back to 'all' with smart sorting`);
                        this.currentFilter = 'all';
                        this.useSmartSort = true;  // Flag for smart sorting
                    } else {
                        this.useSmartSort = false;
                    }
                    
                    this.applyFilter();  // Apply current filter and display (will recalculate reviews_45star and reviews_3star)
                } else {
                    console.error('Error loading reviews:', result.error);
                    // Show user-friendly error message
                    const errorMessage = result.message || result.error || 'Failed to load reviews';
                    this.showError(errorMessage);
                }
            } catch (error) {
                console.error('Exception loading reviews:', error);
                this.showError('Failed to load reviews: ' + error.message);
            }
        }
        
        // IMPROVED: Client-side scraping from app_ultimate.py
        scrapePageData() {
            const hostname = window.location.hostname;
            
            if (hostname.includes('aliexpress')) {
                return this.scrapeAliExpress();
            } else if (hostname.includes('amazon')) {
                return this.scrapeAmazon();
            }
            
            return null;
        }
        
        scrapeAliExpress() {
            try {
                console.log('=== ALIEXPRESS SCRAPING DEBUG ===');
                console.log('window.runParams exists?', typeof window.runParams);
                console.log('window.runParams?.data:', window.runParams?.data ? 'YES' : 'NO');
                
                // Method 1: Extract from window.runParams (EXACTLY like Loox!)
                const runParams = window.runParams?.data || window.runParams || {};
                const feedbackModule = runParams.feedbackModule || runParams.productDetailReviewSummary || {};
                
                console.log('feedbackModule exists?', Object.keys(feedbackModule).length > 0);
                console.log('feedbackList exists?', feedbackModule.feedbackList ? 'YES' : 'NO');
                console.log('feedbackList length:', feedbackModule.feedbackList?.length || 0);
                
                // Extract product info
                const productId = runParams.productId || 
                                feedbackModule.productId ||
                                this.extractProductIdFromUrl();
                
                const sellerId = feedbackModule.sellerAdminSeq || 
                                runParams.sellerAdminSeq ||
                                runParams.adminSeq;
                
                console.log('Extracted productId:', productId);
                console.log('Extracted sellerId:', sellerId);
                
                // Extract reviews from feedbackModule
                let reviews = [];
                
                if (feedbackModule.feedbackList && feedbackModule.feedbackList.length > 0) {
                    console.log(`✅ Found ${feedbackModule.feedbackList.length} reviews in runParams`);
                    
                    reviews = feedbackModule.feedbackList.map((r, idx) => {
                        // IMPROVED: Better image extraction - exclude avatars
                        const reviewImages = [];
                        
                        if (r.images && Array.isArray(r.images)) {
                            r.images.forEach(img => {
                                let imgUrl = null;
                                
                                if (typeof img === 'string') {
                                    imgUrl = img;
                                } else if (img && typeof img === 'object') {
                                    imgUrl = img.imgUrl || img.url || img.src;
                                }
                                
                                // FILTER OUT AVATARS AND JUNK
                                if (imgUrl && 
                                    imgUrl.includes('aliexpress') && 
                                    (imgUrl.includes('/kf/') || imgUrl.includes('ae-pic')) &&
                                    !imgUrl.includes('avatar') && 
                                    !imgUrl.includes('icon') &&
                                    !imgUrl.includes('placeholder')) {
                                    reviewImages.push(imgUrl);
                                }
                            });
                        }
                        
                        console.log(`Review ${idx}: "${r.buyerFeedback?.substring(0, 30)}..." - ${reviewImages.length} photos`);
                        
                        return {
                            id: r.evaluationId || Math.random().toString(36),
                            reviewer_name: r.buyerName || 'Anonymous',
                            text: r.buyerFeedback || '',
                            rating: parseInt(r.buyerEval || 5),
                            date: r.evalTime || new Date().toISOString().split('T')[0],
                            country: r.buyerCountry || 'Unknown',
                            verified: true,
                            images: reviewImages,
                            platform: 'aliexpress'
                        };
                    });
                }
                
                // Method 2: Try DOM scraping if runParams failed
                if (reviews.length === 0) {
                    console.warn('⚠️ No reviews in feedbackList, trying DOM scraping...');
                    reviews = this.scrapeAliExpressDom();
                }
                
                console.log(`🎯 Total reviews extracted: ${reviews.length}`);
                
                return {
                    platform: 'aliexpress',
                    productId: productId,
                    sellerId: sellerId,
                    reviews: reviews,
                    source: reviews.length > 0 ? (feedbackModule.feedbackList ? 'runParams' : 'dom') : 'none'
                };
                
            } catch (error) {
                console.error('❌ AliExpress scrape error:', error);
                return { platform: 'aliexpress', reviews: [], error: error.message };
            }
        }
        
        scrapeAliExpressDom() {
            // IMPROVED: Better DOM scraping from app_ultimate.py
            const reviews = [];
            
            try {
                console.log('🔍 Starting DOM scraping...');
                
                const selectors = [
                    '.list--itemWrap--ARYTMbR',
                    '[class*="list"][class*="itemWrap"]',
                    '[data-pl="product-customer-reviews"] [class*="review"]',
                    'div[class*="review-item"]'
                ];
                
                let reviewElements = [];
                for (const selector of selectors) {
                    reviewElements = document.querySelectorAll(selector);
                    if (reviewElements.length > 0 && reviewElements.length < 100) {
                        console.log(`✅ Found ${reviewElements.length} REAL reviews with: ${selector}`);
                        break;
                    }
                }
                
                if (reviewElements.length === 0) {
                    console.warn('No review elements found, trying body search...');
                    reviewElements = Array.from(document.querySelectorAll('div')).filter(el => {
                        const text = el.textContent || '';
                        const hasRating = el.querySelector('[class*="star"], [class*="rating"]');
                        const hasDate = /\d{1,2}\s+\w+\s+\d{4}/.test(text) || /\d{4}-\d{2}-\d{2}/.test(text);
                        return hasRating && hasDate && text.length > 50 && text.length < 2000;
                    });
                    console.log(`Body search found ${reviewElements.length} potential reviews`);
                }
                
                reviewElements.forEach((el, index) => {
                    try {
                        const infoEl = el.querySelector('.list--itemInfo--URmp38d, [class*="itemInfo"]');
                        const infoText = infoEl?.textContent?.trim() || '';
                        const infoParts = infoText.split('|').map(s => s.trim());
                        const reviewer_name = infoParts[0] || 'Customer';
                        const dateText = infoParts[1] || '';
                        
                        const textEl = el.querySelector('.list--itemReview--xQUhO78, [class*="itemReview"]');
                        let text = textEl?.textContent?.trim() || '';
                        
                        if (!text || text.length < 5) {
                            return;
                        }
                        
                        let rating = 5;
                        const starContainer = el.querySelector('.stars--box--d_zcrGb, [class*="stars"]');
                        if (starContainer) {
                            const filledStars = starContainer.querySelectorAll('[class*="starreviewfilled"]');
                            if (filledStars.length > 0) {
                                rating = filledStars.length;
                            }
                        }
                        
                        let date = new Date().toISOString().split('T')[0];
                        if (dateText) {
                            try {
                                const parsedDate = new Date(dateText);
                                if (!isNaN(parsedDate.getTime())) {
                                    date = parsedDate.toISOString().split('T')[0];
                                }
                            } catch(e) {}
                        }
                        
                        // IMPROVED: Better image extraction - exclude avatars
                        const images = [];
                        const imgElements = el.querySelectorAll('img');
                        imgElements.forEach(img => {
                            const isAvatar = img.closest('.list--itemPhoto--ZgH4_cc') || 
                                           img.closest('[class*="itemPhoto"]');
                            if (isAvatar) return;
                            
                            const src = img.src || img.dataset.src || img.getAttribute('data-src');
                            
                            if (src && 
                                (src.includes('/kf/') || src.includes('ae-pic') || src.includes('ae01.alicdn')) &&
                                !src.includes('avatar') && 
                                !src.includes('icon') &&
                                !src.includes('logo') &&
                                src.length > 50) {
                                images.push(src);
                            }
                        });
                        
                        if (text && text.length > 10) {
                            reviews.push({
                                id: 'dom_' + index,
                                reviewer_name: reviewer_name,
                                text: text.substring(0, 500),
                                rating: rating,
                                date: date,
                                country: 'Unknown',
                                verified: true,
                                images: images,
                                platform: 'aliexpress'
                            });
                            console.log(`✅ Scraped review ${index}: ${reviewer_name} - "${text.substring(0,30)}..." (${images.length} photos)`);
                        }
                    } catch (reviewError) {
                        console.error(`Error processing review ${index}:`, reviewError);
                    }
                });
                
                console.log(`🎯 DOM scraping complete: ${reviews.length} reviews extracted`);
            } catch (error) {
                console.error('❌ DOM scrape error:', error);
            }
            
            return reviews;
        }
        
        scrapeAmazon() {
            try {
                const asin = window.location.pathname.match(/\/dp\/([A-Z0-9]{10})/)?.[1];
                
                const reviews = [];
                const reviewElements = document.querySelectorAll('[data-hook="review"]');
                
                reviewElements.forEach((el, index) => {
                    const nameEl = el.querySelector('[class*="author"]');
                    const textEl = el.querySelector('[data-hook="review-body"]');
                    const ratingEl = el.querySelector('[data-hook="review-star-rating"]');
                    
                    const images = [];
                    el.querySelectorAll('img[data-hook="review-image"]').forEach(img => {
                        images.push(img.src);
                    });
                    
                    if (textEl) {
                        reviews.push({
                            id: 'amz_' + index,
                            reviewer_name: nameEl?.textContent?.trim() || 'Amazon Customer',
                            text: textEl.textContent?.trim() || '',
                            rating: parseInt(ratingEl?.textContent?.match(/\d/)?.[0] || 5),
                            date: new Date().toISOString().split('T')[0],
                            country: 'US',
                            verified: el.querySelector('[data-hook="avp-badge"]') !== null,
                            images: images,
                            platform: 'amazon'
                        });
                    }
                });
                
                return {
                    platform: 'amazon',
                    productId: asin,
                    reviews: reviews
                };
                
            } catch (error) {
                console.error('Amazon scrape error:', error);
                return { platform: 'amazon', reviews: [], error: error.message };
            }
        }
        
        extractProductIdFromUrl() {
            const match = window.location.pathname.match(/\/item\/(\d+)/);
            return match ? match[1] : null;
        }
        
        applyFilter() {
            // Step 1: Apply star rating filter
            let filtered = [...this.allReviews];
            
            if (this.currentFilter === 'photos') {
                filtered = filtered.filter(r => r.images && r.images.length > 0);
            } else if (this.currentFilter === 'ai_recommended') {
                filtered = filtered.filter(r => r.ai_recommended);
            } else if (this.currentFilter === '4-5stars') {
                // Rating >= 70 on the 0-100 scale (like old code)
                filtered = filtered.filter(r => r.rating >= 70);
            } else if (this.currentFilter === '3stars') {
                // Rating 50-69 on the 0-100 scale
                filtered = filtered.filter(r => r.rating >= 50 && r.rating < 70);
            } else if (this.currentFilter === '5stars') {
                // Rating >= 90 on the 0-100 scale
                filtered = filtered.filter(r => r.rating >= 90);
            }
            
            // Step 2: Apply country filter
            if (this.selectedCountry !== 'all') {
                filtered = filtered.filter(r => r.country === this.selectedCountry);
            }
            
            // Step 3: Smart sorting - prioritize photos, then rating, then quality
            // Applied when falling back from AI recommended OR always for best UX
            filtered = this.smartSort(filtered);
            
            this.reviews = filtered;
            
            console.log(`[Filter] Applied filter "${this.currentFilter}" + country "${this.selectedCountry}": ${this.reviews.length} of ${this.allReviews.length} reviews`);
            
            // Reset to first review after filtering
            this.currentIndex = 0;
            
            // Update stats based on all reviews (not filtered) - like v12
            // Calculate rating counts (normalize AliExpress 0-100 to 1-5 scale)
            const reviews45star = this.allReviews.filter(r => {
                const rating = r.rating > 5 ? Math.ceil((r.rating / 100) * 5) : r.rating;
                return rating === 4 || rating === 5;
            });
            const reviews3star = this.allReviews.filter(r => {
                const rating = r.rating > 5 ? Math.ceil((r.rating / 100) * 5) : r.rating;
                return rating === 3;
            });
            
            this.stats = {
                ...this.stats,
                total: this.allReviews.length,
                with_photos: this.allReviews.filter(r => r.images && r.images.length > 0).length,
                ai_recommended: this.allReviews.filter(r => r.ai_recommended).length,
                reviews_45star: reviews45star.length,
                reviews_3star: reviews3star.length
            };
            
            this.displayReview();
        }
        
        smartSort(reviews) {
            // Smart sorting algorithm: Best reviews first
            // Priority: AI Recommended > Has Text Content > Has Photos > High Rating > Quality Score
            return reviews.sort((a, b) => {
                // 1. AI Recommended first (best quality reviews)
                if (a.ai_recommended && !b.ai_recommended) return -1;
                if (!a.ai_recommended && b.ai_recommended) return 1;
                
                // 2. HAS TEXT CONTENT - Reviews with actual text before empty ones
                const aText = (a.text || a.body || '').trim();
                const bText = (b.text || b.body || '').trim();
                const aHasText = aText.length >= 10;  // At least 10 chars = meaningful content
                const bHasText = bText.length >= 10;
                if (aHasText && !bHasText) return -1;
                if (!aHasText && bHasText) return 1;
                
                // 3. Has photos (prioritize reviews with more photos)
                const aPhotos = (a.images && a.images.length) || 0;
                const bPhotos = (b.images && b.images.length) || 0;
                if (aPhotos > 0 && bPhotos === 0) return -1;
                if (aPhotos === 0 && bPhotos > 0) return 1;
                if (aPhotos !== bPhotos) return bPhotos - aPhotos;  // More photos first
                
                // 4. Higher rating first
                const aRating = a.rating || 0;
                const bRating = b.rating || 0;
                if (aRating !== bRating) return bRating - aRating;
                
                // 5. Longer text (more detailed reviews) first
                if (aText.length !== bText.length) return bText.length - aText.length;
                
                // 6. Higher quality score as tiebreaker
                const aQuality = a.quality_score || 0;
                const bQuality = b.quality_score || 0;
                return bQuality - aQuality;
            });
        }
        
        setFilter(filter) {
            console.log(`[Filter] Changing filter from "${this.currentFilter}" to "${filter}"`);
            this.currentFilter = filter;
            this.applyFilter();
        }
        
        setCountry(country) {
            console.log(`[Country] Changing country filter from "${this.selectedCountry}" to "${country}"`);
            this.selectedCountry = country;
            this.applyFilter();
        }
        
        toggleTranslation() {
            this.showTranslations = !this.showTranslations;
            console.log(`[Translation] Toggled to: ${this.showTranslations}`);
            this.displayReview();  // Refresh display without re-filtering
        }
        
        renderStars(rating) {
            // Convert rating from 0-100 scale to 1-5 stars
            const starCount = Math.ceil(rating / 20);
            const filledStars = Math.min(starCount, 5);
            const emptyStars = 5 - filledStars;
            
            // AliExpress SVG stars
            const filledStarSVG = '<svg viewBox="0 0 1024 1024" width="1em" height="1em" fill="currentColor" aria-hidden="false" focusable="false" style="display: inline-block; vertical-align: middle; margin-right: 2px;"><path d="M463.488 157.141333c18.986667-41.557333 78.016-41.557333 97.024 0l91.498667 200.170667 196.544 25.6c42.922667 5.589333 61.653333 57.28 32.256 89.088L738.56 625.92l36.629333 201.258667c7.850667 43.136-36.8 76.8-76.096 57.386666L512 792.064l-187.093333 92.458667c-39.296 19.413333-83.968-14.229333-76.096-57.365334l36.629333-201.258666-142.272-153.92c-29.376-31.786667-10.645333-83.498667 32.277333-89.088l196.544-25.6 91.52-200.170667z"></path></svg>';
            const emptyStarSVG = '<svg viewBox="0 0 1024 1024" width="1em" height="1em" fill="currentColor" aria-hidden="false" focusable="false" style="display: inline-block; vertical-align: middle; margin-right: 2px; opacity: 0.3;"><path d="M512 204.970667l-84.266667 184.32a53.333333 53.333333 0 0 1-41.6 30.72l-181.952 23.68 131.882667 142.698666a53.333333 53.333333 0 0 1 13.290667 45.738667l-33.792 185.642667 172.8-85.397334a53.333333 53.333333 0 0 1 47.274666 0l172.8 85.397334-33.792-185.642667a53.333333 53.333333 0 0 1 13.290667-45.76L819.84 443.733333l-181.930667-23.701333a53.333333 53.333333 0 0 1-41.621333-30.72L512 204.970667z m-48.512-47.829334c18.986667-41.557333 78.016-41.557333 97.024 0l91.498667 200.170667 196.544 25.6c42.922667 5.589333 61.653333 57.28 32.256 89.088L738.56 625.92l36.629333 201.258667c7.850667 43.136-36.8 76.8-76.096 57.386666L512 792.064l-187.093333 92.458667c-39.296 19.413333-83.968-14.229333-76.096-57.365334l36.629333-201.258666-142.272-153.92c-29.376-31.786667-10.645333-83.498667 32.277333-89.088l196.544-25.6 91.52-200.170667z"></path></svg>';
            
            return filledStarSVG.repeat(filledStars) + emptyStarSVG.repeat(emptyStars);
        }
        
        getCountryMap() {
            // Country code to flag/name mapping
            return {
                'AD': {'flag': '🇦🇩', 'name': 'Andorra'}, 'AE': {'flag': '🇦🇪', 'name': 'United Arab Emirates'}, 'AF': {'flag': '🇦🇫', 'name': 'Afghanistan'}, 'AG': {'flag': '🇦🇬', 'name': 'Antigua and Barbuda'}, 'AI': {'flag': '🇦🇮', 'name': 'Anguilla'}, 'AL': {'flag': '🇦🇱', 'name': 'Albania'}, 'AM': {'flag': '🇦🇲', 'name': 'Armenia'}, 'AO': {'flag': '🇦🇴', 'name': 'Angola'}, 'AR': {'flag': '🇦🇷', 'name': 'Argentina'}, 'AS': {'flag': '🇦🇸', 'name': 'American Samoa'}, 'AT': {'flag': '🇦🇹', 'name': 'Austria'}, 'AU': {'flag': '🇦🇺', 'name': 'Australia'}, 'AW': {'flag': '🇦🇼', 'name': 'Aruba'}, 'AZ': {'flag': '🇦🇿', 'name': 'Azerbaijan'},
                'BA': {'flag': '🇧🇦', 'name': 'Bosnia and Herzegovina'}, 'BB': {'flag': '🇧🇧', 'name': 'Barbados'}, 'BD': {'flag': '🇧🇩', 'name': 'Bangladesh'}, 'BE': {'flag': '🇧🇪', 'name': 'Belgium'}, 'BF': {'flag': '🇧🇫', 'name': 'Burkina Faso'}, 'BG': {'flag': '🇧🇬', 'name': 'Bulgaria'}, 'BH': {'flag': '🇧🇭', 'name': 'Bahrain'}, 'BI': {'flag': '🇧🇮', 'name': 'Burundi'}, 'BJ': {'flag': '🇧🇯', 'name': 'Benin'}, 'BM': {'flag': '🇧🇲', 'name': 'Bermuda'}, 'BN': {'flag': '🇧🇳', 'name': 'Brunei'}, 'BO': {'flag': '🇧🇴', 'name': 'Bolivia'}, 'BR': {'flag': '🇧🇷', 'name': 'Brazil'}, 'BS': {'flag': '🇧🇸', 'name': 'Bahamas'}, 'BT': {'flag': '🇧🇹', 'name': 'Bhutan'}, 'BW': {'flag': '🇧🇼', 'name': 'Botswana'}, 'BY': {'flag': '🇧🇾', 'name': 'Belarus'}, 'BZ': {'flag': '🇧🇿', 'name': 'Belize'},
                'CA': {'flag': '🇨🇦', 'name': 'Canada'}, 'CD': {'flag': '🇨🇩', 'name': 'Congo'}, 'CF': {'flag': '🇨🇫', 'name': 'Central African Republic'}, 'CG': {'flag': '🇨🇬', 'name': 'Congo'}, 'CH': {'flag': '🇨🇭', 'name': 'Switzerland'}, 'CI': {'flag': '🇨🇮', 'name': "Côte D'Ivoire"}, 'CK': {'flag': '🇨🇰', 'name': 'Cook Islands'}, 'CL': {'flag': '🇨🇱', 'name': 'Chile'}, 'CM': {'flag': '🇨🇲', 'name': 'Cameroon'}, 'CN': {'flag': '🇨🇳', 'name': 'China'}, 'CO': {'flag': '🇨🇴', 'name': 'Colombia'}, 'CR': {'flag': '🇨🇷', 'name': 'Costa Rica'}, 'CU': {'flag': '🇨🇺', 'name': 'Cuba'}, 'CV': {'flag': '🇨🇻', 'name': 'Cape Verde'}, 'CW': {'flag': '🇨🇼', 'name': 'Curaçao'}, 'CY': {'flag': '🇨🇾', 'name': 'Cyprus'}, 'CZ': {'flag': '🇨🇿', 'name': 'Czech Republic'},
                'DE': {'flag': '🇩🇪', 'name': 'Germany'}, 'DJ': {'flag': '🇩🇯', 'name': 'Djibouti'}, 'DK': {'flag': '🇩🇰', 'name': 'Denmark'}, 'DM': {'flag': '🇩🇲', 'name': 'Dominica'}, 'DO': {'flag': '🇩🇴', 'name': 'Dominican Republic'}, 'DZ': {'flag': '🇩🇿', 'name': 'Algeria'},
                'EC': {'flag': '🇪🇨', 'name': 'Ecuador'}, 'EE': {'flag': '🇪🇪', 'name': 'Estonia'}, 'EG': {'flag': '🇪🇬', 'name': 'Egypt'}, 'ER': {'flag': '🇪🇷', 'name': 'Eritrea'}, 'ES': {'flag': '🇪🇸', 'name': 'Spain'}, 'ET': {'flag': '🇪🇹', 'name': 'Ethiopia'},
                'FI': {'flag': '🇫🇮', 'name': 'Finland'}, 'FJ': {'flag': '🇫🇯', 'name': 'Fiji'}, 'FR': {'flag': '🇫🇷', 'name': 'France'},
                'GA': {'flag': '🇬🇦', 'name': 'Gabon'}, 'GB': {'flag': '🇬🇧', 'name': 'United Kingdom'}, 'GD': {'flag': '🇬🇩', 'name': 'Grenada'}, 'GE': {'flag': '🇬🇪', 'name': 'Georgia'}, 'GH': {'flag': '🇬🇭', 'name': 'Ghana'}, 'GI': {'flag': '🇬🇮', 'name': 'Gibraltar'}, 'GL': {'flag': '🇬🇱', 'name': 'Greenland'}, 'GM': {'flag': '🇬🇲', 'name': 'Gambia'}, 'GN': {'flag': '🇬🇳', 'name': 'Guinea'}, 'GR': {'flag': '🇬🇷', 'name': 'Greece'}, 'GT': {'flag': '🇬🇹', 'name': 'Guatemala'}, 'GU': {'flag': '🇬🇺', 'name': 'Guam'}, 'GY': {'flag': '🇬🇾', 'name': 'Guyana'},
                'HK': {'flag': '🇭🇰', 'name': 'Hong Kong'}, 'HN': {'flag': '🇭🇳', 'name': 'Honduras'}, 'HR': {'flag': '🇭🇷', 'name': 'Croatia'}, 'HT': {'flag': '🇭🇹', 'name': 'Haiti'}, 'HU': {'flag': '🇭🇺', 'name': 'Hungary'},
                'ID': {'flag': '🇮🇩', 'name': 'Indonesia'}, 'IE': {'flag': '🇮🇪', 'name': 'Ireland'}, 'IL': {'flag': '🇮🇱', 'name': 'Israel'}, 'IN': {'flag': '🇮🇳', 'name': 'India'}, 'IQ': {'flag': '🇮🇶', 'name': 'Iraq'}, 'IR': {'flag': '🇮🇷', 'name': 'Iran'}, 'IS': {'flag': '🇮🇸', 'name': 'Iceland'}, 'IT': {'flag': '🇮🇹', 'name': 'Italy'},
                'JM': {'flag': '🇯🇲', 'name': 'Jamaica'}, 'JO': {'flag': '🇯🇴', 'name': 'Jordan'}, 'JP': {'flag': '🇯🇵', 'name': 'Japan'},
                'KE': {'flag': '🇰🇪', 'name': 'Kenya'}, 'KG': {'flag': '🇰🇬', 'name': 'Kyrgyzstan'}, 'KH': {'flag': '🇰🇭', 'name': 'Cambodia'}, 'KI': {'flag': '🇰🇮', 'name': 'Kiribati'}, 'KM': {'flag': '🇰🇲', 'name': 'Comoros'}, 'KN': {'flag': '🇰🇳', 'name': 'Saint Kitts and Nevis'}, 'KP': {'flag': '🇰🇵', 'name': 'North Korea'}, 'KR': {'flag': '🇰🇷', 'name': 'South Korea'}, 'KW': {'flag': '🇰🇼', 'name': 'Kuwait'}, 'KY': {'flag': '🇰🇾', 'name': 'Cayman Islands'}, 'KZ': {'flag': '🇰🇿', 'name': 'Kazakhstan'},
                'LA': {'flag': '🇱🇦', 'name': 'Laos'}, 'LB': {'flag': '🇱🇧', 'name': 'Lebanon'}, 'LC': {'flag': '🇱🇨', 'name': 'Saint Lucia'}, 'LI': {'flag': '🇱🇮', 'name': 'Liechtenstein'}, 'LK': {'flag': '🇱🇰', 'name': 'Sri Lanka'}, 'LR': {'flag': '🇱🇷', 'name': 'Liberia'}, 'LS': {'flag': '🇱🇸', 'name': 'Lesotho'}, 'LT': {'flag': '🇱🇹', 'name': 'Lithuania'}, 'LU': {'flag': '🇱🇺', 'name': 'Luxembourg'}, 'LV': {'flag': '🇱🇻', 'name': 'Latvia'}, 'LY': {'flag': '🇱🇾', 'name': 'Libya'},
                'MA': {'flag': '🇲🇦', 'name': 'Morocco'}, 'MC': {'flag': '🇲🇨', 'name': 'Monaco'}, 'MD': {'flag': '🇲🇩', 'name': 'Moldova'}, 'ME': {'flag': '🇲🇪', 'name': 'Montenegro'}, 'MG': {'flag': '🇲🇬', 'name': 'Madagascar'}, 'MK': {'flag': '🇲🇰', 'name': 'Macedonia'}, 'ML': {'flag': '🇲🇱', 'name': 'Mali'}, 'MM': {'flag': '🇲🇲', 'name': 'Myanmar'}, 'MN': {'flag': '🇲🇳', 'name': 'Mongolia'}, 'MO': {'flag': '🇲🇴', 'name': 'Macao'}, 'MR': {'flag': '🇲🇷', 'name': 'Mauritania'}, 'MS': {'flag': '🇲🇸', 'name': 'Montserrat'}, 'MT': {'flag': '🇲🇹', 'name': 'Malta'}, 'MU': {'flag': '🇲🇺', 'name': 'Mauritius'}, 'MV': {'flag': '🇲🇻', 'name': 'Maldives'}, 'MW': {'flag': '🇲🇼', 'name': 'Malawi'}, 'MX': {'flag': '🇲🇽', 'name': 'Mexico'}, 'MY': {'flag': '🇲🇾', 'name': 'Malaysia'}, 'MZ': {'flag': '🇲🇿', 'name': 'Mozambique'},
                'NA': {'flag': '🇳🇦', 'name': 'Namibia'}, 'NC': {'flag': '🇳🇨', 'name': 'New Caledonia'}, 'NE': {'flag': '🇳🇪', 'name': 'Niger'}, 'NG': {'flag': '🇳🇬', 'name': 'Nigeria'}, 'NI': {'flag': '🇳🇮', 'name': 'Nicaragua'}, 'NL': {'flag': '🇳🇱', 'name': 'Netherlands'}, 'NO': {'flag': '🇳🇴', 'name': 'Norway'}, 'NP': {'flag': '🇳🇵', 'name': 'Nepal'}, 'NR': {'flag': '🇳🇷', 'name': 'Nauru'}, 'NZ': {'flag': '🇳🇿', 'name': 'New Zealand'},
                'OM': {'flag': '🇴🇲', 'name': 'Oman'},
                'PA': {'flag': '🇵🇦', 'name': 'Panama'}, 'PE': {'flag': '🇵🇪', 'name': 'Peru'}, 'PG': {'flag': '🇵🇬', 'name': 'Papua New Guinea'}, 'PH': {'flag': '🇵🇭', 'name': 'Philippines'}, 'PK': {'flag': '🇵🇰', 'name': 'Pakistan'}, 'PL': {'flag': '🇵🇱', 'name': 'Poland'}, 'PR': {'flag': '🇵🇷', 'name': 'Puerto Rico'}, 'PS': {'flag': '🇵🇸', 'name': 'Palestine'}, 'PT': {'flag': '🇵🇹', 'name': 'Portugal'}, 'PW': {'flag': '🇵🇼', 'name': 'Palau'}, 'PY': {'flag': '🇵🇾', 'name': 'Paraguay'},
                'QA': {'flag': '🇶🇦', 'name': 'Qatar'},
                'RE': {'flag': '🇷🇪', 'name': 'Réunion'}, 'RO': {'flag': '🇷🇴', 'name': 'Romania'}, 'RS': {'flag': '🇷🇸', 'name': 'Serbia'}, 'RU': {'flag': '🇷🇺', 'name': 'Russia'}, 'RW': {'flag': '🇷🇼', 'name': 'Rwanda'},
                'SA': {'flag': '🇸🇦', 'name': 'Saudi Arabia'}, 'SB': {'flag': '🇸🇧', 'name': 'Solomon Islands'}, 'SC': {'flag': '🇸🇨', 'name': 'Seychelles'}, 'SD': {'flag': '🇸🇩', 'name': 'Sudan'}, 'SE': {'flag': '🇸🇪', 'name': 'Sweden'}, 'SG': {'flag': '🇸🇬', 'name': 'Singapore'}, 'SI': {'flag': '🇸🇮', 'name': 'Slovenia'}, 'SK': {'flag': '🇸🇰', 'name': 'Slovakia'}, 'SL': {'flag': '🇸🇱', 'name': 'Sierra Leone'}, 'SM': {'flag': '🇸🇲', 'name': 'San Marino'}, 'SN': {'flag': '🇸🇳', 'name': 'Senegal'}, 'SO': {'flag': '🇸🇴', 'name': 'Somalia'}, 'SR': {'flag': '🇸🇷', 'name': 'Suriname'}, 'SS': {'flag': '🇸🇸', 'name': 'South Sudan'}, 'SV': {'flag': '🇸🇻', 'name': 'El Salvador'}, 'SY': {'flag': '🇸🇾', 'name': 'Syria'}, 'SZ': {'flag': '🇸🇿', 'name': 'Swaziland'},
                'TC': {'flag': '🇹🇨', 'name': 'Turks and Caicos'}, 'TD': {'flag': '🇹🇩', 'name': 'Chad'}, 'TG': {'flag': '🇹🇬', 'name': 'Togo'}, 'TH': {'flag': '🇹🇭', 'name': 'Thailand'}, 'TJ': {'flag': '🇹🇯', 'name': 'Tajikistan'}, 'TK': {'flag': '🇹🇰', 'name': 'Tokelau'}, 'TL': {'flag': '🇹🇱', 'name': 'Timor-Leste'}, 'TM': {'flag': '🇹🇲', 'name': 'Turkmenistan'}, 'TN': {'flag': '🇹🇳', 'name': 'Tunisia'}, 'TO': {'flag': '🇹🇴', 'name': 'Tonga'}, 'TR': {'flag': '🇹🇷', 'name': 'Turkey'}, 'TT': {'flag': '🇹🇹', 'name': 'Trinidad and Tobago'}, 'TV': {'flag': '🇹🇻', 'name': 'Tuvalu'}, 'TW': {'flag': '🇹🇼', 'name': 'Taiwan'}, 'TZ': {'flag': '🇹🇿', 'name': 'Tanzania'},
                'UA': {'flag': '🇺🇦', 'name': 'Ukraine'}, 'UG': {'flag': '🇺🇬', 'name': 'Uganda'}, 'US': {'flag': '🇺🇸', 'name': 'United States'}, 'UY': {'flag': '🇺🇾', 'name': 'Uruguay'}, 'UZ': {'flag': '🇺🇿', 'name': 'Uzbekistan'},
                'VA': {'flag': '🇻🇦', 'name': 'Vatican City'}, 'VC': {'flag': '🇻🇨', 'name': 'Saint Vincent'}, 'VE': {'flag': '🇻🇪', 'name': 'Venezuela'}, 'VG': {'flag': '🇻🇬', 'name': 'British Virgin Islands'}, 'VI': {'flag': '🇻🇮', 'name': 'US Virgin Islands'}, 'VN': {'flag': '🇻🇳', 'name': 'Vietnam'}, 'VU': {'flag': '🇻🇺', 'name': 'Vanuatu'},
                'WS': {'flag': '🇼🇸', 'name': 'Samoa'},
                'YE': {'flag': '🇾🇪', 'name': 'Yemen'}, 'YT': {'flag': '🇾🇹', 'name': 'Mayotte'},
                'ZA': {'flag': '🇿🇦', 'name': 'South Africa'}, 'ZM': {'flag': '🇿🇲', 'name': 'Zambia'}, 'ZW': {'flag': '🇿🇼', 'name': 'Zimbabwe'}
            };
        }
        
        getUniqueCountries() {
            // Extract unique countries from all reviews
            const countryCodes = [...new Set(this.allReviews.map(r => r.country).filter(c => c))];
            const countryMap = this.getCountryMap();
            
            // Count reviews per country
            const countryReviewCounts = {};
            this.allReviews.forEach(r => {
                if (r.country) {
                    countryReviewCounts[r.country] = (countryReviewCounts[r.country] || 0) + 1;
                }
            });
            
            // Convert codes to objects with display info and count
            return countryCodes
                .map(code => ({
                    code: code,
                    flag: countryMap[code]?.flag || '🌍',
                    name: countryMap[code]?.name || code,
                    count: countryReviewCounts[code] || 0
                }))
                .sort((a, b) => b.count - a.count); // Sort by count (most reviews first)
        }
        
        displayReview() {
            const content = document.getElementById('reviewking-content');
            
            if (!content) {
                console.error('Content element not found');
                return;
            }
            
            console.log('Displaying review...', { hasReviews: !!this.reviews, reviewCount: this.reviews?.length });
            
            // Check if reviews are loaded initially
            if (!this.allReviews || this.allReviews.length === 0) {
                content.innerHTML = '<div style="text-align: center; padding: 40px;">Loading reviews...</div>';
                return;
            }
            
            // Check if no reviews match the current filters
            if (!this.reviews || this.reviews.length === 0) {
                const countryMap = this.getCountryMap();
                const selectedCountryName = this.selectedCountry !== 'all' 
                    ? (countryMap[this.selectedCountry]?.name || this.selectedCountry)
                    : null;
                
                content.innerHTML = `
                    <div style="text-align: center; padding: 60px 40px; background: #fef3c7; border-radius: 16px; 
                                border: 2px dashed #f59e0b;">
                        <div style="font-size: 64px; margin-bottom: 20px;">😕</div>
                        <h3 style="color: #92400e; margin: 0 0 12px; font-size: 22px;">No Reviews Match Your Filters</h3>
                        <p style="color: #b45309; margin: 0 0 24px; font-size: 15px; line-height: 1.6;">
                            ${selectedCountryName 
                                ? `No reviews found from <strong>${selectedCountryName}</strong> with your selected filters.`
                                : 'No reviews match your current filter criteria.'
                            }
                        </p>
                        <div style="background: white; padding: 20px; border-radius: 8px; margin: 0 auto; max-width: 400px; text-align: left;">
                            <p style="color: #666; font-size: 14px; margin: 0 0 16px; font-weight: 600;">💡 Try this:</p>
                            <ul style="color: #666; font-size: 14px; margin: 0; padding-left: 20px; line-height: 2;">
                                ${selectedCountryName 
                                    ? `<li>Select a different country from the dropdown</li>
                                       <li>Or choose "All Countries" to see all reviews</li>`
                                    : `<li>Try selecting "All" in the star rating filter</li>
                                       <li>Remove the "Photos Only" filter if applied</li>`
                                }
                                <li>Check if reviews were successfully loaded (see stats above)</li>
                            </ul>
                        </div>
                        <button class="rk-btn-secondary" 
                                onclick="window.reviewKingClient.setFilter('all'); window.reviewKingClient.setCountry('all');"
                                style="margin-top: 20px; padding: 12px 24px; background: #FF2D85; color: white; 
                                       border: none; border-radius: 8px; font-size: 14px; font-weight: 600; 
                                       cursor: pointer; box-shadow: 0 2px 8px rgba(255,45,133,0.3);">
                            🔄 Reset All Filters
                        </button>
                    </div>
                `;
                return;
            }
            
            const review = this.reviews[this.currentIndex];
            const isRecommended = review.ai_recommended;
            
            // First show product search if no product selected
            if (!this.selectedProduct) {
                content.innerHTML = `
                    <div style="padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                border-radius: 8px; color: white; margin-bottom: 20px;">
                        <div style="margin-bottom: 12px;">
                            <input type="text" id="product-search-input" 
                                   placeholder="Enter Shopify product URL or name..." 
                                   style="width: 100%; padding: 10px 12px; border: none; border-radius: 6px; 
                                          background: rgba(255,255,255,0.9); color: #333; font-size: 14px;" />
                        </div>
                        <div id="product-dropdown" style="display: none; background: white; border-radius: 6px; 
                             box-shadow: 0 4px 12px rgba(0,0,0,0.15); max-height: 120px; overflow-y: auto; color: #333;"></div>
                        <div id="selected-product" style="display: none; margin-top: 8px; padding: 8px 12px; 
                             background: rgba(255,255,255,0.2); border-radius: 6px; font-size: 13px;"></div>
                    </div>
                    
                    <div style="text-align: center; padding: 40px; background: #fef3c7; border-radius: 12px;">
                        <div style="font-size: 48px; margin-bottom: 16px;">🎯</div>
                        <h3 style="color: #92400e; margin: 0 0 8px;">Select Target Product First</h3>
                        <p style="color: #b45309; margin: 0;">Use the search box above to select which Shopify product will receive these reviews</p>
                    </div>
                `;
                this.setupProductSearch();
                return;
            }
            
            // Show the beautiful review interface like your design
            content.innerHTML = `
                <!-- Product Search (always visible when product selected) -->
                <div style="padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            border-radius: 8px; color: white; margin-bottom: 20px;">
                    <div style="margin-bottom: 12px;">
                        <input type="text" id="product-search-input" 
                               placeholder="Enter Shopify product URL or name..." 
                               style="width: 100%; padding: 10px 12px; border: none; border-radius: 6px; 
                                      background: rgba(255,255,255,0.9); color: #333; font-size: 14px;" />
                    </div>
                    <div id="product-dropdown" style="display: none; background: white; border-radius: 6px; 
                         box-shadow: 0 4px 12px rgba(0,0,0,0.15); max-height: 120px; overflow-y: auto; color: #333;"></div>
                    <div id="selected-product" style="display: block; margin-top: 8px; padding: 8px 12px; 
                         background: rgba(255,255,255,0.2); border-radius: 6px; font-size: 13px;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            ${this.selectedProduct.image ? `<img src="${this.selectedProduct.image}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 6px; flex-shrink: 0;">` : '<div style="width: 50px; height: 50px; background: rgba(255,255,255,0.2); border-radius: 6px; flex-shrink: 0;"></div>'}
                            <div style="flex: 1;">
                                <div style="font-weight: 500;">✔ Target Product Selected</div>
                                <div style="opacity: 0.9; font-size: 12px;">${this.selectedProduct.title}</div>
                            </div>
                            <button onclick="window.reviewKingClient.clearProduct()" 
                                    style="background: rgba(255,255,255,0.2); border: none; color: white; 
                                           padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                                Change
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Beautiful Stats Header (like your design) -->
                <div style="background: linear-gradient(135deg, #FF2D85 0%, #FF1493 100%); 
                            padding: 16px; border-radius: 12px; margin-bottom: 24px; color: white; text-align: center;
                            box-shadow: 0 4px 16px rgba(255, 45, 133, 0.3);">
                    <div style="display: flex; justify-content: space-around; flex-wrap: wrap; gap: 16px;">
                        <div style="flex: 1; min-width: 80px;">
                            <div style="font-size: 32px; font-weight: 800; line-height: 1;">${this.reviews.length}</div>
                            <div style="font-size: 12px; opacity: 0.9; margin-top: 4px;">Total Loaded</div>
                        </div>
                        <div style="flex: 1; min-width: 80px;">
                            <div style="font-size: 32px; font-weight: 800; line-height: 1;">${this.stats.ai_recommended}</div>
                            <div style="font-size: 12px; opacity: 0.9; margin-top: 4px;">AI Recommended</div>
                        </div>
                        <div style="flex: 1; min-width: 80px;">
                            <div style="font-size: 32px; font-weight: 800; line-height: 1;">${this.stats.with_photos}</div>
                            <div style="font-size: 12px; opacity: 0.9; margin-top: 4px;">With Photos</div>
                        </div>
                        <div style="flex: 1; min-width: 80px;">
                            <div style="font-size: 32px; font-weight: 800; line-height: 1;">${this.stats.average_quality.toFixed(1)}<span style="font-size: 20px;">/10</span></div>
                            <div style="font-size: 12px; opacity: 0.9; margin-top: 4px;">Avg Quality</div>
                        </div>
                    </div>
                </div>
                
                <!-- Bulk Import Progress Loader -->
                <div id="rk-import-loader" style="display: none; margin-bottom: 16px; padding: 16px; background: rgba(255, 45, 133, 0.1); border: 2px solid #FF2D85; border-radius: 8px;">
                    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                        <div class="rk-spinner" style="width: 20px; height: 20px; border: 3px solid rgba(255, 45, 133, 0.3); border-top-color: #FF2D85; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                        <div style="color: #FF2D85; font-weight: 600; font-size: 14px;">
                            <span id="rk-import-status">Importing reviews...</span>
                        </div>
                    </div>
                    <div style="width: 100%; height: 6px; background: rgba(255, 45, 133, 0.2); border-radius: 3px; overflow: hidden;">
                        <div id="rk-import-progress" style="height: 100%; background: linear-gradient(90deg, #FF2D85, #FF1493); width: 0%; transition: width 0.3s ease; border-radius: 3px;"></div>
                    </div>
                    <div id="rk-import-message" style="margin-top: 8px; font-size: 12px; color: #9ca3af;"></div>
                </div>
                
                <!-- Bulk Import Section -->
                <div style="margin-bottom: 24px;">
                    <div style="color: #9ca3af; font-size: 16px; margin-bottom: 12px; font-weight: 600;">Bulk Imports:</div>
                    
                    <!-- Bulk Import Buttons Row 1 -->
                    <div style="display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap;">
                        <button id="rk-btn-import-all" class="rk-btn" style="background: #FF2D85; color: white; flex: 1; min-width: 150px; padding: 14px 18px; font-size: 14px; font-weight: 700;"
                                onclick="window.reviewKingClient.importAllReviews()">
                            All Reviews (${this.allReviews.length})
                        </button>
                        <button id="rk-btn-import-photos" class="rk-btn" style="background: #FF2D85; color: white; flex: 1; min-width: 150px; padding: 14px 18px; font-size: 14px; font-weight: 700;"
                                onclick="window.reviewKingClient.importWithPhotos()">
                            With Photos (${this.stats.with_photos})
                        </button>
                        <button id="rk-btn-import-no-photos" class="rk-btn" style="background: #FF2D85; color: white; flex: 1; min-width: 150px; padding: 14px 18px; font-size: 14px; font-weight: 700;"
                                onclick="window.reviewKingClient.importWithoutPhotos()">
                            No Photos (${this.allReviews.length - this.stats.with_photos})
                        </button>
                    </div>
                    
                    <!-- Bulk Import Buttons Row 2 -->
                    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                        <button id="rk-btn-import-ai" class="rk-btn" style="background: #FF2D85; color: white; flex: 1; min-width: 150px; padding: 14px 18px; font-size: 14px; font-weight: 700;"
                                onclick="window.reviewKingClient.importAIRecommended()">
                            AI Recommended (${this.stats.ai_recommended})
                        </button>
                        <button id="rk-btn-import-45star" class="rk-btn" style="background: #FF2D85; color: white; flex: 1; min-width: 150px; padding: 14px 18px; font-size: 14px; font-weight: 700;"
                                onclick="window.reviewKingClient.import45Star()">
                            4-5 ⭐ (${this.stats.reviews_45star})
                        </button>
                        <button id="rk-btn-import-3star" class="rk-btn" style="background: #FF2D85; color: white; flex: 1; min-width: 150px; padding: 14px 18px; font-size: 14px; font-weight: 700;"
                                onclick="window.reviewKingClient.import3Star()">
                            3 ⭐ (${this.stats.reviews_3star})
                        </button>
                    </div>
                </div>
                
                <!-- Warning Message -->
                <div style="background: #fffbeb; border: 1px solid #fbbf24; border-radius: 8px; padding: 12px; margin-bottom: 24px;">
                    <div style="display: flex; align-items: flex-start; gap: 8px;">
                        <span style="font-size: 18px;">⚠️</span>
                        <div style="flex: 1;">
                            <div style="color: #92400e; font-weight: 600; font-size: 13px; margin-bottom: 4px;">Warning: Bulk Import Notice</div>
                            <div style="color: #78350f; font-size: 12px; line-height: 1.5;">Bulk import operations may include negative reviews (1-2 star ratings). Please review the selected reviews before importing.</div>
                        </div>
                    </div>
                </div>
                
                <!-- Country Filter & Translation Toggle (Loox-inspired) -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
                    <div>
                        <label style="color: #9ca3af; font-size: 13px; margin-bottom: 6px; display: block; font-weight: 500;">🌍 Reviews from</label>
                        <select id="rk-country-filter" onchange="window.reviewKingClient.setCountry(this.value)" 
                                style="width: 100%; padding: 10px 12px; background: #0f0f23; color: white; border: 1px solid #2d2d3d; border-radius: 8px; font-size: 14px; cursor: pointer;">
                            <option value="all">🌍 All countries (${this.allReviews.length})</option>
                            ${this.getUniqueCountries().map(c => `<option value="${c.code}" ${this.selectedCountry === c.code ? 'selected' : ''}>${c.flag} ${c.name} (${c.count})</option>`).join('')}
                        </select>
                    </div>
                    <div>
                        <label style="color: #9ca3af; font-size: 13px; margin-bottom: 6px; display: block; font-weight: 500;">🌐 Translate</label>
                        <label style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: #0f0f23; border: 1px solid #2d2d3d; border-radius: 8px; cursor: pointer; height: 42px;">
                            <input type="checkbox" id="rk-translation-toggle" 
                                   ${this.showTranslations ? 'checked' : ''}
                                   onchange="window.reviewKingClient.toggleTranslation()"
                                   style="width: 18px; height: 18px; cursor: pointer; accent-color: #FF2D85;">
                            <span style="color: #d1d5db; font-size: 14px;">Show English translation</span>
                        </label>
                    </div>
                </div>
                
                <!-- Filter Buttons (like your design) -->
                <div style="margin-bottom: 24px;">
                    <div style="color: #9ca3af; font-size: 13px; margin-bottom: 10px; font-weight: 500;">Filter Reviews:</div>
                    <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px;">
                        <button class="rk-btn rk-btn-secondary" style="padding: 10px 16px; ${this.currentFilter === 'all' ? 'background: #FF2D85; color: white; border: none;' : ''}" onclick="window.reviewKingClient.setFilter('all')">All (${this.allReviews.length})</button>
                        <button class="rk-btn rk-btn-secondary" style="padding: 10px 16px; ${this.currentFilter === 'photos' ? 'background: #FF2D85; color: white; border: none;' : ''}" onclick="window.reviewKingClient.setFilter('photos')">&#128247; With Photos (${this.stats.with_photos})</button>
                        <button class="rk-btn rk-btn-secondary" style="padding: 10px 16px; ${this.currentFilter === 'ai_recommended' ? 'background: #FF2D85; color: white; border: none;' : ''}" onclick="window.reviewKingClient.setFilter('ai_recommended')"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ff69b4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: middle; margin-right: 6px;"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"></path><path d="M20 3v4"></path><path d="M22 5h-4"></path><path d="M4 17v2"></path><path d="M5 18H3"></path></svg> AI Recommended (${this.stats.ai_recommended})</button>
                        <button class="rk-btn rk-btn-secondary" style="padding: 10px 16px; ${this.currentFilter === '4-5stars' ? 'background: #FF2D85; color: white; border: none;' : ''}" onclick="window.reviewKingClient.setFilter('4-5stars')">4-5 &#9733; (${this.stats.reviews_45star})</button>
                        <button class="rk-btn rk-btn-secondary" style="padding: 10px 16px; ${this.currentFilter === '3stars' ? 'background: #FF2D85; color: white; border: none;' : ''}" onclick="window.reviewKingClient.setFilter('3stars')">3 &#9733; (${this.stats.reviews_3star})</button>
                    </div>
                    <div style="color: #6b7280; font-size: 12px;">
                        Showing ${this.currentIndex + 1} of ${this.reviews.length} reviews
                    </div>
                </div>
                
                <!-- Single Review Card (your beautiful design) -->
                <div style="background: #0f0f23; border-radius: 12px; padding: 28px; color: white; margin-bottom: 20px; border: 1px solid #1a1a2e;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 18px; align-items: flex-start;">
                        <div style="flex: 1;">
                            <h3 style="margin: 0; color: white; font-size: 18px; font-weight: 700; letter-spacing: -0.02em;">${review.reviewer_name}</h3>
                            <div style="color: #fbbf24; font-size: 24px; margin: 6px 0; line-height: 1; display: flex; align-items: center; gap: 2px;">${this.renderStars(review.rating)}</div>
                            <div style="color: #9ca3af; font-size: 12px; font-weight: 500;">${review.date} • ${review.country}</div>
                        </div>
                        <div style="text-align: right; display: flex; flex-direction: column; gap: 8px; align-items: flex-end;">
                            ${isRecommended ? '<span style="background: #10b981; color: white; padding: 6px 12px; border-radius: 16px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; display: inline-block;">&#10004; AI RECOMMENDED</span>' : ''}
                            <span style="background: #3b82f6; color: white; padding: 6px 12px; border-radius: 16px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; display: inline-block;">QUALITY: ${review.quality_score}/10</span>
                        </div>
                    </div>
                    
                    <!-- Review text with translation support -->
                    ${(() => {
                        const hasTranslation = review.translation && review.text !== review.translation;
                        const displayText = (this.showTranslations && hasTranslation) ? review.translation : review.text;
                        const showOriginal = this.showTranslations && hasTranslation;
                        
                        return `
                            <p style="color: #d1d5db; line-height: 1.7; margin: 0 0 18px; font-size: 15px;">${displayText}</p>
                            ${showOriginal ? 
                                `<p style="color: #888; font-size: 13px; margin: 0 0 18px; font-style: italic; border-left: 2px solid #555; padding-left: 10px;">Original: ${review.text}</p>` 
                                : ''
                            }
                        `;
                    })()}
                    
                    ${review.images && review.images.length > 0 ? `
                        <div style="margin-bottom: 18px;">
                            <div style="color: #9ca3af; font-size: 12px; margin-bottom: 10px; font-weight: 600;">
                                📸 ${review.images.length} Photo${review.images.length > 1 ? 's' : ''}
                            </div>
                            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                                ${review.images.map(img => 
                                    `<img src="${img}" style="width: 100px; height: 100px; 
                                    object-fit: cover; border-radius: 10px; cursor: pointer; border: 2px solid #1a1a2e;
                                    transition: all 0.2s;"
                                    onmouseover="this.style.transform='scale(1.05)'; this.style.borderColor='#3b82f6';"
                                    onmouseout="this.style.transform='scale(1)'; this.style.borderColor='#1a1a2e';"
                                    onclick="window.open('${img}', '_blank')">`
                                ).join('')}
                            </div>
                        </div>
                    ` : '<div style="color: #6b7280; font-style: italic; margin-bottom: 18px; font-size: 13px;">No photos</div>'}
                    
                    <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px;">
                        ${review.verified ? '<span style="background: #10b981; color: white; padding: 5px 10px; border-radius: 14px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;">✔ VERIFIED</span>' : ''}
                        <span style="background: #2d2d3d; color: #a1a1aa; padding: 5px 10px; border-radius: 14px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; border: 1px solid #3d3d4d;">
                            PLATFORM: ${review.platform.toUpperCase()}
                        </span>
                        <span style="background: #2d2d3d; color: #a1a1aa; padding: 5px 10px; border-radius: 14px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; border: 1px solid #3d3d4d;">
                            SENTIMENT: ${Math.round(review.sentiment_score * 100)}%
                        </span>
                    </div>
                    
                    <!-- Import/Reject buttons for individual review -->
                    <div style="display: flex; gap: 12px; margin-top: 20px;">
                        <button style="background: #374151; color: white; border: none; padding: 14px 28px; 
                                       border-radius: 8px; cursor: pointer; flex: 1; font-weight: 600; font-size: 14px;
                                       transition: all 0.2s;"
                                onmouseover="this.style.background='#4b5563'" 
                                onmouseout="this.style.background='#374151'"
                                onclick="window.reviewKingClient.skipReview()">
                            Reject
                        </button>
                        <button style="background: #FF2D85; color: white; border: none; padding: 14px 28px; 
                                       border-radius: 8px; cursor: pointer; flex: 2; font-weight: 700; font-size: 14px;
                                       transition: all 0.2s;"
                                onmouseover="this.style.background='#E0186F'; this.style.transform='translateY(-1px)'" 
                                onmouseout="this.style.background='#FF2D85'; this.style.transform='translateY(0)'"
                                onclick="window.reviewKingClient.importReview()">
                            Import
                        </button>
                    </div>
                </div>
                
                <!-- Navigation -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 24px; padding-top: 16px; border-top: 1px solid #2d2d3d;">
                    <button class="rk-btn rk-btn-secondary" style="padding: 10px 20px;" onclick="window.reviewKingClient.prevReview()"
                            ${this.currentIndex === 0 ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : ''}>← Previous</button>
                    <span style="color: #9ca3af; font-size: 14px; font-weight: 600;">
                        ${this.currentIndex + 1} / ${this.reviews.length}
                    </span>
                    <button class="rk-btn rk-btn-secondary" style="padding: 10px 20px;" onclick="window.reviewKingClient.nextReview()"
                            ${this.currentIndex === this.reviews.length - 1 ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : ''}>Next →</button>
                </div>
            `;
            
            this.setupProductSearch();
        }
        
        async importReview() {
            if (!this.selectedProduct) {
                alert('Please select a target product first!');
                return;
            }
            
            const review = this.reviews[this.currentIndex];
            
            try {
                // DEBUG: Log review data before sending
                console.log('[DEBUG] Sending review to database:', {
                    review_id: review.id,
                    reviewer_name: review.author || review.reviewer_name,
                    rating: review.rating,
                    title: review.title,
                    shopify_product_id: this.selectedProduct.id,
                    shopify_product_title: this.selectedProduct.title,
                    review_data: review
                });
                
                const requestBody = {
                    review: review,
                    shopify_product_id: this.selectedProduct.id,
                    session_id: this.sessionId
                };
                
                console.log('[DEBUG] Request URL:', `${API_URL}/admin/reviews/import/single`);
                console.log('[DEBUG] Request body:', JSON.stringify(requestBody, null, 2));
                
                const response = await fetch(`${API_URL}/admin/reviews/import/single`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(requestBody)
                });
                
                console.log('[DEBUG] Response status:', response.status);
                const result = await response.json();
                console.log('[DEBUG] Response data:', result);
                
                if (result.success) {
                    // Log database review ID if available
                    if (result.review_id) {
                        console.log('✅ [DATABASE] Review saved with DB ID:', result.review_id);
                        console.log('   Shopify Product ID:', result.shopify_product_id || this.selectedProduct.id);
                        console.log('   Database Product ID:', result.product_id || 'N/A');
                        console.log('   Imported at:', result.imported_at || new Date().toISOString());
                    } else {
                        console.warn('⚠️ [WARNING] Review imported but NO database ID returned - using simulation mode');
                        if (result.imported_review) {
                            console.log('   Source Review ID (not DB ID):', result.imported_review.id);
                        }
                    }
                    
                    // Track analytics
                    fetch(`${API_URL}/e?cat=Import+by+URL&a=Post+imported&c=${this.sessionId}`, 
                          { method: 'GET' });
                    
                    // Handle duplicate vs new import
                    if (result.duplicate) {
                        const message = result.message || `⚠️ Review already imported for this product (Database ID: ${result.review_id})`;
                        alert(message);
                        // Don't auto-advance for duplicates - let user see what happened
                        // this.nextReview();
                    } else {
                        const message = result.review_id 
                            ? `✔ Review imported successfully! Database ID: ${result.review_id}`
                            : `✔ Review imported (simulation mode - database unavailable)`;
                        alert(message);
                        this.nextReview();
                    }
                } else {
                    alert('Failed to import: ' + result.error);
                }
            } catch (error) {
                alert('Import failed. Please try again.');
            }
        }
        
        async skipReview() {
            const review = this.reviews[this.currentIndex];
            
            try {
                const response = await fetch(`${API_URL}/admin/reviews/skip`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        review_id: review.id,
                        session_id: this.sessionId
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('Review skipped. It will not be included in bulk import.');
                    this.nextReview();
                } else {
                    alert('Failed to skip review: ' + result.error);
                }
            } catch (error) {
                alert('Skip failed. Please try again.');
            }
        }
        
        // Helper methods for bulk import progress
        showImportLoader(statusText, totalReviews) {
            this.isImporting = true;
            const loader = document.getElementById('rk-import-loader');
            const status = document.getElementById('rk-import-status');
            const progress = document.getElementById('rk-import-progress');
            const message = document.getElementById('rk-import-message');
            
            if (loader && status && progress && message) {
                loader.style.display = 'block';
                status.textContent = statusText || 'Importing reviews...';
                progress.style.width = '0%';
                message.textContent = '';
            }
            
            // Disable all bulk import buttons
            this.setBulkImportButtonsEnabled(false);
        }
        
        updateImportProgress(current, total) {
            const progress = document.getElementById('rk-import-progress');
            const percentage = total > 0 ? Math.round((current / total) * 100) : 0;
            if (progress) {
                progress.style.width = percentage + '%';
            }
        }
        
        hideImportLoader(success, message, details) {
            this.isImporting = false;
            const loader = document.getElementById('rk-import-loader');
            const status = document.getElementById('rk-import-status');
            const progress = document.getElementById('rk-import-progress');
            const messageEl = document.getElementById('rk-import-message');
            
            if (loader && status && progress && messageEl) {
                if (success) {
                    status.textContent = '✅ Import completed!';
                    status.style.color = '#10b981';
                    progress.style.background = 'linear-gradient(90deg, #10b981, #059669)';
                    progress.style.width = '100%';
                } else {
                    status.textContent = '❌ Import failed';
                    status.style.color = '#ef4444';
                    progress.style.background = 'linear-gradient(90deg, #ef4444, #dc2626)';
                }
                
                if (message) {
                    messageEl.textContent = message;
                    messageEl.style.color = success ? '#10b981' : '#ef4444';
                }
                
                if (details) {
                    messageEl.textContent += ' ' + details;
                }
            }
            
            // Re-enable all bulk import buttons
            this.setBulkImportButtonsEnabled(true);
            
            // Hide loader after 5 seconds
            setTimeout(() => {
                if (loader) loader.style.display = 'none';
                // Reset progress bar
                if (progress) {
                    progress.style.width = '0%';
                    progress.style.background = 'linear-gradient(90deg, #FF2D85, #FF1493)';
                }
                if (status) {
                    status.textContent = 'Importing reviews...';
                    status.style.color = '#FF2D85';
                }
            }, 5000);
        }
        
        setBulkImportButtonsEnabled(enabled) {
            // Update all bulk import buttons including new ones
            const buttons = [
                document.getElementById('rk-btn-import-all'),
                document.getElementById('rk-btn-import-photos'),
                document.getElementById('rk-btn-import-no-photos'),
                document.getElementById('rk-btn-import-ai'),
                document.getElementById('rk-btn-import-45star'),
                document.getElementById('rk-btn-import-3star')
            ];
            
            buttons.forEach(btn => {
                if (btn) {
                    btn.disabled = !enabled;
                    btn.style.opacity = enabled ? '1' : '0.5';
                    btn.style.cursor = enabled ? 'pointer' : 'not-allowed';
                }
            });
        }
        
        async importAllReviews() {
            if (this.isImporting) {
                return; // Prevent multiple simultaneous imports
            }
            
            if (!this.selectedProduct) {
                alert('Please select a target product first!');
                return;
            }
            
            if (!this.allReviews || this.allReviews.length === 0) {
                alert('No reviews available to import. Please load reviews first.');
                return;
            }
            
            // Count negative reviews for warning
            const negativeReviews = this.allReviews.filter(r => {
                const rating = r.rating > 5 ? Math.ceil((r.rating / 100) * 5) : r.rating;
                return rating <= 2;
            });
            
            const warningMsg = negativeReviews.length > 0 
                ? `Import all ${this.allReviews.length} reviews to "${this.selectedProduct.title}"?\n\n⚠️ WARNING: This will import ${negativeReviews.length} negative review(s) (1-2 stars).\n\nThis will import multiple reviews at once.`
                : `Import all ${this.allReviews.length} reviews to "${this.selectedProduct.title}"?\n\nThis will import multiple reviews at once.`;
            
            if (!confirm(warningMsg)) {
                return;
            }
            
            this.showImportLoader(`Importing ${this.allReviews.length} reviews...`, this.allReviews.length);
            
            try {
                const response = await fetch(`${API_URL}/admin/reviews/import/bulk`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        reviews: this.allReviews,  // Use allReviews, not filtered reviews
                        shopify_product_id: this.selectedProduct.id,
                        session_id: this.sessionId,
                        platform: 'aliexpress',
                        filters: {
                            min_quality_score: 0  // Import all quality levels
                        }
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Track analytics
                    fetch(`${API_URL}/e?cat=Import+by+URL&a=Bulk+imported&c=${this.sessionId}`, 
                          { method: 'GET' });
                    
                    const duplicateMsg = result.duplicate_count > 0 ? ` | 🔄 Duplicates: ${result.duplicate_count}` : '';
                    const message = `✅ Imported: ${result.imported_count} | ❌ Failed: ${result.failed_count} | ⏭️ Skipped: ${result.skipped_count}${duplicateMsg}`;
                    this.hideImportLoader(true, `Successfully imported ${result.imported_count} reviews!`, message);
                } else {
                    this.hideImportLoader(false, 'Import failed: ' + result.error, '');
                }
            } catch (error) {
                console.error('Bulk import error:', error);
                this.hideImportLoader(false, 'Import failed. Please try again.', error.message || '');
            }
        }
        
        async importWithPhotos() {
            if (this.isImporting) {
                return; // Prevent multiple simultaneous imports
            }
            
            if (!this.selectedProduct) {
                alert('Please select a target product first!');
                return;
            }
            
            if (!this.allReviews || this.allReviews.length === 0) {
                alert('No reviews available to import. Please load reviews first.');
                return;
            }
            
            // Filter allReviews (not just filtered display reviews) for reviews with photos
            const reviewsWithPhotos = this.allReviews.filter(r => r.images && r.images.length > 0);
            
            if (reviewsWithPhotos.length === 0) {
                alert('⚠️ No reviews with photos found for this product.\n\nPlease try selecting a different product with photo reviews.');
                return;
            }
            
            // Count negative reviews for warning
            const negativeReviews = reviewsWithPhotos.filter(r => {
                const rating = r.rating > 5 ? Math.ceil((r.rating / 100) * 5) : r.rating;
                return rating <= 2;
            });
            
            const warningMsg = negativeReviews.length > 0
                ? `Import ${reviewsWithPhotos.length} reviews with photos to "${this.selectedProduct.title}"?\n\n⚠️ WARNING: This will import ${negativeReviews.length} negative review(s) (1-2 stars).`
                : `Import ${reviewsWithPhotos.length} reviews with photos to "${this.selectedProduct.title}"?`;
            
            if (!confirm(warningMsg)) {
                return;
            }
            
            this.showImportLoader(`Importing ${reviewsWithPhotos.length} reviews with photos...`, reviewsWithPhotos.length);
            
            try {
                const response = await fetch(`${API_URL}/admin/reviews/import/bulk`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        reviews: reviewsWithPhotos,
                        shopify_product_id: this.selectedProduct.id,
                        session_id: this.sessionId,
                        platform: 'aliexpress'
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    const duplicateMsg = result.duplicate_count > 0 ? ` | 🔄 Duplicates: ${result.duplicate_count}` : '';
                    const message = `✅ Imported: ${result.imported_count} | ❌ Failed: ${result.failed_count}${duplicateMsg}`;
                    this.hideImportLoader(true, `Successfully imported ${result.imported_count} reviews with photos!`, message);
                } else {
                    this.hideImportLoader(false, 'Import failed: ' + result.error, '');
                }
            } catch (error) {
                console.error('Import with photos error:', error);
                this.hideImportLoader(false, 'Import failed. Please try again.', error.message || '');
            }
        }
        
        async importWithoutPhotos() {
            if (this.isImporting) {
                return; // Prevent multiple simultaneous imports
            }
            
            if (!this.selectedProduct) {
                alert('Please select a target product first!');
                return;
            }
            
            if (!this.allReviews || this.allReviews.length === 0) {
                alert('No reviews available to import. Please load reviews first.');
                return;
            }
            
            // Filter allReviews (not just filtered display reviews) for reviews without photos
            const reviewsWithoutPhotos = this.allReviews.filter(r => !r.images || r.images.length === 0);
            
            if (reviewsWithoutPhotos.length === 0) {
                alert('⚠️ No reviews without photos found for this product.\n\nAll reviews for this product have photos. Please try selecting a different product.');
                return;
            }
            
            // Count negative reviews for warning
            const negativeReviews = reviewsWithoutPhotos.filter(r => {
                const rating = r.rating > 5 ? Math.ceil((r.rating / 100) * 5) : r.rating;
                return rating <= 2;
            });
            
            const warningMsg = negativeReviews.length > 0
                ? `Import ${reviewsWithoutPhotos.length} reviews without photos to "${this.selectedProduct.title}"?\n\n⚠️ WARNING: This will import ${negativeReviews.length} negative review(s) (1-2 stars).`
                : `Import ${reviewsWithoutPhotos.length} reviews without photos to "${this.selectedProduct.title}"?`;
            
            if (!confirm(warningMsg)) {
                return;
            }
            
            this.showImportLoader(`Importing ${reviewsWithoutPhotos.length} reviews without photos...`, reviewsWithoutPhotos.length);
            
            try {
                const response = await fetch(`${API_URL}/admin/reviews/import/bulk`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        reviews: reviewsWithoutPhotos,
                        shopify_product_id: this.selectedProduct.id,
                        session_id: this.sessionId,
                        platform: 'aliexpress'
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    const duplicateMsg = result.duplicate_count > 0 ? ` | 🔄 Duplicates: ${result.duplicate_count}` : '';
                    const message = `✅ Imported: ${result.imported_count} | ❌ Failed: ${result.failed_count}${duplicateMsg}`;
                    this.hideImportLoader(true, `Successfully imported ${result.imported_count} reviews without photos!`, message);
                } else {
                    this.hideImportLoader(false, 'Import failed: ' + result.error, '');
                }
            } catch (error) {
                console.error('Import without photos error:', error);
                this.hideImportLoader(false, 'Import failed. Please try again.', error.message || '');
            }
        }
        
        async importAIRecommended() {
            if (this.isImporting) {
                return; // Prevent multiple simultaneous imports
            }
            
            if (!this.selectedProduct) {
                alert('Please select a target product first!');
                return;
            }
            
            if (!this.allReviews || this.allReviews.length === 0) {
                alert('No reviews available to import. Please load reviews first.');
                return;
            }
            
            // Filter allReviews for AI recommended reviews
            const aiRecommendedReviews = this.allReviews.filter(r => r.ai_recommended);
            
            if (aiRecommendedReviews.length === 0) {
                alert('⚠️ No AI recommended reviews found for this product.\n\nAI recommended reviews are reviews with high quality scores. Please try selecting a different product.');
                return;
            }
            
            // Count negative reviews for warning
            const negativeReviews = aiRecommendedReviews.filter(r => {
                const rating = r.rating > 5 ? Math.ceil((r.rating / 100) * 5) : r.rating;
                return rating <= 2;
            });
            
            const warningMsg = negativeReviews.length > 0
                ? `Import ${aiRecommendedReviews.length} AI recommended reviews to "${this.selectedProduct.title}"?\n\n⚠️ WARNING: This will import ${negativeReviews.length} negative review(s) (1-2 stars).`
                : `Import ${aiRecommendedReviews.length} AI recommended reviews to "${this.selectedProduct.title}"?`;
            
            if (!confirm(warningMsg)) {
                return;
            }
            
            this.showImportLoader(`Importing ${aiRecommendedReviews.length} AI recommended reviews...`, aiRecommendedReviews.length);
            
            try {
                const response = await fetch(`${API_URL}/admin/reviews/import/bulk`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        reviews: aiRecommendedReviews,
                        shopify_product_id: this.selectedProduct.id,
                        session_id: this.sessionId,
                        platform: 'aliexpress'
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    const duplicateMsg = result.duplicate_count > 0 ? ` | 🔄 Duplicates: ${result.duplicate_count}` : '';
                    const message = `✅ Imported: ${result.imported_count} | ❌ Failed: ${result.failed_count}${duplicateMsg}`;
                    this.hideImportLoader(true, `Successfully imported ${result.imported_count} AI recommended reviews!`, message);
                } else {
                    this.hideImportLoader(false, 'Import failed: ' + result.error, '');
                }
            } catch (error) {
                console.error('Import AI recommended error:', error);
                this.hideImportLoader(false, 'Import failed. Please try again.', error.message || '');
            }
        }
        
        async import45Star() {
            if (this.isImporting) {
                return; // Prevent multiple simultaneous imports
            }
            
            if (!this.selectedProduct) {
                alert('Please select a target product first!');
                return;
            }
            
            if (!this.allReviews || this.allReviews.length === 0) {
                alert('No reviews available to import. Please load reviews first.');
                return;
            }
            
            // Filter allReviews for 4-5 star reviews
            const reviews45star = this.allReviews.filter(r => {
                const rating = r.rating > 5 ? Math.ceil((r.rating / 100) * 5) : r.rating;
                return rating === 4 || rating === 5;
            });
            
            if (reviews45star.length === 0) {
                alert('⚠️ No 4-5 star reviews found for this product.\n\nPlease try selecting a different product with higher-rated reviews.');
                return;
            }
            
            if (!confirm(`Import ${reviews45star.length} reviews with 4-5 stars to "${this.selectedProduct.title}"?`)) {
                return;
            }
            
            this.showImportLoader(`Importing ${reviews45star.length} reviews with 4-5 stars...`, reviews45star.length);
            
            try {
                const response = await fetch(`${API_URL}/admin/reviews/import/bulk`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        reviews: reviews45star,
                        shopify_product_id: this.selectedProduct.id,
                        session_id: this.sessionId,
                        platform: 'aliexpress'
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    const duplicateMsg = result.duplicate_count > 0 ? ` | 🔄 Duplicates: ${result.duplicate_count}` : '';
                    const message = `✅ Imported: ${result.imported_count} | ❌ Failed: ${result.failed_count}${duplicateMsg}`;
                    this.hideImportLoader(true, `Successfully imported ${result.imported_count} reviews with 4-5 stars!`, message);
                } else {
                    this.hideImportLoader(false, 'Import failed: ' + result.error, '');
                }
            } catch (error) {
                console.error('Import 4-5 star error:', error);
                this.hideImportLoader(false, 'Import failed. Please try again.', error.message || '');
            }
        }
        
        async import3Star() {
            if (this.isImporting) {
                return; // Prevent multiple simultaneous imports
            }
            
            if (!this.selectedProduct) {
                alert('Please select a target product first!');
                return;
            }
            
            if (!this.allReviews || this.allReviews.length === 0) {
                alert('No reviews available to import. Please load reviews first.');
                return;
            }
            
            // Filter allReviews for 3 star reviews
            const reviews3star = this.allReviews.filter(r => {
                const rating = r.rating > 5 ? Math.ceil((r.rating / 100) * 5) : r.rating;
                return rating === 3;
            });
            
            if (reviews3star.length === 0) {
                alert('⚠️ No 3 star reviews found for this product.\n\nPlease try selecting a different product.');
                return;
            }
            
            if (!confirm(`Import ${reviews3star.length} reviews with 3 stars to "${this.selectedProduct.title}"?`)) {
                return;
            }
            
            this.showImportLoader(`Importing ${reviews3star.length} reviews with 3 stars...`, reviews3star.length);
            
            try {
                const response = await fetch(`${API_URL}/admin/reviews/import/bulk`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        reviews: reviews3star,
                        shopify_product_id: this.selectedProduct.id,
                        session_id: this.sessionId,
                        platform: 'aliexpress'
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    const duplicateMsg = result.duplicate_count > 0 ? ` | 🔄 Duplicates: ${result.duplicate_count}` : '';
                    const message = `✅ Imported: ${result.imported_count} | ❌ Failed: ${result.failed_count}${duplicateMsg}`;
                    this.hideImportLoader(true, `Successfully imported ${result.imported_count} reviews with 3 stars!`, message);
                } else {
                    this.hideImportLoader(false, 'Import failed: ' + result.error, '');
                }
            } catch (error) {
                console.error('Import 3 star error:', error);
                this.hideImportLoader(false, 'Import failed. Please try again.', error.message || '');
            }
        }
        
        nextReview() {
            if (this.currentIndex < this.reviews.length - 1) {
                this.currentIndex++;
                this.displayReview();
            } else if (this.pagination.has_next) {
                this.loadReviews(this.pagination.page + 1);
            } else {
                alert('No more reviews!');
            }
        }
        
        prevReview() {
            if (this.currentIndex > 0) {
                this.currentIndex--;
                this.displayReview();
            }
        }
        
        showError(message) {
            document.getElementById('reviewking-content').innerHTML = `
                <div style="text-align: center; padding: 40px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
                    <h3 style="color: #ef4444; margin: 0 0 8px;">Error</h3>
                    <p style="color: #6b7280; margin: 0;">${message}</p>
                    <button class="rk-btn rk-btn-primary" style="margin-top: 20px;"
                            onclick="if(window.reviewKingClient) window.reviewKingClient.close()">Close</button>
                </div>
            `;
        }
        
        close() {
            console.log('[REVIEWKING] Closing and cleaning up...');
            
            // Remove overlay if it exists
            const overlay = document.getElementById('reviewking-overlay');
            if (overlay) {
                overlay.remove();
            }
            
            // Clean up modal click handler if it exists
            if (this.modalClickHandler) {
                document.body.removeEventListener('click', this.modalClickHandler);
                this.modalClickHandler = null;
                console.log('[REVIEWKING] Removed modal click handler');
            }
            
            // Cleanup complete - no need to restore body scroll or reset global state
        }
    }
    
    // Wrap initialization in try-catch for error handling
    // Note: window.reviewKingClient is assigned inside the constructor before init() runs
    try {
        new ReviewKingClient();
    } catch (error) {
        console.error('[REVIEWKING] Initialization error:', error);
        window.reviewKingActive = false;
        delete window.reviewKingClient;  // Clean up if it was partially assigned
        alert('ReviewKing initialization failed: ' + error.message);
        
        // Clean up any partially created overlay
        const overlay = document.getElementById('reviewking-overlay');
        if (overlay) overlay.remove();
    }
})();