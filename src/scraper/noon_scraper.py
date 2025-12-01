import requests
from typing import Dict, Optional
from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)

class NoonScraper:
    def __init__(self):
        self.api_key = config.api_key
        self.base_url = config.endpoint
        self.params = {
            'api_key': self.api_key,
            'render_js': str(config.render_js).lower(),
            'country_code': config.country_code
        }
    
    def scrape(self, url: str, custom_params: Optional[Dict] = None) -> Optional[str]:
        """Scrape a URL using ScrapingBee"""
        params = {**self.params}
        if custom_params:
            params.update(custom_params)
        
        # Add the target URL
        params['url'] = url
        
        try:
            response = requests.get(self.base_url, params=params)
            
            # Show detailed error if request failed
            if response.status_code != 200:
                logger.error(f"ScrapingBee returned status {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")  # First 500 chars of error
                response.raise_for_status()
            
            return response.text
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error scraping {url}: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Error response: {e.response.text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
    
    def scrape_search(self, search_query: str) -> Optional[str]:
        """Scrape noon.com search results"""
        search_url = f"https://www.noon.com/uae-en/search?q={search_query}"
        return self.scrape(search_url)