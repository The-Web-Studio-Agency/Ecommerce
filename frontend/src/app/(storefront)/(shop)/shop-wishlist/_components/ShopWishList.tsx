'use client';

import Image from 'next/image';
import Link from 'next/link';
import { toast } from 'react-toastify';

import CommanBanner from '@/components/CommanBanner';
import IMAGES from '@/constant/theme';
import { useCart } from '@/context/CartContext';
import { useWishlist } from '@/context/WishlistContext';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatMoney } from '@/lib/format';
import type { WishlistItem } from '@/types/cart';

function WishlistRow({ item }: { item: WishlistItem }) {
  const { removeItem, pending: wishlistPending } = useWishlist();
  const { addToCart, pending: cartPending } = useCart();

  async function handleRemove() {
    const error = await removeItem(item.id);
    if (error) toast.error(error);
    else toast.info('Removed from your wishlist');
  }

  async function handleAddToCart() {
    await addToCart(item.variant_id, 1);
    toast.success('Added to your cart');
  }

  return (
    <tr>
      <td className="product-item-img">
        {item.image && <Image src={item.image.url} alt={item.image.alt_text ?? item.product_name} width={80} height={100} />}
      </td>
      <td className="product-item-name">
        <Link href={`/single-product/${item.product_id}`}>{item.product_name}</Link>
        <div>{item.variant_name}</div>
      </td>
      <td className="product-item-price">
        <span>{formatMoney(String(item.unit_price), STOREFRONT_CURRENCY)}</span>
      </td>
      <td className="product-item-stock">In Stock</td>
      <td className="product-item-totle">
        <button
          type="button"
          onClick={handleAddToCart}
          disabled={cartPending}
          className="btn btn-secondary btnhover text-nowrap">
          {cartPending ? 'Adding...' : 'Add To Cart'}
        </button>
      </td>
      <td className="product-item-close">
        <Link href="#" onClick={event => { event.preventDefault(); if (!wishlistPending) handleRemove(); }}>
          <i className="ti-close" />
        </Link>
      </td>
    </tr>
  );
}

export default function ShopWishList() {
  const { wishlist } = useWishlist();

  return (
    <div className="page-content bg-light">
      <CommanBanner parentText="Home" currentText="Wishlist" mainText="Wishlist" image={IMAGES.BackBg1.src} />
      <div className="content-inner-1">
        <div className="container">
          <div className="row justify-content-center">
            <div className="col-lg-9">
              {wishlist.items.length === 0 ? (
                <div className="text-center py-5">
                  <p className="mb-4">Your wishlist is empty.</p>
                  <Link href="/shop-standard" className="btn btn-secondary btnhover">
                    Continue Shopping
                  </Link>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table check-tbl style-1">
                    <thead>
                      <tr>
                        <th>Product</th>
                        <th></th>
                        <th>Price</th>
                        <th>Stock</th>
                        <th></th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {wishlist.items.map(item => (
                        <WishlistRow key={item.id} item={item} />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
