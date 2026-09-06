'use client';

import Link from 'next/link';
import Image, { StaticImageData } from 'next/image';
import { useState } from 'react';
import { useCart } from '@/context/CartContext';

interface ProductCardProps {
  productId: string;
  image: StaticImageData | string;
  title: string;
  price: number;
  oldPrice?: number;
  discount?: number;
  colors: string[];
  sizes: string[];
  rating: number;
  stockCount: number;
}

export default function ProductCard({
  productId,
  image,
  title,
  price,
  oldPrice,
  discount,
  colors,
  sizes,
  rating,
  stockCount,
}: ProductCardProps) {
  const [heartIcon, setHeartIcon] = useState(false);

  const { addToCart } = useCart();

  const handleAddToCart = () => {
    addToCart({
      productId,
      name: title,
      image: typeof image === 'string' ? image : image.src,
      price,
      rating,
      stockCount,
      color: colors[0],
      size: sizes[0],
      quantity: 1,
    });
  };

  return (
    <div className="product-card">
      {/* Wishlist */}
      <div className={`btn-wishlist ${heartIcon ? 'active' : ''}`} onClick={() => setHeartIcon(!heartIcon)}>
        {heartIcon ? (
          <i className="icon heart-icon feather icon-heart-on dz-heart-fill" />
        ) : (
          <i className="icon heart-icon feather icon-heart dz-heart" />
        )}
      </div>

      {/* Product Image */}
      <Link href={`/single-product/${productId}`}>
        <div className="product-media">
          {/* Discount */}
          {discount && (
            <div className="discount-tag">
              <span>{discount}% Off</span>
            </div>
          )}

          {/* Image */}
          <div className="product-img-container">
            <Image width={500} height={700} src={image} alt={title} className="product-img" />
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
        <p className="product-name-text">{title}</p>

        {/* Price */}
        <div className="product-price-list">
          <p className="product-price-text">${price.toFixed(2)}</p>

          {oldPrice && <p className="product-old-price-text">${oldPrice.toFixed(2)}</p>}
        </div>

        {/* Colors */}
        {colors.length > 0 && (
          <div className="swatches">
            {colors.map((color, index) => (
              <span key={index} className="swatch" style={{ background: color }} />
            ))}
          </div>
        )}

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
          <button type="button" className="btn-add-cart" onClick={handleAddToCart}>
            Add to Cart
            <span className="plus-icon">+</span>
          </button>
        </div>
      </div>
    </div>
  );
}
