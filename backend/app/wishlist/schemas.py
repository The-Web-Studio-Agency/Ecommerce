from uuid import UUID
from pydantic import BaseModel
class WishlistItemImage(BaseModel):
    url:str
    alt_text:str|None=None


class WishListItemCreate(BaseModel):
    variant_id:UUID
    
class WishListItemRead(BaseModel):
    id:UUID
    variant_id:UUID
    product_id:UUID
    product_name:str
    variant_name:str
    sku:str
    unit_price:float
    image:WishlistItemImage|None=None

class WishListRead(BaseModel):
    id:UUID
    items:list[WishListItemRead]=[]
    item_count:int=0