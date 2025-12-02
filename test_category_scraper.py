from src.agent.category_scraper import CategoryScraper

def test_category_scraper():
    """Test the Category Scraper agent with KDP categories"""
    print("🧪 Testing Category Scraper Agent with KDP Categories...")
    print("-" * 50)
    
    scraper = CategoryScraper(enrich_with_details=False)
    
    # Load KDP config
    kdp_config = scraper.load_kdp_categories()
    subcategories = scraper.get_all_kdp_subcategories(kdp_config)
    
    # Test with just first 5 subcategories
    print(f"\n📚 Testing with first 5 KDP subcategories (out of {len(subcategories)} total)...")
    test_subcategories = subcategories[:5]
    
    results = {}
    for i, subcat_info in enumerate(test_subcategories, 1):
        subcat = subcat_info['subcategory']
        full_path = subcat_info['full_path']
        print(f"\n🔍 Testing {i}/5: {full_path}")
        products = scraper.scrape_category(subcat, max_products=3)
        if products:
            results[full_path] = products
            print(f"   ✅ Found {len(products)} products")
        else:
            print(f"   ⚠️  No products found")
    
    if results:
        scraper.save_kdp_results(results, "data/test_kdp_scraped_results.json")
        print(f"\n✅ Successfully tested {len(results)} categories!")
        print(f"   Total products: {sum(len(p) for p in results.values())}")
    else:
        print("\n⚠️  No results found")

if __name__ == "__main__":
    test_category_scraper()