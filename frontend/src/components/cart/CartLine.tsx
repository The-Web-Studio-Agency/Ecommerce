'use client';

import Image from 'next/image';
import { useActionState } from 'react';

import { removeCartItem, updateCartQuantity } from '@/lib/cart/actions';
import { initialCartState } from '@/lib/cart/state';
import { formatMoney } from '@/lib/format';
import type { CartItem } from '@/types/cart';

import styles from './CartView.module.css';

const MAX_SELECTABLE = 10;

export default function CartLine({ item, currency }: { item: CartItem; currency: string }) {
  const [, updateAction] = useActionState(updateCartQuantity, initialCartState);
  const [, removeAction] = useActionState(removeCartItem, initialCartState);

  return (
    <div className={styles.line}>
      <div className={styles.thumb}>
        {item.image && (
          <Image
            src={item.image.url}
            alt={item.image.alt_text ?? item.product_name}
            fill
            className={styles.thumbImage}
            sizes="96px"
          />
        )}
      </div>

      <div>
        <p className={styles.name}>{item.product_name}</p>
        <p className={styles.sku}>{item.variant_name}</p>
        <p className={styles.unit} data-numeric>
          {formatMoney(item.unit_price, currency)} each
        </p>

        <div className={styles.controls}>
          <form action={updateAction} className={styles.qtyForm}>
            <input type="hidden" name="item_id" value={item.id} />

            <label htmlFor={`qty-${item.id}`} className={styles.sku}>
              Qty
            </label>

            <select
              id={`qty-${item.id}`}
              name="quantity"
              defaultValue={item.quantity}
              className={styles.qtySelect}
              onChange={(event) => event.currentTarget.form?.requestSubmit()}
            >
              {Array.from({ length: MAX_SELECTABLE }, (_, index) => index + 1).map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </form>

          <form action={removeAction}>
            <input type="hidden" name="item_id" value={item.id} />
            <button type="submit" className={styles.remove}>
              Remove
            </button>
          </form>
        </div>
      </div>

      <p className={styles.lineTotal} data-numeric>
        {formatMoney(item.subtotal, currency)}
      </p>
    </div>
  );
}
