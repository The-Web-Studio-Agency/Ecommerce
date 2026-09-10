'use client';

import Image from 'next/image';
import { useState } from 'react';

import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatMoney } from '@/lib/format';
import type { CartItem } from '@/types/cart';
import type { CheckoutPreview } from '@/types/orders';

import styles from './Checkout.module.css';

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
      <path d="M5 12.5 10 17 19 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M5 5l14 14M19 5 5 19" strokeLinecap="round" />
    </svg>
  );
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      style={{ transform: open ? 'rotate(180deg)' : undefined, transition: 'transform 0.15s ease' }}>
      <path d="m6 9 6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" strokeLinecap="round" />
    </svg>
  );
}

function TruckIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M2 6h11v10H2z" strokeLinejoin="round" />
      <path d="M13 10h4l4 3.5V16h-8z" strokeLinejoin="round" />
      <circle cx="6" cy="18" r="1.8" />
      <circle cx="16.5" cy="18" r="1.8" />
    </svg>
  );
}

function ReturnIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 9V4M4 9h5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4 9a8 8 0 1 1 2 6.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3Z" strokeLinejoin="round" />
      <path d="m9 12 2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SupportIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 13v-1a8 8 0 0 1 16 0v1" strokeLinecap="round" />
      <rect x="2.5" y="13" width="5" height="6" rx="1.5" />
      <rect x="16.5" y="13" width="5" height="6" rx="1.5" />
    </svg>
  );
}

/**
 * Items + coupon + totals + trust badges + Place Order, all in one panel.
 *
 * The reference stacks this as a single mobile column (with its own numbered
 * "4"/"5" headings) and as a sticky sidebar on desktop (numbers gone, coupon
 * nested under a collapsible toggle, a trust-badges card added). Rather than
 * two components, this renders once and lets `Checkout.module.css` show the
 * right pieces per breakpoint -- see the CSS file's comments.
 */
