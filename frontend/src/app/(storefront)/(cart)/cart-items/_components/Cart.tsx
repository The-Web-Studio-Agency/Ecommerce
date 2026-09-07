'use client';

import Image from 'next/image';
import Link from 'next/link';

import { useCart } from '@/context/CartContext';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatMoney } from '@/lib/format';
import type { CartItem } from '@/types/cart';
import type { CheckoutPreview } from '@/types/orders';

// -----------------------------------
// QUANTITY CONTROL
// -----------------------------------

function QuantityControl({
  quantity,
  disabled,
  onChange,
}: {
  quantity: number;
  disabled: boolean;
  onChange: (quantity: number) => void;
}) {
  return (
    <div className="cart-items-qty">
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange(quantity === 1 ? quantity : quantity - 1)}
        className="cart-items-qty-btn"
        aria-label="Decrease quantity">
        −
      </button>

      <span className="cart-items-qty-value">{quantity}</span>

      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange(quantity + 1)}
        className="cart-items-qty-btn"
        aria-label="Increase quantity">
        +
      </button>
    </div>
  );
}

// -----------------------------------
// LINE
// -----------------------------------

function CartLineItem({
  item,
  disabled,
  onQtyChange,
  onRemove,
}: {
  item: CartItem;
  disabled: boolean;
  onQtyChange: (itemId: string, quantity: number) => void;
  onRemove: (itemId: string) => void;
}) {
  return (
    <div className="cart-items-card">
      <div className="cart-items-card-inner">
        {/* IMAGE */}

        <div className="cart-items-image-wrap">
          {item.image && (
            <Image
              src={item.image.url}
              alt={item.image.alt_text ?? item.product_name}
              className="cart-items-image"
              width={100}
              height={100}
            />
          )}
        </div>

        {/* DETAILS */}

        <div className="cart-items-details">
          <div className="cart-items-details-top">
            <div>
              <h3 className="cart-items-name">
                <Link href={`/single-product/${item.product_id}`}>{item.product_name}</Link>
              </h3>

              <p className="cart-items-variant">{item.variant_name}</p>

              <p className="cart-items-variant">SKU: {item.sku}</p>
            </div>
          </div>

          <div className="cart-items-quantity-details">
            <div className="cart-items-actions">
              <QuantityControl
                quantity={item.quantity}
                disabled={disabled}
                onChange={quantity => onQtyChange(item.id, quantity)}
              />
            </div>
          </div>
        </div>

        {/* PRICE */}

        <div className="cart-items-price-details">
          <div className="cart-items-price-block">
            <div className="cart-items-price">{formatMoney(item.subtotal, STOREFRONT_CURRENCY)}</div>

            {item.quantity > 1 && (
              <div className="cart-items-price-each">
                {formatMoney(item.unit_price, STOREFRONT_CURRENCY)} each
              </div>
            )}
          </div>

          {/* REMOVE */}

          <button
            type="button"
            disabled={disabled}
            onClick={() => onRemove(item.id)}
            className="cart-items-link">
            <Image src="/assets/dustbin.png" alt="remove-button-image" width={20} height={20} />
          </button>
        </div>
      </div>
    </div>
  );
}

// -----------------------------------
// CART
// -----------------------------------

/**
 * The cart page.
 *
 * Line totals and the subtotal are the backend's; shipping and tax only
 * exist once checkout prices them, which needs a session -- so a guest sees
 * the subtotal and is told the rest is worked out at checkout, rather than
 * being shown a guess that changes at the last step.
 */
export default function Cart({ preview }: { preview: CheckoutPreview | null }) {
  const { cart, items, itemCount, pending, error, updateQuantity, removeFromCart } = useCart();

  return (
    <div className="cart-items-page">
      <div className="cart-items-container">
        {/* =================================
            CART LIST
        ================================= */}

        <div className="cart-items-list">
          <h1 className="cart-items-title">
            Your Cart{' '}
            <span className="cart-items-count">
              ({itemCount} {itemCount === 1 ? 'item' : 'items'})
            </span>
          </h1>

          {error && <div className="cart-items-empty">{error}</div>}

          {items.length === 0 ? (
            <div className="cart-items-empty">Your cart is empty.</div>
          ) : (
            items.map(item => (
              <CartLineItem
                key={item.id}
                item={item}
                disabled={pending}
                onQtyChange={updateQuantity}
                onRemove={removeFromCart}
              />
            ))
          )}
        </div>

        {/* =================================
            ORDER SUMMARY
        ================================= */}
        {items.length !== 0 && (
          <div className="cart-items-summary">
            <h2 className="cart-items-summary-title">Order Summary</h2>

            <div className="cart-items-summary-rows">
              {/* SUBTOTAL */}

              <div className="cart-items-summary-row">
                <span>Subtotal ({itemCount} items)</span>

                <span className="cart-items-summary-value">
                  {formatMoney(preview ? preview.subtotal : cart.subtotal, STOREFRONT_CURRENCY)}
                </span>
              </div>

              {/* SHIPPING */}

              <div className="cart-items-summary-row">
                <span>Shipping</span>

                <span className="cart-items-summary-value">
                  {preview ? formatMoney(preview.shipping_amount, STOREFRONT_CURRENCY) : 'At checkout'}
                </span>
              </div>

              {/* TAX */}

              <div className="cart-items-summary-row">
                <span>Tax</span>

                <span className="cart-items-summary-value">
                  {preview ? formatMoney(preview.tax_amount, STOREFRONT_CURRENCY) : 'At checkout'}
                </span>
              </div>
            </div>

            {/* =================================
              TOTAL
              ================================= */}

            <div className="cart-items-total">
              <span className="cart-items-total-label">Total</span>

              <span className="cart-items-total-value">
                {formatMoney(preview ? preview.total_amount : cart.subtotal, STOREFRONT_CURRENCY)}
              </span>
            </div>

            {/* CHECKOUT */}
            <Link href={'/check-out'}>
              <button type="button" className="cart-items-checkout-btn">
                Proceed to Checkout
              </button>
            </Link>

            {/* NOTES */}

            <div className="cart-items-notes">
              <div className="cart-items-note">
                <span>Secure checkout, encrypted payment</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
