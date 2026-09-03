from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class VariantAttributes(BaseModel):
    """One variant's actual option values, e.g. {"Color": "Black", "Size": "S"}.

    Straight off that variant's ProductVariantOption rows -- never inferred
    from the product's name, images, or any other unrelated field.
    """

    variant_id: uuid.UUID
    options: Dict[str, str] = Field(default_factory=dict)

    class Config:
        from_attributes = True

class ProductDiscoveryItem(BaseModel):
    id: uuid.UUID
    name: str
    brand: Optional[str] = None
    category_id: uuid.UUID
    price: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    rating: Optional[float] = None
    variants: List[VariantAttributes] = Field(default_factory=list)

    class Config:
        from_attributes = True

class PaginatedDiscoveryResponse(BaseModel):
    items: List[ProductDiscoveryItem]
    total: int
    page: int
    size: int
    pages: int

class SuggestionItem(BaseModel):
    title: str

class SearchSuggestionsResponse(BaseModel):
    suggestions: List[str]

class SearchHistoryItem(BaseModel):
    id: uuid.UUID
    query: str
    created_at: str

    class Config:
        from_attributes = True

class SearchHistoryResponse(BaseModel):
    history: List[str]