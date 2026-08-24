from uuid import UUID
from sqlalchemy import and_,delete,select # type: ignore
from app.catalogue.models import Product,ProductImage,ProductVariant
from app.wishlist.models import Wishlist,WishlistItem
#korachoode kodukkan ond

class WishlistRepository:
        model=Wishlist
        async def get_by_customer(self,customer_id:UUID)->Wishlist|None:
            return await self.find_one(Wishlist.customer_id==customer_id)
        async def create(self,wishlist:Wishlist)->Wishlist:
            self.session.add(wishlist)
            await self.session.flush()
            return wishlist

class WishlistItemRepository:
        model=WishlistItem
        async def get_items(self,wishlist_id:UUID)->list[WishlistItem]:
            return await self.find(WishlistItem.wishlist_id==wishlist_id)       
        async def get(self,wishlist_id:UUID,variant_id:UUID)->WishlistItem|None:
            return await self.find_one(WishlistItem.wishlist_id == wishlist_id, WishlistItem.variant_id == variant_id)
        async def get_by_variant(self,wishlist_id:UUID,variant_id:UUID)->WishlistItem|None:
            return await self.find_one(WishlistItem.wishlist_id==wishlist_id,WishlistItem.variant_id==variant_id)
        async def add_item(self,wishlist_id:UUID,variant_id:UUID)->WishlistItem:
            return await self.add(WishlistItem(wishlist_id=wishlist_id,variant_id=variant_id))
        async def get_item(self,wishlist_id:UUID,item_id:UUID,)->WishlistItem|None:
            return await self.find_one(WishlistItem.wishlist_id==wishlist_id,WishlistItem.id == item_id)
        async def clear(self,wishlist_id:UUID)->int:
            query=delete(WishlistItem).where(WishlistItem.tenant_id == self.tenant_id,WishlistItem.wishlist_id == wishlist_id)
            result=await self.session.execute(query)
            await self.session.flush()
            return result.rowcount or 0
        async def list_with_catalogue(self,wishlist_id:UUID)->list[tuple[WishlistItem,ProductVariant,Product]]:
            stmt=(select(WishlistItem,ProductVariant,Product)
            .join(ProductVariant,and_(ProductVariant.id==WishlistItem.variant_id,ProductVariant.tenant_id == WishlistItem.tenant_id))
            .join(Product,and_(Product.id == ProductVariant.product_id,Product.tenant_id==ProductVariant.tenant_id))
            .where(WishlistItem.tenant_id==self.tenant_id, WishlistItem.wishlist_id == wishlist_id)
            .order_by(WishlistItem.created_at))
            return list((await self.session.execute(stmt)).all())

        async def primary_images(self,product_ids:list[UUID])->dict[UUID, ProductImage]:
            if not product_ids:
                return {}
            rows = await self.session.scalars(select(ProductImage).where(ProductImage.tenant_id == self.tenant_id,ProductImage.product_id.in_(product_ids),ProductImage.is_primary.is_(True)))
            return {image.product_id:image for image in rows.all()}