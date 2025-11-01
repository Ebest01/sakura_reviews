"""
Shopify OAuth Authentication
Handles app installation, token management, and API calls
"""
import hmac
import hashlib
import binascii
from urllib.parse import parse_qs, urlencode
import requests
from flask import session, redirect, request
from functools import wraps
import shopify

class ShopifyAuth:
    def __init__(self, api_key, api_secret, scopes, redirect_uri):
        self.api_key = api_key
        self.api_secret = api_secret
        self.scopes = scopes
        self.redirect_uri = redirect_uri
    
    def verify_hmac(self, params):
        """Verify HMAC signature from Shopify"""
        if 'hmac' not in params:
            return False
        
        encoded_params = {}
        for key, value in params.items():
            if key != 'hmac':
                if isinstance(value, list):
                    encoded_params[key] = value[0]
                else:
                    encoded_params[key] = value
        
        query_string = urlencode(sorted(encoded_params.items()))
        
        calculated_hmac = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        provided_hmac = params['hmac'] if isinstance(params['hmac'], str) else params['hmac'][0]
        
        return hmac.compare_digest(calculated_hmac, provided_hmac)
    
    def build_auth_url(self, shop_domain, state=None):
        """Build OAuth authorization URL"""
        params = {
            'client_id': self.api_key,
            'scope': self.scopes,
            'redirect_uri': self.redirect_uri
        }
        
        if state:
            params['state'] = state
        
        auth_url = f"https://{shop_domain}/admin/oauth/authorize?{urlencode(params)}"
        return auth_url
    
    def exchange_code_for_token(self, shop_domain, code):
        """Exchange authorization code for access token"""
        token_url = f"https://{shop_domain}/admin/oauth/access_token"
        
        payload = {
            'client_id': self.api_key,
            'client_secret': self.api_secret,
            'code': code
        }
        
        response = requests.post(token_url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data.get('access_token')
    
    def get_shop_info(self, shop_domain, access_token):
        """Get shop information from Shopify"""
        headers = {
            'X-Shopify-Access-Token': access_token,
            'Content-Type': 'application/json'
        }
        
        url = f"https://{shop_domain}/admin/api/2024-01/shop.json"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()['shop']

def login_required(f):
    """Decorator to require Shopify authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        shop = session.get('shop')
        if not shop:
            return {'error': 'Not authenticated'}, 401
        return f(*args, **kwargs)
    return decorated_function

def init_shopify_session(shop_domain, access_token):
    """Initialize Shopify API session"""
    session = shopify.Session(shop_domain, '2024-01', access_token)
    shopify.ShopifyResource.activate_session(session)
    return session

class ShopifyAPI:
    """Wrapper for Shopify API calls"""
    
    def __init__(self, shop_domain, access_token):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.api_version = '2024-01'
        self.base_url = f"https://{shop_domain}/admin/api/{self.api_version}"
        self.headers = {
            'X-Shopify-Access-Token': access_token,
            'Content-Type': 'application/json'
        }
    
    def graphql(self, query, variables=None):
        """Execute GraphQL query"""
        url = f"{self.base_url}/graphql.json"
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_products(self, limit=50):
        """Get products from shop"""
        url = f"{self.base_url}/products.json"
        params = {'limit': limit}
        
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()['products']
    
    def get_product(self, product_id):
        """Get single product"""
        url = f"{self.base_url}/products/{product_id}.json"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()['product']
    
    def create_product_review(self, product_id, review_data):
        """Create product review using metafields (Shopify doesn't have native review API)"""
        # Note: Shopify doesn't have a native product review API
        # We'll use metafields to store reviews or integrate with Product Reviews app
        
        # For now, we'll create a metafield for the review
        url = f"{self.base_url}/products/{product_id}/metafields.json"
        
        metafield = {
            'metafield': {
                'namespace': 'reviewking',
                'key': f"review_{review_data['id']}",
                'value': str(review_data),
                'type': 'json'
            }
        }
        
        response = requests.post(url, json=metafield, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def create_recurring_charge(self, plan_name, price, return_url):
        """Create recurring application charge (subscription)"""
        url = f"{self.base_url}/recurring_application_charges.json"
        
        charge = {
            'recurring_application_charge': {
                'name': plan_name,
                'price': price,
                'return_url': return_url,
                'test': True  # Set to False in production
            }
        }
        
        response = requests.post(url, json=charge, headers=self.headers)
        response.raise_for_status()
        return response.json()['recurring_application_charge']
    
    def activate_recurring_charge(self, charge_id):
        """Activate recurring charge after merchant approval"""
        url = f"{self.base_url}/recurring_application_charges/{charge_id}/activate.json"
        
        response = requests.post(url, json={}, headers=self.headers)
        response.raise_for_status()
        return response.json()['recurring_application_charge']
    
    def get_recurring_charge(self, charge_id):
        """Get recurring charge details"""
        url = f"{self.base_url}/recurring_application_charges/{charge_id}.json"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()['recurring_application_charge']
    
    def cancel_recurring_charge(self, charge_id):
        """Cancel recurring charge"""
        url = f"{self.base_url}/recurring_application_charges/{charge_id}.json"
        
        response = requests.delete(url, headers=self.headers)
        response.raise_for_status()
        return True

