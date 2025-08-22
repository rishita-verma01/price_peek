from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
import time
from urllib.parse import quote
import threading
import os

app = Flask(__name__)
# Enable CORS for all origins with proper headers
CORS(app, resources={
    r"/*": {
        "origins": ["*"],  # Allow all origins for now
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

# Global driver instance
driver = None
driver_lock = threading.Lock()

def init_driver():
    """Initialize the Chrome WebDriver for Render"""
    global driver
    if driver is None:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # For Render: Use the installed chromium binary
        service = Service(executable_path='/usr/bin/chromium')
        driver = webdriver.Chrome(service=service, options=chrome_options)

def extract_price(price_text):
    """Extract numeric price from text"""
    if not price_text:
        return None
    
    # Remove commas and extract numbers
    price_match = re.search(r'₹\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', price_text)
    if not price_match:
        price_match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', price_text)
    
    if price_match:
        price = price_match.group(1).replace(',', '')
        if price.isdigit():
            return price
    return None

def scrape_amazon_selenium(product_name):
    """Scrape Amazon using Selenium for dynamic content"""
    try:
        with driver_lock:
            init_driver()
            url = f"https://www.amazon.in/s?k={quote(product_name)}"
            driver.get(url)
            
            # Wait for results to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-component-type='s-search-result']"))
            )
            
            # Find all product containers
            products = driver.find_elements(By.CSS_SELECTOR, "[data-component-type='s-search-result']")
            
            for product in products[:5]:
                try:
                    # Try multiple price selectors
                    price_selectors = [
                        "span.a-price-whole",
                        "span.a-offscreen",
                        ".a-price",
                        ".a-color-price"
                    ]
                    
                    price = None
                    for selector in price_selectors:
                        try:
                            price_element = product.find_element(By.CSS_SELECTOR, selector)
                            price_text = price_element.text
                            price = extract_price(price_text)
                            if price:
                                break
                        except NoSuchElementException:
                            continue
                    
                    if price:
                        # Find product link
                        try:
                            link_element = product.find_element(By.CSS_SELECTOR, "a.a-link-normal")
                            product_url = link_element.get_attribute("href")
                            return {'price': f"₹{price}", 'url': product_url, 'available': True}
                        except NoSuchElementException:
                            continue
                            
                except Exception as e:
                    print(f"Error processing Amazon product: {e}")
                    continue
            
            return {'price': 'Not available', 'url': url, 'available': False}
            
    except TimeoutException:
        print("Amazon page load timeout")
        return {'price': 'Not available', 'url': f"https://www.amazon.in/s?k={quote(product_name)}", 'available': False}
    except Exception as e:
        print(f"Amazon scraping error: {str(e)}")
        return {'price': 'Not available', 'url': f"https://www.amazon.in/s?k={quote(product_name)}", 'available': False}

def scrape_flipkart_selenium(product_name):
    """Scrape Flipkart using Selenium for dynamic content"""
    try:
        with driver_lock:
            init_driver()
            url = f"https://www.flipkart.com/search?q={quote(product_name)}"
            driver.get(url)
            
            # Wait for results to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-id]"))
            )
            
            # Find all product containers
            products = driver.find_elements(By.CSS_SELECTOR, "[data-id]")
            
            for product in products[:5]:
                try:
                    # Try multiple price patterns
                    price = None
                    
                    # Pattern 1: Look for elements containing ₹ symbol
                    try:
                        price_elements = product.find_elements(By.XPATH, ".//*[contains(text(), '₹')]")
                        for elem in price_elements:
                            price_text = elem.text
                            price = extract_price(price_text)
                            if price:
                                break
                    except:
                        pass
                    
                    # Pattern 2: Look for common price class patterns
                    if not price:
                        price_selectors = [
                            "div._30jeq3",
                            "div.Nx9bqj",
                            "div._4b5DiR",
                            "div._1vC4OE",
                            "div._2rQ-NK",
                            "[class*='price']",
                            "[class*='Price']"
                        ]
                        
                        for selector in price_selectors:
                            try:
                                price_element = product.find_element(By.CSS_SELECTOR, selector)
                                price_text = price_element.text
                                price = extract_price(price_text)
                                if price:
                                    break
                            except NoSuchElementException:
                                continue
                    
                    if price:
                        # Find product link using multiple patterns
                        product_url = None
                        link_selectors = [
                            "a._1fQZEK",
                            "a.CGtC98",
                            "a._2UzuFa",
                            "a.s1Q9rs",
                            "a[href*='/p/']",
                            "a[href*='pid=']"
                        ]
                        
                        for selector in link_selectors:
                            try:
                                link_element = product.find_element(By.CSS_SELECTOR, selector)
                                href = link_element.get_attribute("href")
                                if href and ("flipkart.com" in href or href.startswith("/")):
                                    product_url = href if href.startswith("http") else f"https://www.flipkart.com{href}"
                                    break
                            except NoSuchElementException:
                                continue
                        
                        if product_url:
                            return {'price': f"₹{price}", 'url': product_url, 'available': True}
                            
                except Exception as e:
                    print(f"Error processing Flipkart product: {e}")
                    continue
            
            return {'price': 'Not available', 'url': url, 'available': False}
            
    except TimeoutException:
        print("Flipkart page load timeout")
        return {'price': 'Not available', 'url': f"https://www.flipkart.com/search?q={quote(product_name)}", 'available': False}
    except Exception as e:
        print(f"Flipkart scraping error: {str(e)}")
        return {'price': 'Not available', 'url': f"https://www.flipkart.com/search?q={quote(product_name)}", 'available': False}

@app.route('/')
def home():
    return jsonify({
        'message': 'Price Comparison API is running!',
        'endpoints': {
            'search': '/search?product=product_name',
            'example': '/search?product=iphone+15'
        }
    })

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/search', methods=['GET'])
def search_product():
    product_name = request.args.get('product', '')
    
    if not product_name:
        return jsonify({'error': 'Product name is required'}), 400
    
    results = []
    
    # Scrape from each store
    stores = [
        ('amazon', 'Amazon India', scrape_amazon_selenium),
        ('flipkart', 'Flipkart', scrape_flipkart_selenium),
    ]
    
    for store, store_name, scraper_func in stores:
        result = scraper_func(product_name)
        results.append({
            'store': store, 
            'storeName': store_name, 
            **result
        })
    
    return jsonify(results)

@app.teardown_appcontext
def shutdown_driver(exception=None):
    """Close the driver when the app shuts down"""
    global driver
    if driver is not None:
        driver.quit()
        driver = None

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
