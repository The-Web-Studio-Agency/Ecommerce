'use client';

import Image from 'next/image';
import Link from 'next/link';
import { toast } from 'react-toastify';

import { BagIcon, HeartIcon } from '@/app/(storefront)/(home)/home/_components/luxe/Icons';
// Reused wholesale from the Product Listing page: card media box, image
// crop/position, the wishlist heart button, product name and price styles
// are identical here, so nothing about them is redefined.
import listingStyles from '@/app/(storefront)/(shop)/shop-list/_components/luxe/Listing.module.css';
import { useCart } from '@/context/CartContext';
import { useWishlist } from '@/context/WishlistContext';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatMoney } from '@/lib/format';
import type { WishlistItem } from '@/types/cart';

import wishlistStyles from './Wishlist.module.css';

interface Props {
  item: WishlistItem;
}

/**
 * A saved item, styled to match a Product Listing card (same media box,
 * heart, name/price) with the two actions a wishlist row actually needs:
 * Add to Cart and Remove. The heart doubles as a quick remove too, same
 * toggle semantics as the listing card -- every item here is already
 * saved, so there's nothing for it to do but unsave.
 *
 * `variant_name` (e.g. "Black / M") is the real, already-chosen variant --
 * there is no separate colour swatch in the wishlist API to render, so it's
 * shown as plain text rather than inventing one.
 */
export default function WishlistCard({ item }: Props) {
  const { removeItem, pending: wishlistPending } = useWishlist();
  const { addToCart, pending: cartPending } = useCart();

  const href = `/single-product/${item.product_id}`;

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
    <div className={wishlistStyles.card}>
      <div className={listingStyles.cardMediaWrap}>
        <Link href={href} className={listingStyles.cardMediaLink} aria-label={item.product_name}>
          <div className={listingStyles.cardMedia}>
            {item.image ? (
              <Image
                src={item.image.url}
                alt={item.image.alt_text ?? item.product_name}
                fill
                sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
                className={listingStyles.cardImg}
              />
            ) : (
              <div className={listingStyles.mediaEmpty}>No image yet</div>
            )}
          </div>
        </Link>

        <button
          type="button"
          className={`${listingStyles.wishlistBtn} ${listingStyles.wishlistBtnActive}`}
          onClick={() => {
            if (!wishlistPending) handleRemove();
          }}
          disabled={wishlistPending}
          aria-pressed="true"
          aria-label="Remove from wishlist"
        >
          <HeartIcon size={16} filled />
        </button>
      </div>

      <Link href={href} className={wishlistStyles.cardBody}>
        <p className={listingStyles.name}>{item.product_name}</p>
        <p className={wishlistStyles.variant}>{item.variant_name}</p>
        <p className={listingStyles.price}>{formatMoney(String(item.unit_price), STOREFRONT_CURRENCY)}</p>
      </Link>

      <div className={wishlistStyles.actions}>
        <button
          type="button"
          className={wishlistStyles.primaryBtn}
          onClick={handleAddToCart}
          disabled={cartPending}
        >
          <BagIcon size={14} />
          {cartPending ? 'Adding…' : 'Add to Cart'}
        </button>
        <button
          type="button"
          className={wishlistStyles.secondaryBtn}
          onClick={handleRemove}
          disabled={wishlistPending}
        >
          Remove
        </button>
      </div>
    </div>
  );
}
