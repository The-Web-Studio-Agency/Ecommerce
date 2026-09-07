'use client';

import Image from 'next/image';
import { useMemo, useState } from 'react';

import ProductCard from '../Shop/ProductCard';
import { useCart } from '@/context/CartContext';
import { useWishlist } from '@/context/WishlistContext';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatMoney } from '@/lib/format';
import type { ProductStorefront, ProductSummaryStorefront, VariantStorefront } from '@/types/catalogue';

type Props = {
  product: ProductStorefront;
  rating: number;
  related: ProductSummaryStorefront[];
};

/** Option values the shopper has picked, keyed by option name. */
type Selection = Record<string, string>;

/**
 * Start on the first in-stock variant, falling back to the first of any.
 *
 * Landing on a sold-out combination when a sellable one exists would read
 * as the whole product being unavailable.
 */
function initialSelection(product: ProductStorefront): Selection {
  const variant = product.variants.find(entry => entry.in_stock) ?? product.variants[0];
  return variant ? { ...variant.options } : {};
}

function findVariant(product: ProductStorefront, selection: Selection): VariantStorefront | null {
  const names = product.options.map(option => option.name);

  return (
    product.variants.find(variant => names.every(name => variant.options[name] === selection[name])) ??
    null
  );
}

/**
 * Whether a value can be painted as a swatch.
 *
 * Option values are free text on the backend -- "Black" is a CSS colour but
 * "Sand Dune" is not, and a chip with an unpaintable value would render as
 * an invisible blank, so those fall back to showing the name.
 */
function isPaintable(value: string): boolean {
  if (typeof CSS === 'undefined' || !CSS.supports) return false;
  return CSS.supports('color', value.replace(/\s+/g, ''));
}

