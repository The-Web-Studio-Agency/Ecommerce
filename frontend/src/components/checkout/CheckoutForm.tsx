'use client';

import { useActionState, useMemo, useState } from 'react';

import Button from '@/components/ui/Button';
import { Input } from '@/components/ui/Field';
import { applyCoupon, placeOrder } from '@/lib/orders/actions';
import { initialCheckoutState } from '@/lib/orders/state';
import { formatMoney } from '@/lib/format';
import type { Address } from '@/types/addresses';
import type { CheckoutPreview } from '@/types/orders';

import AddressForm from './AddressForm';
import styles from './Checkout.module.css';

export default function CheckoutForm({
  addresses,
  preview,
  currency,
  appliedCoupon,
}: {
  addresses: Address[];
  preview: CheckoutPreview | null;
  currency: string;
  appliedCoupon: string | null;
}) {
  const defaultAddress = addresses.find((address) => address.is_default) ?? addresses[0];
  const [selected, setSelected] = useState(defaultAddress?.id ?? '');
  const [showForm, setShowForm] = useState(addresses.length === 0);

  const [couponState, couponAction, applyingCoupon] = useActionState(applyCoupon, initialCheckoutState);
  const [orderState, orderAction, placing] = useActionState(placeOrder, initialCheckoutState);

  /*
   * One key per visit to this page. Submitting twice -- a double click, a
   * refresh, a flaky connection -- returns the first order rather than
   * creating a second.
   */
  const idempotencyKey = useMemo(() => crypto.randomUUID(), []);

  const coupon = couponState.couponCode ?? appliedCoupon ?? '';

  return (
    <div className={styles.layout}>
      <div>
        <section className={styles.step}>
          <h2 className={styles.stepTitle}>Delivery address</h2>

          {addresses.length > 0 && (
            <div className={styles.addresses}>
              {addresses.map((address) => (
                <label
                  key={address.id}
                  className={`${styles.address} ${selected === address.id ? styles.addressSelected : ''}`}
                >
                  <input
                    type="radio"
                    name="address_choice"
                    value={address.id}
                    checked={selected === address.id}
                    onChange={() => setSelected(address.id)}
                  />

                  <span className={styles.addressBody}>
                    <span className={styles.addressName}>{address.full_name}</span>
                    <br />
                    {address.address_line_1}
                    {address.address_line_2 ? `, ${address.address_line_2}` : ''}
                    <br />
                    {address.city}, {address.state} {address.postal_code}
                    <br />
                    <span className={styles.muted}>{address.phone}</span>
                  </span>
                </label>
              ))}
            </div>
          )}

          {showForm ? (
            <AddressForm />
          ) : (
            <div style={{ marginTop: 'var(--space-4)' }}>
              <Button type="button" variant="secondary" onClick={() => setShowForm(true)}>
                Add a new address
              </Button>
            </div>
          )}
        </section>

        <section className={styles.step}>
          <h2 className={styles.stepTitle}>Discount</h2>

          <form action={couponAction} className={styles.couponRow}>
            <div className={styles.couponInput}>
              <Input label="Coupon code" name="code" defaultValue={coupon} placeholder="Enter a code" />
            </div>

            <Button type="submit" variant="secondary" disabled={applyingCoupon}>
              {applyingCoupon ? 'Checking' : 'Apply'}
            </Button>
          </form>

          {couponState.message && (
            <p
              className={`${styles.alert} ${couponState.status === 'success' ? styles.success : ''}`}
              style={{ marginTop: 'var(--space-3)', marginBottom: 0 }}
            >
              {couponState.message}
            </p>
          )}
        </section>

        <section className={styles.step}>
          <h2 className={styles.stepTitle}>Payment</h2>
          <p className={styles.payment}>Cash on delivery. Pay when your order arrives.</p>
        </section>
      </div>

      <aside className={styles.summary}>
        <h2 className={styles.summaryTitle}>Your order</h2>

        {preview?.items.map((item) => (
          <div key={item.variant_id} className={styles.item}>
            <span className={styles.itemName}>
              {item.product_name} &times; {item.quantity}
            </span>
            <span data-numeric>{formatMoney(item.subtotal, currency)}</span>
          </div>
        ))}

        {preview && (
          <div className={styles.rows}>
            <div className={styles.row}>
              <span>Subtotal</span>
              <span data-numeric>{formatMoney(preview.subtotal, currency)}</span>
            </div>

            {Number(preview.discount_amount) > 0 && (
              <div className={styles.row}>
                <span>Discount{preview.coupon_code ? ` (${preview.coupon_code})` : ''}</span>
                <span data-numeric>-{formatMoney(preview.discount_amount, currency)}</span>
              </div>
            )}

            <div className={styles.row}>
              <span>Delivery</span>
              <span data-numeric>
                {Number(preview.shipping_amount) === 0
                  ? 'Free'
                  : formatMoney(preview.shipping_amount, currency)}
              </span>
            </div>

            <div className={styles.row}>
              <span>Tax</span>
              <span data-numeric>{formatMoney(preview.tax_amount, currency)}</span>
            </div>

            <div className={`${styles.row} ${styles.total}`}>
              <span>Total</span>
              <span data-numeric>{formatMoney(preview.total_amount, currency)}</span>
            </div>
          </div>
        )}

        <form action={orderAction} className={styles.cta}>
          <input type="hidden" name="address_id" value={selected} />
          <input type="hidden" name="coupon_code" value={coupon} />
          <input type="hidden" name="idempotency_key" value={idempotencyKey} />

          {orderState.status === 'error' && orderState.message && (
            <p className={styles.alert}>{orderState.message}</p>
          )}

          <Button type="submit" size="lg" block disabled={placing || !selected}>
            {placing ? 'Placing order' : 'Place order'}
          </Button>
        </form>
      </aside>
    </div>
  );
}
