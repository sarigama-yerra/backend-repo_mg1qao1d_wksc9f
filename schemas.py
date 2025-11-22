"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class Image(BaseModel):
    url: str
    alt: Optional[str] = None


class Variant(BaseModel):
    sku: str
    thickness_mm: int = Field(..., description="Thickness in millimeters")
    size: str = Field(..., description="Size label, e.g., 1m x 1m")
    color: str
    price: float = Field(..., ge=0)
    stock: int = Field(..., ge=0)


class FAQItem(BaseModel):
    question: str
    answer: str


class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str
    slug: str = Field(..., description="URL-friendly identifier")
    subtitle: Optional[str] = None
    description: Optional[str] = None
    base_price: float = Field(..., ge=0, description="Reference price")
    category: str = "Gym Mats"
    images: List[Image] = []
    variants: List[Variant] = []
    specs: Dict[str, str] = {}
    uvps: List[str] = []  # Unique value propositions
    faqs: List[FAQItem] = []
    rating: Optional[float] = Field(4.9, ge=0, le=5)
    reviews_count: Optional[int] = 0
    in_stock: bool = True


class CartItem(BaseModel):
    product_slug: str
    sku: str
    quantity: int = Field(1, ge=1)
    price: float
    title: str
    image: Optional[str] = None
    selected_options: Dict[str, str] = {}


class Cart(BaseModel):
    cart_id: str
    items: List[CartItem] = []
    currency: str = "USD"