export default function OrderSummaryPanel({
  cartItems,
  preview,
  couponInput,
  onCouponInputChange,
  onApplyCoupon,
  onRemoveCoupon,
  couponPending,
  couponError,
  canPlaceOrder,
  placeOrderPending,
  placeOrderError,
}: {
  cartItems: CartItem[];
  preview: CheckoutPreview | null;
  couponInput: string;
  onCouponInputChange: (value: string) => void;
  onApplyCoupon: () => void;
  onRemoveCoupon: () => void;
  couponPending: boolean;
  couponError: string | null;
  canPlaceOrder: boolean;
  placeOrderPending: boolean;
  placeOrderError: string | null;
}) {
  const [couponOpen, setCouponOpen] = useState(true);

  const appliedCode = preview?.coupon_code ?? null;
  const discount = preview ? Number(preview.discount_amount) : 0;
  const shippingAmount = preview ? Number(preview.shipping_amount) : 0;

  return (
    <>
      <div className={styles.summaryCard}>
        <div className={styles.summaryHeader}>
          <p className={styles.summaryTitle}>
            <span className={`${styles.stepNumber} ${styles.stepNumberMobileOnly}`}>5</span>
            Order Summary
          </p>
          <span className={styles.itemCount}>
            {cartItems.length} {cartItems.length === 1 ? 'item' : 'items'}
          </span>
        </div>

        <div className={styles.summaryItems}>
          {cartItems.map(item => (
            <div key={item.id} className={styles.summaryItem}>
              <div className={styles.summaryThumb}>
                {item.image && (
                  <Image src={item.image.url} alt={item.image.alt_text ?? item.product_name} fill sizes="52px" />
                )}
              </div>
              <div className={styles.summaryItemBody}>
                <p className={styles.summaryItemName}>{item.product_name}</p>
                <p className={styles.summaryItemMeta}>
                  {item.variant_name} &nbsp;|&nbsp; Qty: {item.quantity}
                </p>
              </div>
              <span className={styles.summaryItemPrice}>{formatMoney(item.subtotal, STOREFRONT_CURRENCY)}</span>
            </div>
          ))}
        </div>

        <div className={styles.couponSection}>
          <div className={styles.couponMobileHeader}>
            <span className={styles.stepNumber}>4</span>
            <p className={styles.sectionTitle}>Apply Coupon</p>
          </div>

          <button
            type="button"
            className={styles.couponDesktopToggle}
            onClick={() => setCouponOpen(open => !open)}>
            Have a coupon code?
            <ChevronIcon open={couponOpen} />
          </button>

          {couponOpen && !appliedCode && (
            <div className={styles.couponForm}>
              <input
                type="text"
                placeholder="Enter coupon code"
                className={styles.couponInput}
                value={couponInput}
                disabled={couponPending}
                onChange={event => onCouponInputChange(event.target.value.toUpperCase())}
              />
              <button
                type="button"
                className={styles.couponApplyBtn}
                disabled={couponPending || !couponInput.trim()}
                onClick={onApplyCoupon}>
                {couponPending ? 'Checking…' : 'Apply'}
              </button>
            </div>
          )}

          {couponError && <p className={styles.couponError}>{couponError}</p>}

          {appliedCode && (
            <div className={styles.couponApplied}>
              <span className={styles.couponAppliedIcon}>
                <CheckIcon />
              </span>
              <div className={styles.couponAppliedText}>
                <strong>{appliedCode} applied!</strong>
                <span>You saved {formatMoney(preview?.discount_amount, STOREFRONT_CURRENCY)} on this order.</span>
              </div>
              <button type="button" className={styles.couponRemoveBtn} onClick={onRemoveCoupon} aria-label="Remove coupon">
                <CloseIcon />
              </button>
            </div>
          )}
        </div>

        <div className={styles.summaryTotals}>
          <div className={styles.summaryRow}>
            <span>Subtotal</span>
            <span>{formatMoney(preview?.subtotal, STOREFRONT_CURRENCY)}</span>
          </div>

          {appliedCode && discount > 0 && (
            <div className={styles.summaryRow}>
              <span>Discount ({appliedCode})</span>
              <span className={styles.discountValue}>− {formatMoney(preview?.discount_amount, STOREFRONT_CURRENCY)}</span>
            </div>
          )}

          <div className={styles.summaryRow}>
            <span>Shipping</span>
            <span>{shippingAmount > 0 ? formatMoney(preview?.shipping_amount, STOREFRONT_CURRENCY) : 'Free'}</span>
          </div>

          <div className={styles.summaryRow}>
            <span>Estimated Tax</span>
            <span>{formatMoney(preview?.tax_amount, STOREFRONT_CURRENCY)}</span>
          </div>
        </div>

        <div className={styles.summaryTotalRow}>
          <span>Total</span>
          <span>{formatMoney(preview?.total_amount, STOREFRONT_CURRENCY)}</span>
        </div>
      </div>

      <div className={styles.trustPanel}>
        <div className={styles.trustItem}>
          <span className={styles.trustIcon}>
            <TruckIcon />
          </span>
          <div>
            <p className={styles.trustTitle}>Free Shipping</p>
            <p className={styles.trustDesc}>On eligible orders</p>
          </div>
        </div>
        <div className={styles.trustItem}>
          <span className={styles.trustIcon}>
            <ReturnIcon />
          </span>
          <div>
            <p className={styles.trustTitle}>Easy Returns</p>
            <p className={styles.trustDesc}>30-day return policy</p>
          </div>
        </div>
        <div className={styles.trustItem}>
          <span className={styles.trustIcon}>
            <ShieldIcon />
          </span>
          <div>
            <p className={styles.trustTitle}>Secure Payment</p>
            <p className={styles.trustDesc}>Your data is protected</p>
          </div>
        </div>
        <div className={styles.trustItem}>
          <span className={styles.trustIcon}>
            <SupportIcon />
          </span>
          <div>
            <p className={styles.trustTitle}>Customer Support</p>
            <p className={styles.trustDesc}>Available 24/7</p>
          </div>
        </div>
      </div>

      <button type="submit" className={styles.placeOrderBtn} disabled={!canPlaceOrder || placeOrderPending}>
        {placeOrderPending ? 'Placing order…' : 'Place Order'}
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M4 12h16M13 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {placeOrderError && <p className={styles.couponError}>{placeOrderError}</p>}

      <p className={styles.secureNote}>
        <LockIcon />
        Your payment information is secure and encrypted.
      </p>
    </>
  );
}
