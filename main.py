from src.scraper.noon_scraper import NoonScraper
import os

def main():
    print("Testing Noon Scraper...")
    
    scraper = NoonScraper()
    
    # Test with a simple search
    search_query = "books"
    print(f"Searching for: {search_query}")
    
    result = scraper.scrape_search(search_query)
    
    if result:
        print("✅ Success! Got HTML content")
        print(f"Content length: {len(result)} characters")
        
        # Save HTML to file for inspection
        os.makedirs("data", exist_ok=True)
        with open("data/sample_search.html", "w", encoding="utf-8") as f:
            f.write(result)
        print("📄 Saved HTML to data/sample_search.html")
    else:
        print("❌ Failed to scrape")

if __name__ == "__main__":
    main()