from src.scraper.noon_scraper import NoonScraper
from src.scraper.noon_detail_parser import NoonDetailParser
from src.models.product import Product
import json

def test_detail_parser():
    """Test the Detail Agent parser with a real product page"""
    print("🧪 Testing Detail Agent Parser...")
    print("-" * 50)
    
    # Load a product from parsed_products.json
    try:
        with open("data/parsed_products.json", "r", encoding="utf-8") as f:
            products_data = json.load(f)
        
        if not products_data:
            print("❌ No products found in parsed_products.json")
            print("   Run test_parser.py first to generate product data.")
            return
        
        # Get the first product
        first_product_data = products_data[0]
        product = Product(**first_product_data)
        
        print(f"📖 Testing with product: {product.title}")
        print(f"   URL: {product.product_url}")
        print(f"\n📊 Current data (from search results):")
        print(f"   Price: {product.price} {product.currency}")
        print(f"   Category: {product.category or 'Not found'}")
        print(f"   Reviews: {product.review_count or 'Not found'}")
        print(f"   Rating: {product.average_rating or 'Not found'}")
        print(f"   Author: {product.author or 'Not found'}")
        print(f"   Format: {product.format or 'Not found'}")
        print(f"   BSR: {product.bsr or 'Not found'}")
        
        # Scrape the detail page
        print(f"\n🌐 Scraping product detail page...")
        scraper = NoonScraper()
        html = scraper.scrape(str(product.product_url))
        
        if not html:
            print("❌ Failed to scrape product detail page")
            return
        
        print(f"✅ Got HTML ({len(html)} characters)")
        
        # Parse the detail page
        print(f"\n📖 Parsing detail page...")
        detail_parser = NoonDetailParser()
        enriched_product = detail_parser.parse_product_detail(html, existing_product=product)
        
        if not enriched_product:
            print("❌ Failed to parse product detail page")
            return
        
        # Show enriched data
        print(f"\n✨ Enriched data (from detail page):")
        print("-" * 50)
        print(f"   Title: {enriched_product.title}")
        print(f"   Price: {enriched_product.price} {enriched_product.currency}")
        print(f"   Category: {enriched_product.category or 'Not found'}")
        print(f"   Reviews: {enriched_product.review_count or 'Not found'}")
        print(f"   Rating: {enriched_product.average_rating or 'Not found'}")
        print(f"   Author: {enriched_product.author or 'Not found'}")
        print(f"   Format: {enriched_product.format or 'Not found'}")
        print(f"   Publication Date: {enriched_product.publication_date or 'Not found'}")
        print(f"   Language: {enriched_product.language or 'Not found'}")
        print(f"   BSR: {enriched_product.bsr or 'Not found'}")
        if enriched_product.bsr_category:
            print(f"   BSR Category: {enriched_product.bsr_category}")
        print(f"   Availability: {enriched_product.availability or 'Not found'}")
        
        # Show what was added
        print(f"\n📈 Data enrichment summary:")
        print("-" * 50)
        fields_added = []
        if product.category != enriched_product.category and enriched_product.category:
            fields_added.append("Category")
        if product.review_count != enriched_product.review_count and enriched_product.review_count:
            fields_added.append("Review Count")
        if product.average_rating != enriched_product.average_rating and enriched_product.average_rating:
            fields_added.append("Rating")
        if product.author != enriched_product.author and enriched_product.author:
            fields_added.append("Author")
        if product.format != enriched_product.format and enriched_product.format:
            fields_added.append("Format")
        if product.bsr != enriched_product.bsr and enriched_product.bsr:
            fields_added.append("BSR")
        
        if fields_added:
            print(f"   ✅ Successfully extracted: {', '.join(fields_added)}")
        else:
            print(f"   ⚠️  No new data extracted (might need to adjust selectors)")
        
        # Save enriched product for inspection
        enriched_data = enriched_product.model_dump()
        with open("data/enriched_product.json", "w", encoding="utf-8") as f:
            json.dump(enriched_data, f, indent=2, default=str)
        print(f"\n💾 Saved enriched product to data/enriched_product.json")
        
    except FileNotFoundError:
        print("❌ Error: data/parsed_products.json not found!")
        print("   Run test_parser.py first to generate product data.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_detail_parser()