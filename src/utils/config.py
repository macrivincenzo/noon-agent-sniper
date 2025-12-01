from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os

load_dotenv()

class ScrapingBeeConfig(BaseSettings):
    # Read directly from environment - bypasses Pydantic's env mapping issues
    api_key: str
    endpoint: str = "https://app.scrapingbee.com/api/v1/"
    render_js: bool = True
    premium: bool = True
    country_code: str = "ae"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )
    
    def __init__(self, **kwargs):
        # Manually load from environment if not provided
        if 'api_key' not in kwargs:
            api_key = os.getenv('SCRAPING_BEE_API_KEY')
            if api_key:
                kwargs['api_key'] = api_key
        if 'endpoint' not in kwargs:
            endpoint = os.getenv('SCRAPING_BEE_ENDPOINT')
            if endpoint:
                kwargs['endpoint'] = endpoint
        super().__init__(**kwargs)

config = ScrapingBeeConfig()