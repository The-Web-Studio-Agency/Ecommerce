'use client';

import Image from 'next/image';
import Link from 'next/link';
import { toast } from 'react-toastify';

import MobileBottomNav from '@/components/MobileBottomNav';
import { useCart } from '@/context/CartContext';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatMoney } from '@/lib/format';
import type { CartItem } from '@/types/cart';
import type { CheckoutPreview } from '@/types/orders';

import styles from './Cart.module.css';

// -----------------------------------
// ROW
// -----------------------------------

function QtyStepper({
  item,
  disabled,
  onQtyChange,
}: {
  item: CartItem;
  disabled: boolean;
  onQtyChange: (itemId: string, quantity: number) => void;
}) {
  return (
    <div className={styles.qtyStepper}>
      <button
        type="button"
        disabled={disabled || item.quantity <= 1}
        onClick={() => onQtyChange(item.id, item.quantity - 1)}
        aria-label="Decrease quantity">
        −
      </button>
      <span>{item.quantity}</span>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onQtyChange(item.id, item.quantity + 1)}
        aria-label="Increase quantity">
        +
      </button>
    </div>
  );
}

function RemoveButton({
  item,
  disabled,
  onRemove,
}: {
  item: CartItem;
  disabled: boolean;
  onRemove: (itemId: string) => void;
}) {
  return (
    <button
      type="button"
      className={styles.removeBtn}
      disabled={disabled}
      onClick={() => onRemove(item.id)}
      aria-label={`Remove ${item.product_name} from cart`}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M5 5l14 14M19 5 5 19" strokeLinecap="round" />
      </svg>
    </button>
  );
}

/**
 * Below `md` this renders as the reference's stacked phone layout: image,
 * then name/variant/price/qty stacked underneath with the remove "X" at top
 * right. At `md` and up the reference switches to a single row -- image,
 * name/variant/price, then quantity, line total and remove lined up on the
 * right -- so `.desktopMeta` duplicates the qty stepper and remove button
 * or that row (CSS shows exactly one copy of each at a time; see
 * Cart.module.css) rather than reflowing the same nodes, which CSS alone
 * can't do across a breakpoint that also regroups the surrounding markup.
 */
function CartRow({
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
    <div className={styles.row}>
      <div className={styles.thumb}>
        {item.image && (
          <Image
            src={item.image.url}
            alt={item.image.alt_text ?? item.product_name}
            fill
            sizes="(min-width: 992px) 140px, 110px"
          />
        )}
      </div>

      <div className={styles.info}>
        <div className={styles.infoTop}>
          <div>
            <p className={styles.name}>
              <Link href={`/single-product/${item.product_id}`}>{item.product_name}</Link>
            </p>
            <p className={styles.variant}>{item.variant_name}</p>
          </div>

          <div className={styles.removeBtnMobile}>
            <RemoveButton item={item} disabled={disabled} onRemove={onRemove} />
          </div>
        </div>

        <p className={styles.price}>{formatMoney(item.unit_price, STOREFRONT_CURRENCY)}</p>

        <div className={styles.qtyStepperMobile}>
          <QtyStepper item={item} disabled={disabled} onQtyChange={onQtyChange} />
        </div>
      </div>

      <div className={styles.desktopMeta}>
        <QtyStepper item={item} disabled={disabled} onQtyChange={onQtyChange} />
        <p className={styles.lineTotal}>{formatMoney(item.subtotal, STOREFRONT_CURRENCY)}</p>
        <RemoveButton item={item} disabled={disabled} onRemove={onRemove} />
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
 * All data comes from CartContext, the same real, backend-held cart the
 * header badge and every "Add to Cart" button already use -- there is no
 * separate fetch or mock data here.
 */
export default function Cart({ preview }: { preview: CheckoutPreview | null }) {
  const { cart, items, pending, error, updateQuantity, removeFromCart, clearCart } = useCart();

  async function handleRemove(itemId: string) {
    await removeFromCart(itemId);
    toast.info('Removed from your cart');
  }

  async function handleClearCart() {
    if (!window.confirm('Remove everything from your cart?')) return;
    await clearCart();
    toast.info('Cart cleared');
  }

  const total = preview ? preview.total_amount : cart.subtotal;

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <h1 className={styles.heading}>My Cart</h1>
        <p className={styles.subtitle}>Review your items before checkout</p>

        {error && <div className={styles.error}>{error}</div>}

        {items.length === 0 ? (
          <div className={styles.empty}>
            <div className={styles.emptyIcon}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4">
                <path d="M6 8h12l1 12.5a1 1 0 0 1-1 1.5H6a1 1 0 0 1-1-1.5L6 8Z" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M9 8V6a3 3 0 0 1 6 0v2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <p className={styles.emptyHeading}>Your cart is empty</p>
            <p className={styles.emptyText}>Looks like you haven&apos;t added anything yet.</p>
            <Link href="/shop-standard" className={styles.continueBtn}>
              Continue Shopping
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M4 12h16M13 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </Link>
          </div>
        ) : (
          <>
            <div className={styles.list}>
              {items.map(item => (
                <CartRow
                  key={item.id}
                  item={item}
                  disabled={pending}
                  onQtyChange={updateQuantity}
                  onRemove={handleRemove}
                />
              ))}
            </div>

            <div className={styles.clearCartRow}>
              <button type="button" className={styles.clearCartBtn} disabled={pending} onClick={handleClearCart}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                  <path d="M4 7h16M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2m-9 0 1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Clear Cart
              </button>
            </div>

            <Link href="/check-out" className={styles.checkoutBar}>
              <span className={styles.checkoutLabel}>Proceed to Checkout</span>
              <span className={styles.checkoutRight}>
                {formatMoney(total, STOREFRONT_CURRENCY)}
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M4 12h16M13 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
            </Link>
          </>
        )}
      </div>

      <MobileBottomNav />
    </div>
  );
}
