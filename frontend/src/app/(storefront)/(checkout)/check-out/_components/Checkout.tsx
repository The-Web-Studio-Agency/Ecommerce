'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useActionState, useEffect, useState } from 'react';

import { useCart } from '@/context/CartContext';
import { placeOrder, previewCheckoutFor } from '@/lib/orders/actions';
import { initialCheckoutState } from '@/lib/orders/state';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatMoney } from '@/lib/format';
import type { Address } from '@/types/addresses';
import type { CheckoutPreview } from '@/types/orders';

import AddressFormModal from './AddressFormModal';
import styles from './Checkout.module.css';
import CheckoutHeader from './CheckoutHeader';
import OrderSummaryPanel from './OrderSummaryPanel';

// -----------------------------------
// ICONS
// -----------------------------------

function ChevronRightIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="m9 6 6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
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

function CardIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="2.5" y="5.5" width="19" height="13" rx="2" />
      <path d="M2.5 10h19" strokeLinecap="round" />
    </svg>
  );
}

function CodIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="2.5" y="7" width="19" height="12" rx="2" />
      <circle cx="12" cy="13" r="3" />
      <path d="M2.5 10.5h3M18.5 10.5h3" strokeLinecap="round" />
    </svg>
  );
}

function GooglePayIcon() {
  return (
    <span style={{ background: '#4285F4' }} className={styles.methodBadge}>
      G
    </span>
  );
}

function PayPalIcon() {
  return (
    <span style={{ background: '#003087' }} className={styles.methodBadge}>
      P
    </span>
  );
}

function UpiIcon() {
  return (
    <span style={{ background: '#1a1a1a', fontSize: '9px' }} className={styles.methodBadge}>
      UPI
    </span>
  );
}

// -----------------------------------
// ADDRESS SECTION
// -----------------------------------

function AddressSection({
  addresses,
  selectedId,
  disabled,
  onSelect,
  onEdit,
  onAddNew,
}: {
  addresses: Address[];
  selectedId: string | null;
  disabled: boolean;
  onSelect: (id: string) => void;
  onEdit: (address: Address) => void;
  onAddNew: () => void;
}) {
  return (
    <section>
      <div className={styles.sectionHeader}>
        <div className={styles.sectionTitleGroup}>
          <span className={styles.stepNumber}>1</span>
          <h2 className={styles.sectionTitle}>Delivery Address</h2>
        </div>
        <Link href="/account-address" className={styles.manageLink}>
          Manage Addresses
        </Link>
      </div>

      <div className={styles.card}>
        {addresses.length === 0 ? (
          <p className={styles.emptyAddresses}>No saved addresses yet -- add one below.</p>
        ) : (
          addresses.map(address => {
            const selected = address.id === selectedId;
            return (
              <div key={address.id} className={`${styles.row} ${selected ? styles.rowSelected : ''}`}>
                <input
                  type="radio"
                  name="delivery_address"
                  className={styles.radio}
                  checked={selected}
                  disabled={disabled}
                  onChange={() => onSelect(address.id)}
                  aria-label={`Deliver to ${address.full_name}`}
                />
                <div className={styles.addressBody} onClick={() => !disabled && onSelect(address.id)}>
                  <div className={styles.addressTopLine}>
                    <span className={styles.addressLabel}>{address.full_name}</span>
                    {address.is_default && <span className={styles.defaultBadge}>Default</span>}
                  </div>
                  <p className={styles.addressLine}>
                    {address.address_line_1}
                    {address.address_line_2 ? `, ${address.address_line_2}` : ''}
                  </p>
                  <p className={styles.addressLine}>
                    {address.city}, {address.state} {address.postal_code}, {address.country}
                  </p>
                  <p className={styles.addressLine}>{address.phone}</p>
                </div>
                <button
                  type="button"
                  className={styles.addressEdit}
                  onClick={() => onEdit(address)}
                  disabled={disabled}>
                  Edit
                  <ChevronRightIcon />
                </button>
              </div>
            );
          })
        )}
      </div>

      <button type="button" className={styles.addAddressBtn} onClick={onAddNew} disabled={disabled}>
        <span style={{ fontSize: '16px', lineHeight: 1 }}>+</span> Add New Address
      </button>
    </section>
  );
}

// -----------------------------------
// SHIPPING SECTION
// -----------------------------------

