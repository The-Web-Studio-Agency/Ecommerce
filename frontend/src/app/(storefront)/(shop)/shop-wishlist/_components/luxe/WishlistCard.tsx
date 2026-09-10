'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { toast } from 'react-toastify';

import { CloseIcon, StarIcon } from '@/app/(storefront)/(home)/home/_components/luxe/Icons';
// Reused wholesale from the Product Listing page: card media box, image
// crop/position, the circular icon button, product name and price styles
// are identical here, so nothing about them is redefined.
import listingStyles from '@/app/(storefront)/(shop)/shop-list/_components/luxe/Listing.module.css';
import { useCart } from '@/context/CartContext';
import { useWishlist } from '@/context/WishlistContext';
import { reviewApi } from '@/lib/api/reviews';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatMoney } from '@/lib/format';
import type { RatingSummary } from '@/types/reviews';
import type { WishlistItem } from '@/types/cart';

import wishlistStyles from './Wishlist.module.css';

interface Props {
  item: WishlistItem;
}

/**
 * A saved item, styled to match a Product Listing card (same media box,
 * name/price) plus a star rating and a single "Add to Bag" action.
 *
 * The rating is real: `reviewApi.summary` is a public, per-product endpoint,
 * fetched client-side per card since the wishlist itself is client state.
 * A product with no reviews yet shows no rating row at all, rather than a
 * fabricated number.
 */
export default function WishlistCard({ item }: Props) {
  const { removeItem, pending: wishlistPending } = useWishlist();
  const { addToCart, pending: cartPending } = useCart();
  const [rating, setRating] = useState<RatingSummary | null>(null);

  useEffect(() => {
    let cancelled = false;

    reviewApi
      .summary(item.product_id)
      .then(summary => {
        if (!cancelled) setRating(summary);
      })
      .catch(() => {
        if (!cancelled) setRating(null);
      });

    return () => {
      cancelled = true;
    };
  }, [item.product_id]);

  const href = `/single-product/${item.product_id}`;

  async function handleRemove() {
    const error = await removeItem(item.id);
    if (error) toast.error(error);
    else toast.info('Removed from your wishlist');
  }

  async function handleAddToBag() {
    await addToCart(item.variant_id, 1);
    toast.success('Added to your bag');
  }

  return (
    <div className={wishlistStyles.card}>
      <div className={listingStyles.cardMediaWrap}>
        <Link href={href} className={listingStyles.cardMediaLink} aria-label={item.product_name}>
          <div className={`${listingStyles.cardMedia} ${wishlistStyles.media}`}>
            {item.image ? (
              <Image
                src={item.image.url}
                alt={item.image.alt_text ?? item.product_name}
                fill
                sizes="(max-width: 1023px) 50vw, (max-width: 1439px) 33vw, 25vw"
                className={listingStyles.cardImg}
              />
            ) : (
              <div className={listingStyles.mediaEmpty}>No image yet</div>
            )}
          </div>
        </Link>

        <button
          type="button"
          className={listingStyles.wishlistBtn}
          onClick={() => {
            if (!wishlistPending) handleRemove();
          }}
          disabled={wishlistPending}
          aria-label="Remove from wishlist">
          <CloseIcon size={14} />
        </button>
      </div>

      <Link href={href} className={wishlistStyles.cardBody}>
        <p className={listingStyles.name}>{item.product_name}</p>
        <p className={listingStyles.price}>{formatMoney(String(item.unit_price), STOREFRONT_CURRENCY)}</p>
      </Link>

      {rating && rating.total_reviews > 0 && (
        <p className={wishlistStyles.rating}>
          <StarIcon size={13} />
          {rating.average_rating.toFixed(1)}
          <span className={wishlistStyles.ratingCount}>({rating.total_reviews})</span>
        </p>
      )}

      <button type="button" className={wishlistStyles.addToBagBtn} onClick={handleAddToBag} disabled={cartPending}>
        {cartPending ? 'Adding…' : 'Add to Bag'}
      </button>
    </div>
  );
}
