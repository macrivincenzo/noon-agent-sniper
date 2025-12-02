from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

class Product(BaseModel):
    """Structured product data model for Noon.com products"""
    
    title: str
    price: float
    currency: str = "AED"
    product_url: HttpUrl
    category: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    sku: Optional[str] = None
    
    # Review data
    review_count: Optional[int] = None
    average_rating: Optional[float] = None  # e.g., 4.5 out of 5.0
    
    # Best Seller Rank (BSR)
    bsr: Optional[int] = None  # Lower number = better rank (e.g., #1 is best)
    bsr_category: Optional[str] = None  # Category where BSR applies
    
    # Market demand signals
    availability: Optional[str] = None  # "In Stock", "Out of Stock", "Low Stock"
    discount_percentage: Optional[float] = None  # Discount percentage (e.g., 15.5)
    
    # Competitive intelligence
    author: Optional[str] = None  # Author name
    format: Optional[str] = None  # "Hardcover", "Paperback", "eBook", "Audiobook"
    publication_date: Optional[str] = None  # Publication date
    
    # Content metadata
    language: Optional[str] = None  # Book language
    
    scraped_at: datetime = datetime.now()
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "The Great Gatsby",
                "price": 45.99,
                "currency": "AED",
                "product_url": "https://www.noon.com/uae-en/the-great-gatsby",
                "category": "Books > Fiction",
                "image_url": "https://f.nooncdn.com/products/...",
                "sku": "N123456789",
                "review_count": 1247,
                "average_rating": 4.5,
                "bsr": 1234,
                "bsr_category": "Books > Literature & Fiction",
                "availability": "In Stock",
                "discount_percentage": 15.0,
                "author": "F. Scott Fitzgerald",
                "format": "Paperback",
                "publication_date": "2020-01-15",
                "language": "English",
                "scraped_at": "2024-01-15T10:30:00"
            }
        }