function ShippingSection({ preview }: { preview: CheckoutPreview | null }) {
  const shippingAmount = preview ? Number(preview.shipping_amount) : 0;

  return (
    <section>
      <div className={styles.sectionHeader}>
        <div className={styles.sectionTitleGroup}>
          <span className={styles.stepNumber}>2</span>
          <h2 className={styles.sectionTitle}>Shipping Method</h2>
        </div>
      </div>

      <div className={styles.card}>
        <div className={styles.row}>
          <input type="radio" name="shipping_method" className={styles.radio} checked readOnly aria-label="Standard shipping" />
          <span className={styles.methodIcon}>
            <TruckIcon />
          </span>
          <div className={styles.methodBody}>
            <p className={styles.methodTitle}>Standard Shipping</p>
            <p className={styles.methodDesc}>5 - 7 business days</p>
          </div>
          <span className={styles.methodPrice}>
            {shippingAmount > 0 ? formatMoney(preview?.shipping_amount, STOREFRONT_CURRENCY) : 'Free'}
          </span>
        </div>

        <div className={`${styles.row} ${styles.rowDisabled}`}>
          <input type="radio" name="shipping_method" className={styles.radio} disabled aria-label="Express shipping" />
          <span className={styles.methodIcon}>
            <TruckIcon />
          </span>
          <div className={styles.methodBody}>
            <p className={styles.methodTitle}>
              Express Shipping <span className={styles.comingSoon}>Coming soon</span>
            </p>
            <p className={styles.methodDesc}>2 - 3 business days</p>
          </div>
        </div>
      </div>
    </section>
  );
}

// -----------------------------------
// PAYMENT SECTION
// -----------------------------------

function PaymentSection() {
  return (
    <section>
      <div className={styles.sectionHeader}>
        <div className={styles.sectionTitleGroup}>
          <span className={styles.stepNumber}>3</span>
          <h2 className={styles.sectionTitle}>Payment Method</h2>
        </div>
      </div>

      <div className={styles.card}>
        <div className={`${styles.row} ${styles.rowDisabled}`}>
          <input type="radio" name="payment_method" className={styles.radio} disabled aria-label="Credit or debit card" />
          <span className={styles.methodIcon}>
            <CardIcon />
          </span>
          <div className={styles.methodBody}>
            <p className={styles.methodTitle}>
              Credit / Debit Card <span className={styles.comingSoon}>Coming soon</span>
            </p>
            <p className={styles.methodDesc}>Visa, Mastercard, RuPay, AMEX, etc.</p>
          </div>
          <div className={styles.cardNetworks}>
            <span>VISA</span>
            <span>MC</span>
            <span>AMEX</span>
          </div>
        </div>

        <div className={`${styles.row} ${styles.rowDisabled}`}>
          <input type="radio" name="payment_method" className={styles.radio} disabled aria-label="Google Pay" />
          <GooglePayIcon />
          <div className={styles.methodBody}>
            <p className={styles.methodTitle}>
              Google Pay <span className={styles.comingSoon}>Coming soon</span>
            </p>
            <p className={styles.methodDesc}>Pay with Google Pay</p>
          </div>
        </div>

        <div className={`${styles.row} ${styles.rowDisabled}`}>
          <input type="radio" name="payment_method" className={styles.radio} disabled aria-label="PayPal" />
          <PayPalIcon />
          <div className={styles.methodBody}>
            <p className={styles.methodTitle}>
              PayPal <span className={styles.comingSoon}>Coming soon</span>
            </p>
            <p className={styles.methodDesc}>Pay with PayPal</p>
          </div>
        </div>

        <div className={`${styles.row} ${styles.rowDisabled}`}>
          <input type="radio" name="payment_method" className={styles.radio} disabled aria-label="UPI" />
          <UpiIcon />
          <div className={styles.methodBody}>
            <p className={styles.methodTitle}>
              UPI <span className={styles.comingSoon}>Coming soon</span>
            </p>
            <p className={styles.methodDesc}>Pay via UPI (PhonePe, Google Pay, Paytm, etc.)</p>
          </div>
        </div>

        <div className={styles.row}>
          <input type="radio" name="payment_method" className={styles.radio} checked readOnly aria-label="Cash on delivery" />
          <span className={styles.methodIcon}>
            <CodIcon />
          </span>
          <div className={styles.methodBody}>
            <p className={styles.methodTitle}>Cash on Delivery</p>
            <p className={styles.methodDesc}>Pay when your order is delivered</p>
          </div>
        </div>
      </div>

      <label className={styles.billingRow}>
        <input type="checkbox" defaultChecked disabled />
        Billing address is the same as delivery address
      </label>
    </section>
  );
}

// -----------------------------------
// CHECKOUT
// -----------------------------------

/**
 * The checkout page.
 *
 * Line items and their images come from `CartContext` (the real, backend
 * held cart); pricing (subtotal/discount/shipping/tax/total) comes from
 * `CheckoutPreview`, re-fetched whenever a coupon is applied or removed via
 * `previewCheckoutFor` -- the backend re-validates the coupon against the
 * real cart every time, so nothing about money is computed here. Only the
 * chosen address, coupon code and a stable idempotency key are ever sent to
 * `placeOrder`; the backend computes and charges everything else.
 */
