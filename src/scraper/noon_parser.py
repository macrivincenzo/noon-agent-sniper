from bs4 import BeautifulSoup
from typing import List, Optional
import re
import json
from src.models.product import Product
from src.utils.logger import get_logger

logger = get_logger(__name__)

class NoonParser:
    """Parse HTML from noon.com to extract product information"""
    
    def __init__(self):
        pass
    
    def parse_search_results(self, html: str) -> List[Product]:
        """
        Parse search results page and extract product data.
        Tries multiple strategies to find product information.
        """
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        # Strategy 1: Look for JSON data in script tags
        products_json = self._extract_from_json(soup)
        if products_json:
            logger.info(f"Found {len(products_json)} products in JSON data")
            products.extend(products_json)
        
        # Strategy 2: Look for product cards using CSS selectors
        products_html = self._extract_from_html(soup)
        if products_html:
            logger.info(f"Found {len(products_html)} products in HTML structure")
            products.extend(products_html)
        
        # Remove duplicates based on product URL
        unique_products = self._remove_duplicates(products)
        logger.info(f"Total unique products found: {len(unique_products)}")
        
        return unique_products
    
    def _extract_from_json(self, soup: BeautifulSoup) -> List[Product]:
        """Try to extract product data from JSON in script tags"""
        products = []
        
        # Look for script tags that might contain product data
        scripts = soup.find_all('script', type='application/json')
        scripts.extend(soup.find_all('script', string=re.compile(r'products|items|searchResults', re.I)))
        
        for script in scripts:
            try:
                # Try to parse JSON
                if script.string:
                    data = json.loads(script.string)
                    # Recursively search for product-like objects
                    found_products = self._find_products_in_json(data)
                    products.extend(found_products)
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return products
    
    def _find_products_in_json(self, data, path="") -> List[Product]:
        """Recursively search JSON for product-like objects"""
        products = []
        
        if isinstance(data, dict):
            # Check if this looks like a product object
            if self._looks_like_product(data):
                product = self._json_to_product(data)
                if product:
                    products.append(product)
            
            # Recursively search nested structures
            for key, value in data.items():
                products.extend(self._find_products_in_json(value, f"{path}.{key}"))
        
        elif isinstance(data, list):
            for item in data:
                products.extend(self._find_products_in_json(item, path))
        
        return products
    
    def _looks_like_product(self, obj: dict) -> bool:
        """Check if a dictionary looks like a product object"""
        product_indicators = ['title', 'name', 'price', 'url', 'link', 'sku', 'productId']
        return any(key.lower() in product_indicators for key in obj.keys())
    
    def _json_to_product(self, data: dict) -> Optional[Product]:
        """Convert JSON product data to Product model"""
        try:
            # Map common JSON field names to our Product model
            title = (
                data.get('title') or 
                data.get('name') or 
                data.get('productName') or 
                data.get('displayName') or
                ""
            )
            
            if not title:
                return None
            
            # Extract price
            price = self._extract_price(data)
            if price is None:
                return None
            
            # Extract URL
            url = self._extract_url(data)
            if not url:
                return None
            
            # Build product data
            product_data = {
                'title': title.strip(),
                'price': price,
                'product_url': url,
                'category': data.get('category') or data.get('categoryPath'),
                'image_url': data.get('imageUrl') or data.get('image') or data.get('thumbnail'),
                'sku': data.get('sku') or data.get('productId') or data.get('id'),
                'review_count': data.get('reviewCount') or data.get('reviews') or data.get('numReviews'),
                'average_rating': data.get('rating') or data.get('averageRating') or data.get('starRating'),
                'bsr': data.get('bsr') or data.get('bestSellerRank') or data.get('rank'),
                'bsr_category': data.get('bsrCategory') or data.get('category'),
                'availability': data.get('availability') or data.get('stockStatus') or data.get('inStock'),
                'discount_percentage': data.get('discount') or data.get('discountPercent') or data.get('salePercent'),
                'author': data.get('author') or data.get('authorName'),
                'format': data.get('format') or data.get('bookFormat') or data.get('edition'),
                'publication_date': data.get('publicationDate') or data.get('publishDate') or data.get('releaseDate'),
                'language': data.get('language') or data.get('lang'),
            }
            
            # Create Product object
            return Product(**product_data)
            
        except Exception as e:
            logger.debug(f"Error converting JSON to product: {e}")
            return None
    
    def _extract_from_html(self, soup: BeautifulSoup) -> List[Product]:
        """Extract products using CSS selectors"""
        products = []
        
        # Common selectors for product cards (we'll try multiple)
        selectors = [
            '[data-qa*="product"]',
            '[class*="Product"]',
            '[class*="product"]',
            'a[href*="/uae-en/"]',
            '[data-product-id]',
            '[data-sku]',
        ]
        
        product_elements = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                product_elements.extend(elements)
                break  # Use first selector that finds elements
        
        for element in product_elements:
            product = self._extract_product_info(element)
            if product:
                products.append(product)
        
        return products
    
    def _extract_product_info(self, element) -> Optional[Product]:
        """Extract information from a single product HTML element"""
        try:
            # Find title - use precise method
            title = self._find_text_precise(element, [
                '[class*="title"]',
                '[class*="name"]',
                'h2', 'h3', 'h4',
                '[data-qa*="title"]',
                '[data-qa*="name"]',
            ])
            
            if not title:
                return None
            
            # Find price
            price = self._find_price(element)
            if price is None:
                return None
            
            # Find URL
            url = self._find_url(element)
            if not url:
                return None
            
            # Build product data
            product_data = {
                'title': title.strip(),
                'price': price,
                'product_url': url,
                'category': self._find_category(element),  # Improved method
                'image_url': self._find_image(element),
                'sku': element.get('data-sku') or element.get('data-product-id') or element.get('id'),
                'review_count': self._find_review_count(element),
                'average_rating': self._find_rating(element),
                'discount_percentage': self._find_discount_improved(element),  # Improved method
                'availability': self._find_availability(element),
            }
            
            return Product(**product_data)
            
        except Exception as e:
            logger.debug(f"Error extracting product from HTML: {e}")
            return None
    
    def _find_text_precise(self, element, selectors: List[str]) -> Optional[str]:
        """Find text using multiple CSS selectors - precise, no fallback to all text"""
        for selector in selectors:
            found = element.select_one(selector)
            if found:
                text = found.get_text(strip=True, separator=' ')
                # Only return if text is reasonable length
                if text and 5 <= len(text) <= 200:
                    return text
        return None
    
    def _find_text(self, element, selectors: List[str]) -> Optional[str]:
        """Find text using multiple CSS selectors"""
        for selector in selectors:
            found = element.select_one(selector)
            if found and found.get_text(strip=True):
                return found.get_text(strip=True)
        
        # Fallback: get direct text - but limit it and use separator
        text = element.get_text(strip=True, separator=' ')
        if text and len(text) < 200:  # Reasonable title length
            return text
        
        return None

    def _find_category(self, element) -> Optional[str]:
        """Extract category - be very specific to avoid grabbing everything"""
        # Look for breadcrumb or category links - these are usually more reliable
        category_selectors = [
            '[class*="breadcrumb"] a',
            '[class*="category"] a',
            '[class*="Category"] a',
            'nav[class*="breadcrumb"] a',
            'ol[class*="breadcrumb"] a',
            '[data-qa*="category"]',
            '[data-category]',
        ]
        
        for selector in category_selectors:
            found = element.select_one(selector)
            if found:
                text = found.get_text(strip=True)
                # Categories shouldn't be too long and should be meaningful
                if text and 3 <= len(text) <= 100 and not text.isdigit():
                    return text
        
        # Try to find category in data attributes
        category = element.get('data-category') or element.get('data-cat')
        if category:
            return category
        
        # Don't fallback to getting all text - return None if we can't find it properly
        return None
    
    def _find_discount_improved(self, element) -> Optional[float]:
        """Extract discount percentage - improved to find actual discounts, not cashback"""
        # Look for discount tags with specific classes
        discount_selectors = [
            '[class*="Discount"]',
            '[class*="discount"]',
            '[class*="sale"]',
            '[class*="Sale"]',
            '[class*="off"]',
            '[class*="Off"]',
            '[class*="percent"]',
        ]
        
        for selector in discount_selectors:
            discount_elem = element.select_one(selector)
            if discount_elem:
                text = discount_elem.get_text(strip=True)
                # Look for patterns like "67% Off", "15% discount", etc.
                # But exclude "cashback" percentages
                if 'cashback' not in text.lower():
                    match = re.search(r'(\d+)%\s*(?:Off|off|discount|Discount|sale|Sale)', text)
                    if match:
                        try:
                            discount = float(match.group(1))
                            if 0 <= discount <= 100:
                                return discount
                        except ValueError:
                            pass
        
        # Also check in the element's text directly, but be more careful
        text = element.get_text()
        # Look for discount patterns but exclude cashback
        # Pattern: number followed by % and then "Off" or "discount"
        match = re.search(r'(\d+)%\s*(?:Off|off|discount|Discount|sale|Sale)', text)
        if match and 'cashback' not in text.lower()[:match.start() + 50]:  # Check context
            try:
                discount = float(match.group(1))
                if 0 <= discount <= 100:
                    return discount
            except ValueError:
                pass
        
        return None
    
    def _find_price(self, element) -> Optional[float]:
        """Extract price from element"""
        # Look for price in various formats
        price_selectors = [
            '[class*="price"]',
            '[class*="Price"]',
            '[data-qa*="price"]',
            '[data-price]',
        ]
        
        for selector in price_selectors:
            price_elem = element.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self._parse_price(price_text)
                if price:
                    return price
        
        # Try to find price in element's text
        text = element.get_text()
        price = self._parse_price(text)
        return price
    
    def _parse_price(self, text: str) -> Optional[float]:
        """Parse price from text string"""
        if not text:
            return None
        
        # Look for patterns like "45.99", "AED 45.99", "45,99", etc.
        # Remove currency symbols and extract number
        price_patterns = [
            r'(\d+\.\d+)',  # 45.99
            r'(\d+,\d+)',   # 45,99
            r'(\d+)',       # 45
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text.replace(',', '.'))
            if match:
                try:
                    price = float(match.group(1).replace(',', '.'))
                    # Reasonable price range for books (1 to 10000 AED)
                    if 1 <= price <= 10000:
                        return price
                except ValueError:
                    continue
        
        return None
    
    def _find_url(self, element) -> Optional[str]:
        """Find product URL"""
        # Check if element itself is a link
        if element.name == 'a' and element.get('href'):
            href = element.get('href')
            if 'noon.com' in href or href.startswith('/'):
                return self._normalize_url(href)
        
        # Look for link in children
        link = element.find('a', href=True)
        if link:
            href = link.get('href')
            if 'noon.com' in href or href.startswith('/'):
                return self._normalize_url(href)
        
        # Check data attributes
        url = element.get('data-url') or element.get('data-href') or element.get('data-link')
        if url:
            return self._normalize_url(url)
        
        return None
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL to full format"""
        if url.startswith('http'):
            return url
        elif url.startswith('/'):
            return f"https://www.noon.com{url}"
        else:
            return f"https://www.noon.com/{url}"
    
    def _find_image(self, element) -> Optional[str]:
        """Find product image URL"""
        img = element.find('img')
        if img:
            return img.get('src') or img.get('data-src') or img.get('data-lazy-src')
        return None
    
    def _find_review_count(self, element) -> Optional[int]:
        """Extract review count"""
        text = element.get_text()
        # Look for patterns like "(1247 reviews)", "1247 reviews", etc.
        match = re.search(r'(\d+)\s*reviews?', text, re.I)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return None
    
    def _find_rating(self, element) -> Optional[float]:
        """Extract average rating"""
        # Look for star ratings
        stars = element.select('[class*="star"], [class*="rating"]')
        for star_elem in stars:
            text = star_elem.get_text()
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                try:
                    rating = float(match.group(1))
                    if 0 <= rating <= 5:
                        return rating
                except ValueError:
                    pass
        return None
    
    def _find_discount(self, element) -> Optional[float]:
        """Extract discount percentage"""
        text = element.get_text()
        # Look for patterns like "15% off", "15% discount", etc.
        match = re.search(r'(\d+)%', text)
        if match:
            try:
                discount = float(match.group(1))
                if 0 <= discount <= 100:
                    return discount
            except ValueError:
                pass
        return None
    
    def _find_availability(self, element) -> Optional[str]:
        """Extract availability status"""
        text = element.get_text().lower()
        if 'out of stock' in text or 'unavailable' in text:
            return "Out of Stock"
        elif 'in stock' in text or 'available' in text:
            return "In Stock"
        elif 'low stock' in text:
            return "Low Stock"
        return None
    
    def _extract_price(self, data: dict) -> Optional[float]:
        """Extract price from JSON data"""
        price = (
            data.get('price') or 
            data.get('salePrice') or 
            data.get('currentPrice') or 
            data.get('amount')
        )
        
        if price is None:
            return None
        
        # Handle different price formats
        if isinstance(price, (int, float)):
            return float(price)
        elif isinstance(price, str):
            return self._parse_price(price)
        elif isinstance(price, dict):
            # Sometimes price is an object like {"value": 45.99, "currency": "AED"}
            return float(price.get('value', price.get('amount', 0)))
        
        return None
    
    def _extract_url(self, data: dict) -> Optional[str]:
        """Extract product URL from JSON data"""
        url = (
            data.get('url') or 
            data.get('link') or 
            data.get('productUrl') or 
            data.get('href') or
            data.get('slug')
        )
        
        if not url:
            return None
        
        return self._normalize_url(url)
    
    def _remove_duplicates(self, products: List[Product]) -> List[Product]:
        """Remove duplicate products based on URL"""
        seen_urls = set()
        unique_products = []
        
        for product in products:
            url_str = str(product.product_url)
            if url_str not in seen_urls:
                seen_urls.add(url_str)
                unique_products.append(product)
        
        return unique_products