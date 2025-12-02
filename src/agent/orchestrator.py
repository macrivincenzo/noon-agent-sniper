from typing import List, Dict, Optional
import json
import os
from datetime import datetime
from src.agent.category_scraper import CategoryScraper
from src.agent.gap_analyzer import GapAnalyzer
from src.scraper.noon_scraper import NoonScraper
from src.scraper.noon_detail_parser import NoonDetailParser
from src.models.product import Product
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Orchestrator:
    """
    Orchestrator Agent - The conductor of the system.
    Coordinates all agents to work together automatically.
    Uses smart enrichment: only enriches high-opportunity categories.
    Works incrementally: processes one category at a time.
    """
    
    def __init__(
        self,
        enrich_threshold: float = 50.0,
        max_products_per_category: Optional[int] = None,
        enrich_with_details: bool = True
    ):
        """
        Initialize the Orchestrator
        
        Args:
            enrich_threshold: Only enrich categories with opportunity score above this
            max_products_per_category: Max products to scrape per category
            enrich_with_details: Whether to use smart enrichment
        """
        self.category_scraper = CategoryScraper(enrich_with_details=False)  # Basic scraping only
        self.gap_analyzer = GapAnalyzer()
        self.scraper = NoonScraper()  # For detail page scraping
        self.detail_parser = NoonDetailParser()  # For smart enrichment
        self.enrich_threshold = enrich_threshold
        self.max_products = max_products_per_category
        self.enrich_with_details = enrich_with_details
        
        # Results tracking
        self.scraped_results = {}
        self.opportunities = []
        self.stats = {
            'categories_scraped': 0,
            'categories_analyzed': 0,
            'categories_enriched': 0,
            'opportunities_found': 0,
            'errors': 0
        }
    
    def run_full_analysis(
        self,
        config_path: str = "config/kdp_categories.json",
        output_dir: str = "data"
    ) -> Dict:
        """
        Run the complete analysis workflow:
        1. Scrape all KDP categories (incremental)
        2. Analyze each category immediately
        3. Smart enrichment for high-opportunity categories
        4. Generate final report
        
        Args:
            config_path: Path to KDP categories config
            output_dir: Directory to save results
        
        Returns:
            Dictionary with final results and statistics
        """
        logger.info("="*70)
        logger.info("🚀 ORCHESTRATOR: Starting Full Analysis")
        logger.info("="*70)
        logger.info(f"   Strategy: Incremental + Smart Enrichment")
        logger.info(f"   Enrichment threshold: {self.enrich_threshold}")
        logger.info(f"   Max products per category: {self.max_products or 'unlimited'}")
        logger.info("="*70)
        
        # Load KDP categories
        kdp_config = self.category_scraper.load_kdp_categories(config_path)
        if not kdp_config:
            logger.error("❌ Failed to load KDP categories")
            return {'error': 'Failed to load KDP categories'}
        
        subcategories = self.category_scraper.get_all_kdp_subcategories(kdp_config)
        search_strategy = kdp_config.get('search_strategy', {})
        skip_threshold = search_strategy.get('skip_if_no_results_threshold', 0)
        max_products = self.max_products or search_strategy.get('max_products_per_category', 50)
        
        logger.info(f"📚 Found {len(subcategories)} KDP subcategories to process")
        logger.info("")
        
        # Process each category incrementally
        for i, subcat_info in enumerate(subcategories, 1):
            main_cat = subcat_info['main_category']
            subcat = subcat_info['subcategory']
            full_path = subcat_info['full_path']
            
            logger.info(f"\n{'='*70}")
            logger.info(f"📦 Category {i}/{len(subcategories)}: {full_path}")
            logger.info(f"{'='*70}")
            
            try:
                # Step 1: Scrape category (uses NoonParser internally)
                products = self.category_scraper.scrape_category(subcat, max_products)
                
                if len(products) <= skip_threshold:
                    logger.info(f"⏭️  Skipping '{full_path}' - only {len(products)} products (threshold: {skip_threshold})")
                    continue
                
                self.scraped_results[full_path] = products
                self.stats['categories_scraped'] += 1
                logger.info(f"✅ Scraped {len(products)} products")
                
                # Step 2: Quick analysis with basic data
                analysis = self.gap_analyzer.analyze_category(full_path, products)
                opportunity_score = analysis.get('opportunity_score', 0)
                
                logger.info(f"📊 Quick Analysis: Score = {opportunity_score}/100")
                logger.info(f"   Status: {analysis.get('status', 'unknown')}")
                logger.info(f"   Recommendation: {analysis.get('recommendation', 'unknown')}")
                
                # Step 3: Smart enrichment (only if high opportunity)
                if self.enrich_with_details and opportunity_score >= self.enrich_threshold:
                    logger.info(f"✨ High opportunity detected! Enriching with detail data...")
                    enriched_products = self._enrich_category_products(products)
                    
                    if enriched_products:
                        # Re-analyze with enriched data
                        analysis = self.gap_analyzer.analyze_category(full_path, enriched_products)
                        self.scraped_results[full_path] = enriched_products
                        self.stats['categories_enriched'] += 1
                        logger.info(f"📊 Re-analyzed with enriched data: Score = {analysis.get('opportunity_score', 0)}/100")
                
                # Step 4: Save opportunity if found
                if analysis.get('recommendation') != 'skip':
                    self.opportunities.append(analysis)
                    self.stats['opportunities_found'] += 1
                    logger.info(f"🎯 Opportunity found! Total: {self.stats['opportunities_found']}")
                
                self.stats['categories_analyzed'] += 1
                
                # Show progress summary
                logger.info(f"📈 Progress: {self.stats['opportunities_found']} opportunities found so far")
                
            except Exception as e:
                logger.error(f"❌ Error processing category '{full_path}': {e}")
                self.stats['errors'] += 1
                continue
        
        # Step 5: Generate final report
        logger.info(f"\n{'='*70}")
        logger.info("📊 Generating Final Report...")
        logger.info(f"{'='*70}")
        
        # Sort opportunities by score
        self.opportunities.sort(key=lambda x: x.get('opportunity_score', 0), reverse=True)
        
        # Generate report
        report = self.gap_analyzer.generate_report(
            self.opportunities,
            output_path=os.path.join(output_dir, "orchestrator_analysis_report.json")
        )
        
        # Save scraped results
        self._save_scraped_results(output_dir)
        
        # Print final summary
        self._print_final_summary()
        
        return {
            'opportunities': self.opportunities,
            'scraped_results': self.scraped_results,
            'stats': self.stats,
            'report': report
        }
    
    def _enrich_category_products(self, products: List[Product]) -> List[Product]:
        """
        Enrich products with detail page data.
        Called only for high-opportunity categories.
        """
        enriched_products = []
        
        for i, product in enumerate(products, 1):
            try:
                logger.info(f"   Enriching product {i}/{len(products)}: {product.title[:50]}...")
                
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
                        enriched_products.append(product)  # Keep original if enrichment fails
                else:
                    enriched_products.append(product)  # Keep original if scraping fails
                    
            except Exception as e:
                logger.debug(f"   Error enriching product {product.title[:50]}: {e}")
                enriched_products.append(product)  # Keep original on error
        
        return enriched_products
    
    def _save_scraped_results(self, output_dir: str):
        """Save scraped results to JSON file"""
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "orchestrator_scraped_results.json")
        
        # Convert to serializable format
        output_data = {}
        for category_path, products in self.scraped_results.items():
            output_data[category_path] = [p.model_dump() for p in products]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        total_products = sum(len(products) for products in self.scraped_results.values())
        logger.info(f"💾 Saved {len(self.scraped_results)} categories with {total_products} products to {output_path}")
    
    def _print_final_summary(self):
        """Print final summary statistics"""
        logger.info(f"\n{'='*70}")
        logger.info("🎉 ORCHESTRATOR: Analysis Complete!")
        logger.info(f"{'='*70}")
        logger.info(f"📊 Statistics:")
        logger.info(f"   Categories scraped: {self.stats['categories_scraped']}")
        logger.info(f"   Categories analyzed: {self.stats['categories_analyzed']}")
        logger.info(f"   Categories enriched: {self.stats['categories_enriched']}")
        logger.info(f"   Opportunities found: {self.stats['opportunities_found']}")
        logger.info(f"   Errors: {self.stats['errors']}")
        
        if self.opportunities:
            high_opp = len([o for o in self.opportunities if o.get('opportunity_score', 0) >= 70])
            moderate_opp = len([o for o in self.opportunities if 50 <= o.get('opportunity_score', 0) < 70])
            
            logger.info(f"\n🎯 Opportunities Breakdown:")
            logger.info(f"   High opportunities (70+): {high_opp}")
            logger.info(f"   Moderate opportunities (50-69): {moderate_opp}")
            logger.info(f"   Low opportunities (<50): {len(self.opportunities) - high_opp - moderate_opp}")
        
        logger.info(f"{'='*70}")