from typing import List, Optional, Dict
import json
import os
from src.scraper.noon_scraper import NoonScraper
from src.scraper.noon_parser import NoonParser
from src.scraper.noon_detail_parser import NoonDetailParser
from src.models.product import Product
from src.utils.logger import get_logger

logger = get_logger(__name__)

class CategoryScraper:
    """
    Category Scraper Agent - Scrapes multiple book categories automatically.
    Works with KDP categories structure for accurate market gap analysis.
    Works together with Search Agent and Detail Agent.
    """
    
    def __init__(self, enrich_with_details: bool = False):
        """
        Initialize the Category Scraper
        
        Args:
            enrich_with_details: If True, will also scrape detail pages for each product
        """
        self.scraper = NoonScraper()
        self.search_parser = NoonParser()
        self.detail_parser = NoonDetailParser() if enrich_with_details else None
        self.enrich_with_details = enrich_with_details
    
    def load_kdp_categories(self, config_path: str = "config/kdp_categories.json") -> Dict:
        """Load KDP categories from configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"✅ Loaded KDP categories from {config_path}")
                return config
        except FileNotFoundError:
            logger.error(f"❌ KDP categories file not found: {config_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing KDP categories file: {e}")
            return {}
    
    def load_noon_categories(self, config_path: str = "config/categories.json") -> List[str]:
        """Load Noon.com categories from configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                categories = config.get('book_categories', [])
                logger.info(f"✅ Loaded {len(categories)} Noon.com categories from {config_path}")
                return categories
        except FileNotFoundError:
            logger.error(f"❌ Categories file not found: {config_path}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing categories file: {e}")
            return []
    
    def get_all_kdp_subcategories(self, kdp_config: Dict) -> List[Dict]:
        """
        Extract all subcategories from KDP structure.
        Returns list of dicts with 'main_category' and 'subcategory' keys.
        """
        subcategories = []
        
        if 'main_categories' not in kdp_config:
            return subcategories
        
        for main_cat in kdp_config['main_categories']:
            main_name = main_cat.get('category', '')
            subcats = main_cat.get('subcategories', [])
            
            for subcat in subcats:
                subcategories.append({
                    'main_category': main_name,
                    'subcategory': subcat,
                    'full_path': f"{main_name} > {subcat}"
                })
        
        return subcategories
    
    def scrape_category(self, category: str, max_products: Optional[int] = None) -> List[Product]:
        """
        Scrape a single category
        
        Args:
            category: Category name to scrape (can be main category or subcategory)
            max_products: Maximum number of products to scrape (None = all)
        
        Returns:
            List of Product objects
        """
        logger.info(f"🔍 Scraping category: {category}")
        
        # Step 1: Use Search Agent to find products
        search_query = f"books {category}"
        html = self.scraper.scrape_search(search_query)
        
        if not html:
            logger.warning(f"⚠️  Failed to scrape search results for category: {category}")
            return []
        
        # Step 2: Parse search results
        products = self.search_parser.parse_search_results(html)
        
        if not products:
            logger.warning(f"⚠️  No products found for category: {category}")
            return []
        
        logger.info(f"✅ Found {len(products)} products in search results")
        
        # Step 3: Optionally enrich with detail page data
        if self.enrich_with_details and self.detail_parser:
            logger.info(f"📖 Enriching products with detail page data...")
            enriched_products = []
            
            total = len(products[:max_products] if max_products else products)
            for i, product in enumerate(products[:max_products] if max_products else products, 1):
                logger.info(f"   Enriching product {i}/{total}: {product.title[:50]}...")
                
                # Scrape detail page
                detail_html = self.scraper.scrape(str(product.product_url))
                
                if detail_html:
                    # Enrich product with detail data
                    enriched_product = self.detail_parser.parse_product_detail(
                        detail_html, 
                        existing_product=product
                    )
                    if enriched_product:
                        enriched_products.append(enriched_product)
                else:
                    # If detail scraping fails, keep original product
                    enriched_products.append(product)
            
            products = enriched_products
            logger.info(f"✅ Enriched {len(enriched_products)} products")
        
        # Limit products if max_products specified
        if max_products and len(products) > max_products:
            products = products[:max_products]
        
        # Add category to each product
        for product in products:
            if not product.category:
                product.category = category
        
        logger.info(f"✅ Completed scraping category '{category}': {len(products)} products")
        return products
    
    def scrape_kdp_categories(
        self,
        max_products_per_category: Optional[int] = None,
        config_path: str = "config/kdp_categories.json"
    ) -> Dict[str, List[Product]]:
        """
        Scrape all KDP categories and subcategories.
        Returns a dictionary mapping category paths to product lists.
        
        Args:
            max_products_per_category: Max products per category
            config_path: Path to KDP categories config file
        
        Returns:
            Dictionary with category paths as keys and product lists as values
        """
        kdp_config = self.load_kdp_categories(config_path)
        
        if not kdp_config:
            logger.error("❌ No KDP categories loaded")
            return {}
        
        # Get search strategy settings
        search_strategy = kdp_config.get('search_strategy', {})
        skip_threshold = search_strategy.get('skip_if_no_results_threshold', 0)
        max_products = max_products_per_category or search_strategy.get('max_products_per_category', 50)
        
        # Get all subcategories
        subcategories = self.get_all_kdp_subcategories(kdp_config)
        
        logger.info(f"🚀 Starting to scrape {len(subcategories)} KDP subcategories...")
        logger.info(f"   Strategy: max_products={max_products}, skip_threshold={skip_threshold}")
        
        results = {}
        skipped_count = 0
        
        for i, subcat_info in enumerate(subcategories, 1):
            main_cat = subcat_info['main_category']
            subcat = subcat_info['subcategory']
            full_path = subcat_info['full_path']
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Category {i}/{len(subcategories)}: {full_path}")
            logger.info(f"{'='*60}")
            
            try:
                # Search using the subcategory name
                products = self.scrape_category(subcat, max_products)
                
                # Check if we should skip (too few results)
                if len(products) <= skip_threshold:
                    logger.info(f"⏭️  Skipping '{full_path}' - only {len(products)} products (threshold: {skip_threshold})")
                    skipped_count += 1
                    continue
                
                results[full_path] = products
                logger.info(f"✅ Category '{full_path}' completed: {len(products)} products")
                
            except Exception as e:
                logger.error(f"❌ Error scraping category '{full_path}': {e}")
                continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🎉 KDP Categories Scraping Completed!")
        logger.info(f"   Total categories scraped: {len(subcategories)}")
        logger.info(f"   Categories with products: {len(results)}")
        logger.info(f"   Categories skipped: {skipped_count}")
        logger.info(f"   Total products collected: {sum(len(products) for products in results.values())}")
        logger.info(f"{'='*60}")
        
        return results
    
    def scrape_all_categories(
        self, 
        categories: Optional[List[str]] = None,
        max_products_per_category: Optional[int] = None,
        config_path: str = "config/categories.json"
    ) -> List[Product]:
        """
        Scrape all Noon.com categories (simple list format)
        
        Args:
            categories: List of categories to scrape (None = load from config)
            max_products_per_category: Max products per category
            config_path: Path to categories config file
        
        Returns:
            List of all Product objects from all categories
        """
        if categories is None:
            categories = self.load_noon_categories(config_path)
        
        if not categories:
            logger.error("❌ No categories to scrape")
            return []
        
        logger.info(f"🚀 Starting to scrape {len(categories)} Noon.com categories...")
        
        all_products = []
        
        for i, category in enumerate(categories, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Category {i}/{len(categories)}: {category}")
            logger.info(f"{'='*60}")
            
            try:
                products = self.scrape_category(category, max_products_per_category)
                all_products.extend(products)
                
                logger.info(f"✅ Category '{category}' completed: {len(products)} products")
            except Exception as e:
                logger.error(f"❌ Error scraping category '{category}': {e}")
                continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🎉 Scraping completed!")
        logger.info(f"   Total categories scraped: {len(categories)}")
        logger.info(f"   Total products collected: {len(all_products)}")
        logger.info(f"{'='*60}")
        
        return all_products
    
    def save_products(self, products: List[Product], output_path: str = "data/scraped_products.json"):
        """Save products to JSON file"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        products_data = [p.model_dump() for p in products]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(products_data, f, indent=2, default=str)
        
        logger.info(f"💾 Saved {len(products)} products to {output_path}")
    
    def save_kdp_results(self, results: Dict[str, List[Product]], output_path: str = "data/kdp_scraped_results.json"):
        """Save KDP scraping results (organized by category) to JSON file"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Convert to serializable format
        output_data = {}
        for category_path, products in results.items():
            output_data[category_path] = [p.model_dump() for p in products]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        total_products = sum(len(products) for products in results.values())
        logger.info(f"💾 Saved {len(results)} categories with {total_products} total products to {output_path}")