export default function Checkout({
  initialAddresses,
  initialPreview,
}: {
  initialAddresses: Address[];
  initialPreview: CheckoutPreview | null;
}) {
  const router = useRouter();
  const { items: cartItems } = useCart();

  const [addresses, setAddresses] = useState(initialAddresses);
  useEffect(() => setAddresses(initialAddresses), [initialAddresses]);

  const [preview, setPreview] = useState(initialPreview);
  useEffect(() => setPreview(initialPreview), [initialPreview]);

  const [selectedAddressId, setSelectedAddressId] = useState<string | null>(
    () => addresses.find(address => address.is_default)?.id ?? addresses[0]?.id ?? null,
  );
  useEffect(() => {
    if (selectedAddressId && addresses.some(address => address.id === selectedAddressId)) return;
    setSelectedAddressId(addresses.find(address => address.is_default)?.id ?? addresses[0]?.id ?? null);
  }, [addresses, selectedAddressId]);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingAddress, setEditingAddress] = useState<Address | null>(null);

  const [couponInput, setCouponInput] = useState('');
  const [couponPending, setCouponPending] = useState(false);
  const [couponError, setCouponError] = useState<string | null>(null);

  const [idempotencyKey] = useState(() => crypto.randomUUID());
  const [placeState, placeFormAction, placePending] = useActionState(placeOrder, initialCheckoutState);

  async function handleApplyCoupon() {
    const code = couponInput.trim();
    if (!code) return;

    setCouponPending(true);
    setCouponError(null);
    const result = await previewCheckoutFor(selectedAddressId, code);
    setCouponPending(false);

    if (result.error) {
      setCouponError(result.error);
      return;
    }

    setPreview(result.preview);
    setCouponInput('');
  }

  async function handleRemoveCoupon() {
    setCouponPending(true);
    const result = await previewCheckoutFor(selectedAddressId, null);
    setCouponPending(false);
    setCouponError(null);
    setPreview(result.preview);
  }

  function openAddModal() {
    setEditingAddress(null);
    setModalOpen(true);
  }

  function openEditModal(address: Address) {
    setEditingAddress(address);
    setModalOpen(true);
  }

  function handleAddressSaved() {
    setModalOpen(false);
    // `saveAddress`/`updateAddress` already revalidated `/check-out` on the
    // server; `router.refresh()` re-runs this page's server component so
    // the fresh address list flows back down as props (same pattern
    // `CartContext` uses after a mutation), without a full page reload.
    router.refresh();
  }

  const canPlaceOrder = Boolean(selectedAddressId) && cartItems.length > 0;

  return (
    <div className={styles.page}>
      <CheckoutHeader />

      <form action={placeFormAction} className={styles.container}>
        <input type="hidden" name="address_id" value={selectedAddressId ?? ''} />
        <input type="hidden" name="coupon_code" value={preview?.coupon_code ?? ''} />
        <input type="hidden" name="idempotency_key" value={idempotencyKey} />

        <nav className={styles.breadcrumb} aria-label="Checkout progress">
          <Link href="/cart-items">Cart</Link>
          <span>›</span>
          <span className={styles.breadcrumbCurrent}>Checkout</span>
          <span>›</span>
          <span>Payment</span>
          <span>›</span>
          <span>Order Confirmed</span>
        </nav>

        <h1 className={styles.heading}>Checkout</h1>
        <p className={styles.subtitle}>Complete your order securely and easily.</p>

        {cartItems.length === 0 && <div className={styles.error}>Your cart is empty -- add something before checking out.</div>}

        <div className={styles.grid}>
          <div className={styles.main}>
            <AddressSection
              addresses={addresses}
              selectedId={selectedAddressId}
              disabled={placePending}
              onSelect={setSelectedAddressId}
              onEdit={openEditModal}
              onAddNew={openAddModal}
            />
            <ShippingSection preview={preview} />
            <PaymentSection />
          </div>

          <div className={styles.sidebar}>
            <OrderSummaryPanel
              cartItems={cartItems}
              preview={preview}
              couponInput={couponInput}
              onCouponInputChange={setCouponInput}
              onApplyCoupon={handleApplyCoupon}
              onRemoveCoupon={handleRemoveCoupon}
              couponPending={couponPending}
              couponError={couponError}
              canPlaceOrder={canPlaceOrder}
              placeOrderPending={placePending}
              placeOrderError={placeState.status === 'error' ? placeState.message : null}
            />
          </div>
        </div>
      </form>

      {modalOpen && (
        <AddressFormModal address={editingAddress} onClose={() => setModalOpen(false)} onSaved={handleAddressSaved} />
      )}
    </div>
  );
}
