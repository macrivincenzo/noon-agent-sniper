from src.scraper.noon_parser import NoonParser
import json

def test_parser():
    """Test the HTML parser with the sample search results"""
    print("🧪 Testing Noon Parser...")
    print("-" * 50)
    
    # Read the HTML file
    try:
        with open("data/sample_search.html", "r", encoding="utf-8") as f:
            html = f.read()
        print(f"✅ Loaded HTML file ({len(html)} characters)")
    except FileNotFoundError:
        print("❌ Error: data/sample_search.html not found!")
        print("   Run main.py first to generate the HTML file.")
        return
    
    # Parse the HTML
    parser = NoonParser()
    print("\n📖 Parsing HTML...")
    products = parser.parse_search_results(html)
    
    # Display results
    print(f"\n📊 Results: Found {len(products)} products")
    print("-" * 50)
    
    if products:
        for i, product in enumerate(products[:5], 1):  # Show first 5
            print(f"\n{i}. {product.title}")
            print(f"   Price: {product.price} {product.currency}")
            print(f"   URL: {product.product_url}")
            if product.category:
                print(f"   Category: {product.category}")
            if product.review_count:
                print(f"   Reviews: {product.review_count}")
            if product.average_rating:
                print(f"   Rating: {product.average_rating}/5.0")
        
        if len(products) > 5:
            print(f"\n... and {len(products) - 5} more products")
        
        # Save to JSON for inspection
        products_json = [p.model_dump() for p in products]
        with open("data/parsed_products.json", "w", encoding="utf-8") as f:
            json.dump(products_json, f, indent=2, default=str)
        print(f"\n💾 Saved all products to data/parsed_products.json")
    else:
        print("\n⚠️  No products found. The HTML structure might be different.")
        print("   We may need to adjust the parser selectors.")

if __name__ == "__main__":
    test_parser()