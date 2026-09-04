'use client';

import { useCart, CartItem } from '@/context/CartContext';
import Image from 'next/image';
import Link from 'next/link';
import { useMemo, useState } from 'react';

type PromoMessage = {
  type: 'success' | 'error';
  text: string;
} | null;

// -----------------------------------
// CURRENCY
// -----------------------------------

function currency(n: number): string {
  return n.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// -----------------------------------
// STOCK BADGE
// -----------------------------------

function StockBadge({ stockCount }: { stockCount: number }) {
  if (stockCount > 10) {
    return (
      <span className="cart-items-badge cart-items-badge--in-stock">
        <svg className="cart-items-badge-icon" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M4 10.5L8 14.5L16 6"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        In Stock
      </span>
    );
  }

  return (
    <span className="cart-items-badge cart-items-badge--low">
      <span className="cart-items-badge-dot" />
      Only {stockCount} left
    </span>
  );
}

// -----------------------------------
// QUANTITY CONTROL
// -----------------------------------

function QuantityControl({
  quantity,
  stockCount,
  onChange,
}: {
  quantity: number;
  stockCount: number;
  onChange: (quantity: number) => void;
}) {
  return (
    <div className="cart-items-qty">
      <button
        type="button"
        onClick={() => onChange(quantity === 1 ? quantity : quantity - 1)}
        className="cart-items-qty-btn"
        aria-label="Decrease quantity">
        −
      </button>

      <span className="cart-items-qty-value">{quantity}</span>

      <button
        type="button"
        onClick={() => onChange(quantity < stockCount ? quantity + 1 : quantity)}
        className="cart-items-qty-btn"
        aria-label="Increase quantity"
        disabled={quantity >= stockCount}>
        +
      </button>
    </div>
  );
}

// -----------------------------------
// CART LINE ITEM
// -----------------------------------

function CartLineItem({
  item,
  onQtyChange,
  onRemove,
}: {
  item: CartItem;

  onQtyChange: (productId: string, color: string, size: string, quantity: number) => void;

  onRemove: (productId: string, color: string, size: string) => void;
}) {
  return (
    <div className="cart-items-card">
      <div className="cart-items-card-inner">
        {/* IMAGE */}

        <div className="cart-items-image-wrap">
          <Image src={item.image} alt={item.name} className="cart-items-image" width={100} height={100} />
        </div>

        {/* DETAILS */}

        <div className="cart-items-details">
          <div className="cart-items-details-top">
            <div>
              <h3 className="cart-items-name">{item.name}</h3>

              <p className="cart-items-variant">
                Color:{' '}
                <span
                  style={{
                    display: 'inline-block',
                    width: '15px',
                    height: '15px',
                    borderRadius: '50%',
                    backgroundColor: item.color,
                    border: '1px solid #ccc',
                    verticalAlign: 'middle',
                    marginLeft: '5px',
                  }}
                />
              </p>

              <p className="cart-items-variant">Size: {item.size}</p>
            </div>
          </div>

          <div className="cart-items-quantity-details">
            <div className="cart-items-badge-row">
              <StockBadge stockCount={item.stockCount} />
            </div>

            <div className="cart-items-actions">
              <QuantityControl
                quantity={item.quantity}
                stockCount={item.stockCount}
                onChange={quantity => onQtyChange(item.productId, item.color, item.size, quantity)}
              />
            </div>
          </div>
        </div>

        {/* PRICE */}

        <div className="cart-items-price-details">
          <div className="cart-items-price-block">
            <div className="cart-items-price">{currency(item.price * item.quantity)}</div>

            {item.quantity > 1 && <div className="cart-items-price-each">{currency(item.price)} each</div>}
          </div>

          {/* REMOVE */}

          <button
            type="button"
            onClick={() => onRemove(item.productId, item.color, item.size)}
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

export default function Cart() {
  const [promo, setPromo] = useState('');

  const [promoMsg, setPromoMsg] = useState<PromoMessage>(null);

  const [discount, setDiscount] = useState(0);

  const { cartItems, updateQuantity, removeFromCart } = useCart();

  // -----------------------------------
  // UPDATE QUANTITY
  // -----------------------------------

  const updateQty = (productId: string, color: string, size: string, quantity: number) => {
    updateQuantity(productId, color, size, quantity);
  };

  // -----------------------------------
  // REMOVE ITEM
  // -----------------------------------

  const removeItem = (productId: string, color: string, size: string) => {
    removeFromCart(productId, color, size);
  };

  // -----------------------------------
  // SUBTOTAL
  // -----------------------------------

  const subtotal = useMemo(() => {
    return cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);
  }, [cartItems]);

  // -----------------------------------
  // ITEM COUNT
  // -----------------------------------

  const itemCount = useMemo(() => {
    return cartItems.reduce((total, item) => total + item.quantity, 0);
  }, [cartItems]);

  // -----------------------------------
  // TAX
  // -----------------------------------

  const tax = useMemo(() => {
    return (subtotal - discount) * 0.065;
  }, [subtotal, discount]);

  // -----------------------------------
  // TOTAL
  // -----------------------------------

  const total = Math.max(0, subtotal - discount) + tax;

  // -----------------------------------
  // PROMO
  // -----------------------------------

  const applyPromo = () => {
    const code = promo.trim().toUpperCase();

    if (!code) return;

    if (code === 'ZEEN10') {
      setDiscount(subtotal * 0.1);

      setPromoMsg({
        type: 'success',
        text: '10% discount applied.',
      });
    } else {
      setDiscount(0);

      setPromoMsg({
        type: 'error',
        text: "That code isn't valid.",
      });
    }
  };

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

          {cartItems.length === 0 ? (
            <div className="cart-items-empty">Your cart is empty.</div>
          ) : (
            cartItems.map(item => (
              <CartLineItem
                key={`${item.productId}-${item.color}-${item.size}`}
                item={item}
                onQtyChange={updateQty}
                onRemove={removeItem}
              />
            ))
          )}
        </div>

        {/* =================================
            ORDER SUMMARY
        ================================= */}

        <div className="cart-items-summary">
          <h2 className="cart-items-summary-title">Order Summary</h2>

          <div className="cart-items-summary-rows">
            {/* SUBTOTAL */}

            <div className="cart-items-summary-row">
              <span>Subtotal ({itemCount} items)</span>

              <span className="cart-items-summary-value">{currency(subtotal)}</span>
            </div>

            {/* DISCOUNT */}

            {discount > 0 && (
              <div className="cart-items-summary-row">
                <span>Discount</span>

                <span className="cart-items-summary-value">−{currency(discount)}</span>
              </div>
            )}

            {/* SHIPPING */}

            <div className="cart-items-summary-row">
              <span>Shipping</span>

              <span className="cart-items-summary-value">Free</span>
            </div>

            {/* TAX */}

            <div className="cart-items-summary-row">
              <span>Estimated Tax</span>

              <span className="cart-items-summary-value">{currency(tax)}</span>
            </div>
          </div>

          {/* =================================
              PROMO
          ================================= */}

          <div className="cart-items-promo">
            <input
              value={promo}
              onChange={e => {
                setPromo(e.target.value);
                setPromoMsg(null);
              }}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  applyPromo();
                }
              }}
              placeholder="Promo code"
              className="cart-items-promo-input"
            />

            <button type="button" onClick={applyPromo} className="cart-items-promo-btn">
              Apply
            </button>
          </div>

          {promoMsg && (
            <p
              className={
                promoMsg.type === 'error'
                  ? 'cart-items-promo-message cart-items-promo-message--error'
                  : 'cart-items-promo-message'
              }>
              {promoMsg.text}
            </p>
          )}

          {/* =================================
              TOTAL
          ================================= */}

          <div className="cart-items-total">
            <span className="cart-items-total-label">Total</span>

            <span className="cart-items-total-value">{currency(total)}</span>
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

            <div className="cart-items-note">
              <span>Free white-glove delivery on this order</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
