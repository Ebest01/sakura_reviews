-- Create products table manually
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    shop_id INTEGER NOT NULL REFERENCES shops(id),
    shopify_product_id VARCHAR(255) NOT NULL,
    shopify_product_title VARCHAR(500),
    shopify_product_handle VARCHAR(255),
    shopify_product_url TEXT,
    source_platform VARCHAR(50),
    source_product_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(shop_id, shopify_product_id)
);

CREATE INDEX IF NOT EXISTS idx_shop_product ON products (shop_id, shopify_product_id);
CREATE INDEX IF NOT EXISTS idx_products_shop_id ON products (shop_id);

