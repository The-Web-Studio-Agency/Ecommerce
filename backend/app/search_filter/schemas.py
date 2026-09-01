from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field

class ProductDiscoveryItem(BaseModel):
    id: uuid.UUID
    name: str
    brand: Optional[str] = None
    gender: Optional[str] = None
    category_id: uuid.UUID
    price: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None

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