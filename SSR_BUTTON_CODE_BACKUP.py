"""
PERMANENT BACKUP: SSR "Get Reviews" Button Code
===============================================
This code must be preserved in app_enhanced.py at the /js/bookmarklet.js endpoint.
DO NOT REMOVE OR MODIFY WITHOUT UPDATING THIS BACKUP FIRST.

Location in app_enhanced.py: Inside the bookmarklet JavaScript code, in the ReviewKingClient class.
Key methods:
- setupModalListener() - Detects SSR pages and sets up modal detection
- setupProductClickListener() - Listens for product clicks on SSR pages
- addSakuraButton(productId) - Adds the "Get Reviews" button to AliExpress modals
- createSakuraButtonElement(productId) - Creates the button HTML element
"""

SSR_BUTTON_CODE = """
// SSR MODE - Setup for AliExpress SSR/modal pages
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
        alert('🌸 Sakura Reviews is now activated!\\n\\nClick on any product to add the "Get Reviews Now" button.');
        
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
        alert('🌸 Sakura Reviews\\n\\nClick on any product in the search results to add the "Get Reviews" button to its modal.');
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
                    const match = productId.match(/productId['":]?[\\s]*(\\d+)/);
                    if (match) productId = match[1];
                }
            }
            
            // Validate product ID (AliExpress IDs are usually 13+ digits starting with 1005)
            if (productId && /^1005\\d{9,}$/.test(String(productId))) {
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
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(255, 105, 180, 0.3);
        margin: 8px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        white-space: nowrap;
    `;
    btn.onmouseover = () => {
        btn.style.transform = 'scale(1.05)';
        btn.style.boxShadow = '0 6px 16px rgba(255, 105, 180, 0.5)';
    };
    btn.onmouseout = () => {
        btn.style.transform = 'scale(1)';
        btn.style.boxShadow = '0 4px 12px rgba(255, 105, 180, 0.3)';
    };
    btn.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        console.log('[SSR MODE] Get Reviews button clicked for product:', productId);
        this.selectedProduct = { productId: productId };
        this.loadReviews();
    };
    return btn;
}
"""

# CRITICAL: This code must always be present in app_enhanced.py's bookmarklet endpoint
# Location: Inside the ReviewKingClient class JavaScript code
# When making edits, preserve these four methods: setupModalListener, setupProductClickListener, addSakuraButton, createSakuraButtonElement

