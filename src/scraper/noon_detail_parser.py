from bs4 import BeautifulSoup
from typing import Optional, Dict
import re
import json
from src.models.product import Product
from src.utils.logger import get_logger

logger = get_logger(__name__)

class NoonDetailParser:
    """Parse individual product detail pages from noon.com to extract full product information"""
    
    def __init__(self):
        pass
    
    def parse_product_detail(self, html: str, existing_product: Optional[Product] = None) -> Optional[Product]:
        """
        Parse a product detail page and extract all product information.
        Can enrich an existing Product object or create a new one.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try to extract from JSON first (most reliable)
        product_data = self._extract_from_json(soup)
        
        # If JSON extraction failed or incomplete, try HTML parsing
        if not product_data or not product_data.get('title'):
            html_data = self._extract_from_html(soup)
            if html_data:
                # Merge HTML data with JSON data (JSON takes priority)
                product_data = {**html_data, **product_data}
        
        # If we have an existing product, enrich it
        if existing_product:
            return self._enrich_product(existing_product, product_data)
        
        # Otherwise, create a new product
        if product_data and product_data.get('title') and product_data.get('price'):
            try:
                return Product(**product_data)
            except Exception as e:
                logger.error(f"Error creating Product from detail data: {e}")
                return None
        
        return None
    
    def _extract_from_json(self, soup: BeautifulSoup) -> Dict:
        """Try to extract product data from JSON in script tags"""
        product_data = {}
        
        # Look for script tags with JSON data
        scripts = soup.find_all('script', type='application/json')
        scripts.extend(soup.find_all('script', string=re.compile(r'product|item|data', re.I)))
        
        for script in scripts:
            try:
                if script.string:
                    data = json.loads(script.string)
                    # Recursively search for product data
                    found_data = self._find_product_data_in_json(data)
                    if found_data:
                        product_data.update(found_data)
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return product_data
    
    def _find_product_data_in_json(self, data, path="") -> Dict:
        """Recursively search JSON for product data"""
        result = {}
        
        if isinstance(data, dict):
            # Check if this looks like product data
            if any(key in ['title', 'name', 'productName', 'price', 'rating', 'reviews'] for key in data.keys()):
                # Extract relevant fields
                if 'title' in data or 'name' in data or 'productName' in data:
                    result['title'] = data.get('title') or data.get('name') or data.get('productName')
                if 'price' in data or 'salePrice' in data or 'currentPrice' in data:
                    result['price'] = self._extract_price_value(data.get('price') or data.get('salePrice') or data.get('currentPrice'))
                if 'rating' in data or 'averageRating' in data or 'starRating' in data:
                    result['average_rating'] = self._extract_rating_value(data.get('rating') or data.get('averageRating') or data.get('starRating'))
                if 'reviewCount' in data or 'reviews' in data or 'numReviews' in data:
                    result['review_count'] = self._extract_review_count_value(data.get('reviewCount') or data.get('reviews') or data.get('numReviews'))
                if 'author' in data or 'authorName' in data:
                    result['author'] = data.get('author') or data.get('authorName')
                if 'category' in data or 'categoryPath' in data:
                    result['category'] = data.get('category') or data.get('categoryPath')
                if 'format' in data or 'bookFormat' in data or 'edition' in data:
                    result['format'] = data.get('format') or data.get('bookFormat') or data.get('edition')
                if 'publicationDate' in data or 'publishDate' in data or 'releaseDate' in data:
                    result['publication_date'] = data.get('publicationDate') or data.get('publishDate') or data.get('releaseDate')
                if 'language' in data or 'lang' in data:
                    result['language'] = data.get('language') or data.get('lang')
                if 'bsr' in data or 'bestSellerRank' in data or 'rank' in data:
                    result['bsr'] = self._extract_bsr_value(data.get('bsr') or data.get('bestSellerRank') or data.get('rank'))
                if 'availability' in data or 'stockStatus' in data or 'inStock' in data:
                    result['availability'] = self._extract_availability_value(data.get('availability') or data.get('stockStatus') or data.get('inStock'))
            
            # Recursively search nested structures
            for key, value in data.items():
                nested_result = self._find_product_data_in_json(value, f"{path}.{key}")
                if nested_result:
                    result.update(nested_result)
        
        elif isinstance(data, list):
            for item in data:
                nested_result = self._find_product_data_in_json(item, path)
                if nested_result:
                    result.update(nested_result)
        
        return result
    
    def _extract_from_html(self, soup: BeautifulSoup) -> Dict:
        """Extract product data using CSS selectors"""
        product_data = {}
        
        # Extract title - IMPROVED to avoid seller names
        title = self._find_title(soup)  # Use new dedicated method
        if title:
            product_data['title'] = title
        
        # Extract price - IMPROVED to get sale price
        price = self._find_price_improved(soup)  # Use new improved method
        if price:
            product_data['price'] = price
        
        # Extract category
        category = self._find_category(soup)
        if category:
            product_data['category'] = category
        
        # Extract author
        author = self._find_author(soup)
        if author:
            product_data['author'] = author
        
        # Extract format
        format_type = self._find_format(soup)
        if format_type:
            product_data['format'] = format_type
        
        # Extract publication date
        pub_date = self._find_publication_date(soup)
        if pub_date:
            product_data['publication_date'] = pub_date
        
        # Extract language
        language = self._find_language(soup)
        if language:
            product_data['language'] = language
        
        # Extract reviews and rating
        review_count = self._find_review_count(soup)
        if review_count:
            product_data['review_count'] = review_count
        
        rating = self._find_rating(soup)
        if rating:
            product_data['average_rating'] = rating
        
        # Extract BSR
        bsr = self._find_bsr(soup)
        if bsr:
            product_data['bsr'] = bsr['rank']
            product_data['bsr_category'] = bsr['category']
        
        # Extract availability
        availability = self._find_availability(soup)
        if availability:
            product_data['availability'] = availability
        
        return product_data
    
    def _find_text(self, soup: BeautifulSoup, selectors: list) -> Optional[str]:
        """Find text using CSS selectors"""
        for selector in selectors:
            found = soup.select_one(selector)
            if found:
                text = found.get_text(strip=True, separator=' ')
                if text and len(text) > 0:
                    return text
        return None
    
    def _find_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product title - avoid seller names and other non-title text"""
        # Strategy 1: Look for title in main product section (most reliable)
        title_selectors = [
            'h1[class*="product"]',
            'h1[class*="Product"]',
            '[class*="ProductTitle"]',
            '[class*="product-title"]',
            '[class*="productName"]',
            '[data-qa*="product-title"]',
            '[data-qa*="product-name"]',
            'h1:not([class*="seller"]):not([class*="Seller"])',
        ]
        
        for selector in title_selectors:
            found = soup.select_one(selector)
            if found:
                text = found.get_text(strip=True, separator=' ')
                # Validate it's a real title (not seller name, not too short/long)
                if (text and 
                    10 <= len(text) <= 200 and  # Reasonable title length
                    'seller' not in text.lower() and
                    'sold by' not in text.lower() and
                    not text.lower().startswith('buy') and
                    not text.isdigit()):
                    return text
        
        # Strategy 2: Look for h1 but exclude seller sections
        h1_elements = soup.find_all('h1')
        for h1 in h1_elements:
            # Skip if it's in a seller section
            parent = h1.find_parent(['div', 'section', 'article'])
            if parent:
                parent_classes = ' '.join(parent.get('class', [])).lower()
                if 'seller' in parent_classes or 'merchant' in parent_classes:
                    continue
            
            text = h1.get_text(strip=True, separator=' ')
            if (text and 
                10 <= len(text) <= 200 and
                'seller' not in text.lower() and
                'sold by' not in text.lower()):
                return text
        
        # Strategy 3: Look in meta tags (most reliable)
        title_meta = (soup.find('meta', {'property': 'og:title'}) or 
                     soup.find('meta', {'name': 'title'}) or
                     soup.find('title'))
        if title_meta:
            title_text = title_meta.get('content') or title_meta.get_text(strip=True)
            # Clean up meta title (might have " | Noon.com" suffix)
            if title_text:
                title_text = re.sub(r'\s*\|\s*Noon.*$', '', title_text, flags=re.I)
                if (title_text and 
                    10 <= len(title_text) <= 200 and
                    'seller' not in title_text.lower()):
                    return title_text.strip()
        
        return None
    
    def _find_price_improved(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract price - prioritize sale price over original price"""
        # Strategy 1: Look for sale/current price first (this is what we want)
        sale_price_selectors = [
            '[class*="sale-price"]',
            '[class*="SalePrice"]',
            '[class*="current-price"]',
            '[class*="CurrentPrice"]',
            '[class*="price"][class*="sale"]',
            '[data-qa*="sale-price"]',
            '[data-qa*="current-price"]',
        ]
        
        for selector in sale_price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self._parse_price(price_text)
                if price:
                    return price
        
        # Strategy 2: Look for any price, but prefer ones not marked as "original" or "was"
        price_selectors = [
            '[class*="price"]:not([class*="original"]):not([class*="was"]):not([class*="strike"])',
            '[class*="Price"]:not([class*="original"]):not([class*="was"]):not([class*="strike"])',
            '[data-qa*="price"]',
            '[data-price]',
        ]
        
        for selector in price_selectors:
            price_elems = soup.select(selector)
            for price_elem in price_elems:
                # Skip if it's clearly an original/was price
                text = price_elem.get_text(strip=True).lower()
                if 'was' in text or 'original' in text or 'before' in text:
                    continue
                
                price_text = price_elem.get_text(strip=True)
                price = self._parse_price(price_text)
                if price:
                    # Prefer lower prices (sale prices are usually lower)
                    return price
        
        # Strategy 3: Look for price in structured data
        price_meta = soup.find('meta', {'property': 'product:price:amount'})
        if price_meta:
            price_value = price_meta.get('content')
            if price_value:
                try:
                    price = float(price_value)
                    if 1 <= price <= 10000:
                        return price
                except ValueError:
                    pass
        
        return None
    
    def _find_category(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract category - filter out navigation breadcrumbs"""
        # Strategy 1: Look for actual category links (not navigation)
        category_selectors = [
            '[class*="category"]:not([class*="breadcrumb"])',
            '[data-qa*="category"]',
            '[itemprop="category"]',
            '[class*="Category"]:not([class*="breadcrumb"])',
        ]
        
        for selector in category_selectors:
            found = soup.select(selector)
            if found:
                categories = []
                for elem in found:
                    text = elem.get_text(strip=True)
                    # Filter out navigation items
                    if (text and len(text) > 2 and 
                        text.lower() not in ['home', 'books', 'noon', 'uae', 'oman', 'qatar', 'saudi'] and
                        not text.startswith('noon')):
                        categories.append(text)
                
                if categories:
                    # Return the most specific category (usually the last one)
                    return categories[-1] if len(categories) == 1 else ' > '.join(categories[-2:])
        
        # Strategy 2: Look in breadcrumbs but filter better
        breadcrumb_selectors = [
            'nav[class*="breadcrumb"] a',
            'ol[class*="breadcrumb"] a',
            '[class*="breadcrumb"] a',
        ]
        
        categories = []
        for selector in breadcrumb_selectors:
            found = soup.select(selector)
            if found:
                for elem in found:
                    text = elem.get_text(strip=True)
                    # Better filtering - exclude navigation and country names
                    if (text and len(text) > 2 and 
                        text.lower() not in ['home', 'books', 'noon', 'uae', 'oman', 'qatar', 'saudi', 'egypt', 'kuwait'] and
                        not text.startswith('noon') and
                        not text.isdigit()):
                        categories.append(text)
                
                if categories:
                    # Filter to only book-related categories
                    book_categories = [c for c in categories if any(word in c.lower() for word in ['book', 'fiction', 'non-fiction', 'literature', 'education', 'children'])]
                    if book_categories:
                        return ' > '.join(book_categories[-2:])
                    # If no book-specific categories, return last meaningful ones
                    return ' > '.join(categories[-2:]) if len(categories) >= 2 else categories[-1]
        
        return None
    
    def _find_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author name - be more precise"""
        # Strategy 1: Look for author in structured data (most reliable)
        author_meta = (soup.find('meta', {'property': 'book:author'}) or 
                      soup.find('meta', {'name': 'author'}) or
                      soup.find('meta', {'property': 'og:book:author'}))
        if author_meta:
            author = author_meta.get('content', '').strip()
            if author and len(author) > 2 and 'noon' not in author.lower():
                return author
        
        # Strategy 2: Look for author in specific sections
        author_selectors = [
            '[class*="author"]:not([class*="noon"]):not([class*="seller"])',
            '[class*="Author"]:not([class*="noon"]):not([class*="seller"])',
            '[data-qa*="author"]',
            '[itemprop="author"]',
        ]
        
        for selector in author_selectors:
            found = soup.select(selector)
            for elem in found:
                text = elem.get_text(strip=True)
                # Clean up the text
                text = re.sub(r'^Author:?\s*', '', text, flags=re.I)
                text = re.sub(r'^By:?\s*', '', text, flags=re.I)
                # Filter out invalid authors
                if (text and len(text) > 2 and 
                    'noon' not in text.lower() and
                    'seller' not in text.lower() and
                    not text.startswith('http') and
                    len(text) < 100):  # Author names shouldn't be too long
                    return text
        
        # Strategy 3: Look for "By [Author Name]" pattern
        page_text = soup.get_text()
        author_patterns = [
            r'By\s+([A-Z][a-zA-Z\s]+?)(?:\s|,|$)',  # "By John Smith"
            r'Author:\s*([A-Z][a-zA-Z\s]+?)(?:\s|,|$)',  # "Author: John Smith"
        ]
        
        for pattern in author_patterns:
            match = re.search(pattern, page_text)
            if match:
                author = match.group(1).strip()
                if (author and len(author) > 2 and 
                    'noon' not in author.lower() and
                    len(author) < 100):
                    return author
        
        return None
    
    def _find_format(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract book format - be more precise"""
        # Common book formats
        valid_formats = ['Hardcover', 'Paperback', 'eBook', 'Audiobook', 'Kindle', 'PDF', 'Mass Market Paperback']
        
        # Strategy 1: Look for format in specific elements
        format_selectors = [
            '[class*="format"]:not([class*="price"]):not([class*="discount"])',
            '[class*="Format"]:not([class*="price"]):not([class*="discount"])',
            '[data-qa*="format"]',
            '[itemprop="bookFormat"]',
        ]
        
        for selector in format_selectors:
            found = soup.select_one(selector)
            if found:
                text = found.get_text(strip=True)
                # Clean up
                text = re.sub(r'^Format:?\s*', '', text, flags=re.I)
                # Check if it matches a valid format
                for valid_format in valid_formats:
                    if valid_format.lower() in text.lower():
                        return valid_format
                # If text is short and looks like a format, return it
                if text and len(text) < 30 and not any(char.isdigit() for char in text[:5]):
                    return text
        
        # Strategy 2: Search page text for format keywords
        page_text = soup.get_text()
        for format_type in valid_formats:
            # Look for format in context like "Format: Paperback" or "Paperback Edition"
            pattern = rf'(?:Format|Edition|Type)[:\s]*{re.escape(format_type)}|{re.escape(format_type)}(?:\s+Edition|\s+Format)'
            if re.search(pattern, page_text, re.I):
                return format_type
        
        return None
    
    def _find_publication_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date"""
        date_selectors = [
            '[class*="publication"]',
            '[class*="publish"]',
            '[class*="date"]',
            '[data-qa*="date"]',
            'span:contains("Published")',
            'div:contains("Published")',
        ]
        
        for selector in date_selectors:
            found = soup.select_one(selector)
            if found:
                text = found.get_text(strip=True)
                # Extract date pattern
                date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{4})', text)
                if date_match:
                    return date_match.group(1)
        
        return None
    
    def _find_language(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract book language"""
        language_selectors = [
            '[class*="language"]',
            '[class*="Language"]',
            '[data-qa*="language"]',
            'span:contains("Language")',
            'div:contains("Language")',
        ]
        
        for selector in language_selectors:
            found = soup.select_one(selector)
            if found:
                text = found.get_text(strip=True)
                text = re.sub(r'^Language:?\s*', '', text, flags=re.I)
                if text and len(text) > 2:
                    return text
        
        return None
    
    def _find_review_count(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract review count"""
        review_selectors = [
            '[class*="review"]',
            '[class*="Review"]',
            '[data-qa*="review"]',
        ]
        
        for selector in review_selectors:
            found = soup.select_one(selector)
            if found:
                text = found.get_text()
                match = re.search(r'(\d+)\s*reviews?', text, re.I)
                if match:
                    try:
                        return int(match.group(1))
                    except ValueError:
                        pass
        
        return None
    
    def _find_rating(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract average rating"""
        rating_selectors = [
            '[class*="rating"]',
            '[class*="Rating"]',
            '[class*="star"]',
            '[data-qa*="rating"]',
            '[itemprop="ratingValue"]',
        ]
        
        for selector in rating_selectors:
            found = soup.select_one(selector)
            if found:
                text = found.get_text()
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    try:
                        rating = float(match.group(1))
                        if 0 <= rating <= 5:
                            return rating
                    except ValueError:
                        pass
        
        return None
    
    def _find_bsr(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract Best Seller Rank - CRITICAL for decision making"""
        # Multiple strategies to find BSR
        bsr_patterns = [
            r'#(\d+)\s+in\s+(.+?)(?:\s*\(|$)',  # "#1234 in Books > Fiction"
            r'Best Seller.*?#(\d+)\s+in\s+(.+?)(?:\s*\(|$)',  # "Best Seller #1234 in Books"
            r'Rank.*?#(\d+)\s+in\s+(.+?)(?:\s*\(|$)',  # "Rank #1234 in Books"
            r'#(\d+)\s+in\s+([A-Z][^#]+?)(?:\s*\(|$)',  # "#1234 in Category Name"
            r'(\d+)\s+in\s+(.+?)(?:\s*\(|$)',  # "1234 in Books" (without #)
        ]
        
        # Strategy 1: Look for BSR in specific elements
        bsr_selectors = [
            '[class*="rank"]',
            '[class*="Rank"]',
            '[class*="bestseller"]',
            '[class*="BestSeller"]',
            '[class*="BSR"]',
            '[data-qa*="rank"]',
            '[data-qa*="bestseller"]',
            '[itemprop="position"]',
        ]
        
        for selector in bsr_selectors:
            found = soup.select(selector)
            for elem in found:
                text = elem.get_text()
                for pattern in bsr_patterns:
                    match = re.search(pattern, text, re.I)
                    if match:
                        try:
                            rank = int(match.group(1))
                            category = match.group(2).strip()
                            # Validate - rank should be reasonable (1 to millions)
                            if 1 <= rank <= 10000000 and len(category) > 2:
                                return {
                                    'rank': rank,
                                    'category': category
                                }
                        except (ValueError, IndexError):
                            continue
        
        # Strategy 2: Search entire page text for BSR patterns
        page_text = soup.get_text()
        for pattern in bsr_patterns:
            matches = re.finditer(pattern, page_text, re.I)
            for match in matches:
                try:
                    rank = int(match.group(1))
                    category = match.group(2).strip()
                    # Additional validation - category should look like a real category
                    if (1 <= rank <= 10000000 and 
                        len(category) > 2 and 
                        category.lower() not in ['the', 'a', 'an', 'in', 'of', 'and']):
                        return {
                            'rank': rank,
                            'category': category
                        }
                except (ValueError, IndexError):
                    continue
        
        # Strategy 3: Look in JSON data
        scripts = soup.find_all('script', type='application/json')
        for script in scripts:
            try:
                if script.string:
                    data = json.loads(script.string)
                    bsr_data = self._find_bsr_in_json(data)
                    if bsr_data:
                        return bsr_data
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return None
    
    def _find_bsr_in_json(self, data) -> Optional[Dict]:
        """Recursively search JSON for BSR data"""
        if isinstance(data, dict):
            # Look for BSR-related keys
            bsr_keys = ['bsr', 'bestSellerRank', 'rank', 'salesRank', 'bestsellerRank']
            for key in bsr_keys:
                if key.lower() in str(data.keys()).lower():
                    rank_value = data.get(key) or data.get(key.lower()) or data.get(key.upper())
                    if rank_value:
                        try:
                            rank = int(rank_value) if isinstance(rank_value, (int, str)) else None
                            if rank and 1 <= rank <= 10000000:
                                category = data.get('category') or data.get('bsrCategory') or data.get('categoryPath')
                                return {
                                    'rank': rank,
                                    'category': category or 'Unknown'
                                }
                        except (ValueError, TypeError):
                            pass
            
            # Recursively search nested structures
            for value in data.values():
                result = self._find_bsr_in_json(value)
                if result:
                    return result
        
        elif isinstance(data, list):
            for item in data:
                result = self._find_bsr_in_json(item)
                if result:
                    return result
        
        return None

    def _find_availability(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract availability status"""
        availability_selectors = [
            '[class*="stock"]',
            '[class*="Stock"]',
            '[class*="availability"]',
            '[data-qa*="stock"]',
        ]
        
        for selector in availability_selectors:
            found = soup.select_one(selector)
            if found:
                text = found.get_text().lower()
                if 'out of stock' in text or 'unavailable' in text:
                    return "Out of Stock"
                elif 'in stock' in text or 'available' in text:
                    return "In Stock"
                elif 'low stock' in text:
                    return "Low Stock"
        
        return None
    
    def _enrich_product(self, product: Product, detail_data: Dict) -> Product:
        """Enrich an existing Product with detail page data"""
        # Create a dict from existing product
        product_dict = product.model_dump()
        
        # Update with detail data (only if detail data has values)
        for key, value in detail_data.items():
            if value is not None and value != "":
                # Special handling for title - don't overwrite if new title looks like a category
                if key == 'title':
                    # If the new title is too short or looks like a category, keep the original
                    if (len(value) < 15 or 
                        value.lower() in ['pre-school', 'early learning', 'books', 'fiction', 'non-fiction'] or
                        '&' in value and len(value) < 30):  # Categories often have "&" and are short
                        # Keep original title, don't update
                        continue
                
                product_dict[key] = value
        
        # Update scraped_at timestamp
        from datetime import datetime
        product_dict['scraped_at'] = datetime.now()
        
        # Create new Product with enriched data
        return Product(**product_dict)
    
    def _extract_price_value(self, value) -> Optional[float]:
        """Extract price from various formats"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return self._parse_price(value)
        if isinstance(value, dict):
            return float(value.get('value', value.get('amount', 0)))
        return None
    
    def _extract_rating_value(self, value) -> Optional[float]:
        """Extract rating from various formats"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            rating = float(value)
            return rating if 0 <= rating <= 5 else None
        if isinstance(value, str):
            match = re.search(r'(\d+\.?\d*)', value)
            if match:
                rating = float(match.group(1))
                return rating if 0 <= rating <= 5 else None
        return None
    
    def _extract_review_count_value(self, value) -> Optional[int]:
        """Extract review count from various formats"""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            match = re.search(r'(\d+)', value)
            if match:
                return int(match.group(1))
        return None
    
    def _extract_bsr_value(self, value) -> Optional[int]:
        """Extract BSR from various formats"""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            match = re.search(r'(\d+)', value)
            if match:
                return int(match.group(1))
        return None
    
    def _extract_availability_value(self, value) -> Optional[str]:
        """Extract availability from various formats"""
        if value is None:
            return None
        if isinstance(value, str):
            value_lower = value.lower()
            if 'out of stock' in value_lower or 'unavailable' in value_lower:
                return "Out of Stock"
            elif 'in stock' in value_lower or 'available' in value_lower:
                return "In Stock"
            elif 'low stock' in value_lower:
                return "Low Stock"
        elif isinstance(value, bool):
            return "In Stock" if value else "Out of Stock"
        return None