'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { toast } from 'react-toastify';

import { useWishlist } from '@/context/WishlistContext';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatPriceRange } from '@/lib/format';
import type { ProductSummaryStorefront } from '@/types/catalogue';

interface ProductCardProps {
  product: ProductSummaryStorefront;
  rating?: number;
}

/**
 * A catalogue tile.
 *
 * The listing endpoint returns no variants, so there is nothing here to put
 * in a cart -- "Add to Cart" opens the product instead, where options are
 * chosen and a real variant id exists. Adding a guessed variant would be
 * the wrong item as often as the right one.
 */
export default function ProductCard({ product, rating = 0 }: ProductCardProps) {
  const router = useRouter();
  const { isProductSaved, toggleProduct, pending } = useWishlist();

  const href = `/single-product/${product.id}`;
  const image = product.primary_image;
  const saved = isProductSaved(product.id);

  async function handleToggleWishlist(event: React.MouseEvent) {
    event.preventDefault();
    if (pending) return;

    const wasSaved = saved;
    const error = await toggleProduct(product.id);

    if (error) toast.error(error);
    else if (wasSaved) toast.info('Removed from your wishlist');
    else toast.success('Saved to your wishlist');
  }

  return (
    <div className="product-card">
      {/* Wishlist */}
      <div className={`btn-wishlist ${saved ? 'active' : ''}`} onClick={handleToggleWishlist}>
        {saved ? (
          <i className="icon heart-icon feather icon-heart-on dz-heart-fill" />
        ) : (
          <i className="icon heart-icon feather icon-heart dz-heart" />
        )}
      </div>

      {/* Product Image */}
      <Link href={href}>
        <div className="product-media">
          {!product.in_stock && (
            <div className="discount-tag">
              <span>Sold out</span>
            </div>
          )}

          {/* Image */}
          <div className="product-img-container">
            {image && (
              <Image
                width={500}
                height={700}
                src={image.url}
                alt={image.alt_text ?? product.name}
                className="product-img"
              />
            )}
          </div>

          {/* View Product */}
          <div className="product-overlay">
            <button type="button" className="btn-view-product">
              View Product
            </button>
          </div>
        </div>
      </Link>

      {/* Product Information */}
      <div className="product-body">
        {/* Product Name */}
        <p className="product-name-text">{product.name}</p>

        {/* Price */}
        <div className="product-price-list">
          <p className="product-price-text">
            {formatPriceRange(product.price_from, product.price_to, STOREFRONT_CURRENCY)}
          </p>
        </div>

        {/* Rating + Cart */}
        <div className="product-footer">
          {/* Rating */}
          <div className="rating">
            {Array.from({ length: 5 }).map((_, index) => {
              if (index < Math.floor(rating)) {
                return <i key={index} className="fa-solid fa-star filled" />;
              }

              if (index < rating) {
                return <i key={index} className="fa-solid fa-star-half-stroke filled" />;
              }

              return <i key={index} className="fa-regular fa-star" />;
            })}
          </div>

          {/* Add To Cart */}
          <button type="button" className="btn-add-cart" onClick={() => router.push(href)}>
            {product.in_stock ? 'Add to Cart' : 'View'}
            <span className="plus-icon">+</span>
          </button>
        </div>
      </div>
    </div>
  );
}