const SingleProduct = ({ product, rating, related }: Props) => {
  const [selectedImage, setSelectedImage] = useState(0);
  const [selection, setSelection] = useState<Selection>(() => initialSelection(product));
  const [quantity, setQuantity] = useState(1);
  const [message, setMessage] = useState<string | null>(null);

  const { addToCart, pending } = useCart();
  const { isVariantSaved, toggleVariant, pending: wishlistPending } = useWishlist();

  const variant = useMemo(() => findVariant(product, selection), [product, selection]);
  const saved = variant ? isVariantSaved(variant.id) : false;

  const images = product.images.length > 0 ? product.images : null;
  const stockCount = variant ? variant.available_quantity : 0;
  const price = variant ? variant.price : product.price_from;

  const colorOption = product.options.find(option => option.name.toLowerCase() === 'color');
  const sizeOption = product.options.find(option => option.name.toLowerCase() === 'size');
  const otherOptions = product.options.filter(
    option => option !== colorOption && option !== sizeOption,
  );

  function choose(name: string, value: string) {
    setSelection(previous => ({ ...previous, [name]: value }));
    setQuantity(1);
    setMessage(null);
  }

  async function handleAddToCart() {
    if (!variant) {
      setMessage('That combination is not available.');
      return;
    }

    await addToCart(variant.id, quantity);
    setMessage('Added to your cart');
  }

  async function handleToggleWishlist() {
    if (!variant) return;

    const wasSaved = saved;
    const error = await toggleVariant(variant.id);

    setMessage(error ?? (wasSaved ? 'Removed from your wishlist' : 'Saved to your wishlist'));
  }

  return (
    <section className="wrapper">
      {/* Single Product */}
      <div className="single-product-container">
        {/* Images */}
        <div className="single-product-image-section">
          {images && (
            <div className="product-thumbnail-gallery">
              {images.map((item, index) => (
                <div
                  key={item.id}
                  className={`${
                    selectedImage === index ? 'selected-product-thumdbnail' : 'unselected-products-thumbnail'
                  } product-thumbnail`}>
                  <Image
                    src={item.url}
                    alt={item.alt_text ?? product.name}
                    width={200}
                    height={200}
                    onClick={() => setSelectedImage(index)}
                  />
                </div>
              ))}
            </div>
          )}

          {images && (
            <div className="product-main-image">
              <Image
                src={images[selectedImage].url}
                alt={images[selectedImage].alt_text ?? product.name}
                width={1000}
                height={1000}
              />
            </div>
          )}
        </div>

        {/* Details */}
        <div className="single-product-details-section">
          {/* Name + Price */}
          <div className="product-name-price">
            <p className="product-type">{product.category.name}</p>

            <p className="product-name">{product.name}</p>

            <div className="product-price">
              <span>{formatMoney(price, STOREFRONT_CURRENCY)}</span>
            </div>
          </div>

          {/* Colors */}
          {colorOption && (
            <div className="product-colors-container">
              <p>Colors :</p>

              {colorOption.values.map(value => {
                const active = selection[colorOption.name] === value;

                return isPaintable(value) ? (
                  <p
                    key={value}
                    title={value}
                    onClick={() => choose(colorOption.name, value)}
                    className={`product-color ${active ? 'active' : ''}`}
                    style={{ backgroundColor: value.replace(/\s+/g, '') }}
                  />
                ) : (
                  <p
                    key={value}
                    onClick={() => choose(colorOption.name, value)}
                    className={`product-size ${active ? 'active' : ''}`}>
                    {value}
                  </p>
                );
              })}
            </div>
          )}

          {/* Sizes */}
          {sizeOption && (
            <div className="product-size-container">
              <p>Sizes :</p>

              {sizeOption.values.map(value => (
                <p
                  key={value}
                  onClick={() => choose(sizeOption.name, value)}
                  className={`product-size ${selection[sizeOption.name] === value ? 'active' : ''}`}>
                  {value}
                </p>
              ))}
            </div>
          )}

          {otherOptions.map(option => (
            <div className="product-size-container" key={option.name}>
              <p>{option.name} :</p>

              {option.values.map(value => (
                <p
                  key={value}
                  onClick={() => choose(option.name, value)}
                  className={`product-size ${selection[option.name] === value ? 'active' : ''}`}>
                  {value}
                </p>
              ))}
            </div>
          ))}

          <div className="single-product-rating">
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

          {/* Quantity + Cart */}
          <div className="product-quantity-cart-container">
            <div className="product-quantity-container">
              <p>Quantity</p>

              <div className="quantity-button">
                <button onClick={() => setQuantity(prev => (prev <= 1 ? prev : prev - 1))}>-</button>

                <p>{quantity}</p>

                <button onClick={() => setQuantity(prev => (prev < stockCount ? prev + 1 : prev))}>+</button>
              </div>
            </div>

            <button
              onClick={handleAddToCart}
              disabled={pending || stockCount === 0}
              className="add-to-cart-btn">
              {stockCount === 0 ? 'OUT OF STOCK' : pending ? 'ADDING...' : 'ADD TO CART'}
            </button>

            <button
              type="button"
              onClick={handleToggleWishlist}
              disabled={wishlistPending || !variant}
              aria-label={saved ? 'Remove from wishlist' : 'Save to wishlist'}
              title={saved ? 'Remove from wishlist' : 'Save to wishlist'}
              style={{
                width: 48,
                height: 48,
                borderRadius: '50%',
                border: '1px solid #e2e2e2',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: '#fff',
                color: saved ? '#cc0d39' : '#333',
                cursor: wishlistPending || !variant ? 'default' : 'pointer',
                flexShrink: 0,
                marginLeft: 12,
              }}>
              <i
                className={`heart-icon feather ${saved ? 'icon-heart-on dz-heart-fill' : 'icon-heart dz-heart'}`}
              />
            </button>
          </div>

          {message && <p className="product-cart-message">{message}</p>}

          {/* Description */}
          <div className="product-description-container">
            <p className="description-heading">DESCRIPTION</p>

            <p>{product.description ?? product.short_description ?? ''}</p>
          </div>
        </div>
      </div>

      {/* Similar Products */}
      {related.length > 0 && (
        <div className="similiar-products-section">
          <p className="similiar-products-heading">YOU MIGHT ALSO LIKE</p>

          <div className="row gx-xl-4 g-3 mt-5 mb-5">
            {related.map(item => (
              <div className="col-12 col-sm-6 col-md-4 col-lg-4 col-xl-4" key={item.id}>
                <ProductCard product={item} />
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
};

export default SingleProduct;
