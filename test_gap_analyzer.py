from src.agent.gap_analyzer import GapAnalyzer
import json

def test_gap_analyzer():
    """Test the Gap Analyzer with scraped results"""
    print("🧪 Testing Gap Analyzer Agent...")
    print("-" * 50)
    
    # Load test results
    try:
        with open("data/test_kdp_scraped_results.json", "r", encoding="utf-8") as f:
            scraped_results = json.load(f)
        
        print(f"✅ Loaded {len(scraped_results)} categories from test results")
    except FileNotFoundError:
        print("❌ Error: data/test_kdp_scraped_results.json not found!")
        print("   Run test_category_scraper.py first to generate test data.")
        return
    
    # Convert JSON back to Product objects
    from src.models.product import Product
    products_by_category = {}
    for category_path, products_data in scraped_results.items():
        products = [Product(**p) for p in products_data]
        products_by_category[category_path] = products
    
    # Initialize Gap Analyzer
    analyzer = GapAnalyzer(
        max_avg_reviews=50,  # Noon.com scale
        max_avg_price=200.0,
        min_products_for_demand=3
    )
    
    # Analyze all categories
    print("\n🔍 Analyzing categories...")
    opportunities = analyzer.analyze_all_categories(products_by_category)
    
    # Generate report
    report = analyzer.generate_report(opportunities, "data/test_gap_analysis_report.json")
    
    # Print summary
    analyzer.print_summary(opportunities)
    
    print(f"\n💾 Full report saved to data/test_gap_analysis_report.json")

if __name__ == "__main__":
    test_gap_analyzer()