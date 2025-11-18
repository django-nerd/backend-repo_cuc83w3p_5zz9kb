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
from typing import Optional, List, Dict, Any

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# SneakPeak specific schemas

class Design(BaseModel):
    """Saved sneaker custom designs
    Collection name: "design"
    """
    user_id: Optional[str] = Field(None, description="User identifier (from Supabase or app)")
    sneaker_id: str = Field(..., description="ID of the base sneaker")
    name: str = Field(..., description="User-friendly name for the design")
    layers: Dict[str, Any] = Field(default_factory=dict, description="Keyed color/material selections per part")
    preview_url: Optional[str] = Field(None, description="Optional preview image URL")
    is_public: bool = Field(False, description="Whether this design is public")

class Alert(BaseModel):
    """Price/stock alert subscriptions
    Collection name: "alert"
    """
    user_id: Optional[str] = Field(None, description="User identifier")
    sneaker_id: str = Field(..., description="ID of the sneaker this alert is for")
    type: str = Field(..., description="'price_drop' | 'restock'")
    threshold_price: Optional[float] = Field(None, ge=0, description="Notify when price <= this value")
    email: Optional[str] = Field(None, description="Email for notifications")

# Add your own schemas here:
# --------------------------------------------------

# Note: The Flames database viewer will automatically:
# 1. Read these schemas from GET /schema endpoint
# 2. Use them for document validation when creating/editing
# 3. Handle all database operations (CRUD) directly
# 4. You don't need to create any database endpoints!
