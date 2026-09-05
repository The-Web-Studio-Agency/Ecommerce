'use client';

import { useActionState, useMemo, useState } from 'react';

import Button from '@/components/ui/Button';
import { Select } from '@/components/ui/Field';
import { addToCart, toggleWishlist } from '@/lib/cart/actions';
import { initialCartState } from '@/lib/cart/state';
import { formatMoney } from '@/lib/format';
import type { StorefrontOption, VariantStorefront } from '@/types/catalogue';

import styles from './BuyBox.module.css';

/**
 * Resolves an option selection to a variant, because the cart is keyed by
 * variant and not by product plus colour and size.
 *
 * A product with no options has exactly one variant, and it is selected
 * outright rather than making someone choose from a list of one.
 */
function findVariant(
  variants: VariantStorefront[],
  selection: Record<string, string>,
): VariantStorefront | null {
  const names = Object.keys(selection);
  if (names.length === 0) return variants[0] ?? null;

  return (
    variants.find((variant) => names.every((name) => variant.options[name] === selection[name])) ?? null
  );
}

export default function BuyBox({
  options,
  variants,
  currency,
  isSignedIn,
}: {
  options: StorefrontOption[];
  variants: VariantStorefront[];
  currency: string;
  isSignedIn: boolean;
}) {
  const [selection, setSelection] = useState<Record<string, string>>({});
  const [quantity, setQuantity] = useState(1);
  const [cartState, cartAction, adding] = useActionState(addToCart, initialCartState);
  const [wishState, wishAction, saving] = useActionState(toggleWishlist, initialCartState);

  const variant = useMemo(() => findVariant(variants, selection), [variants, selection]);

  const needsChoice = options.length > 0 && Object.keys(selection).length < options.length;
  const maxQuantity = Math.min(variant?.available_quantity ?? 0, 10);

  return (
    <div className={styles.root}>
      {options.map((option) => (
        <div key={option.name} className={styles.optionGroup}>
          <span className={styles.optionName}>{option.name}</span>

          <div className={styles.values}>
            {option.values.map((value) => {
              const selected = selection[option.name] === value;

              // A value is only offered if some variant carrying it is in
              // stock, so a shopper cannot select their way to nothing.
              const available = variants.some(
                (candidate) => candidate.options[option.name] === value && candidate.in_stock,
              );

              return (
                <button
                  key={value}
                  type="button"
                  className={[
                    styles.value,
                    selected ? styles.valueSelected : '',
                    available ? '' : styles.valueUnavailable,
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  aria-pressed={selected}
                  disabled={!available}
                  onClick={() => setSelection((current) => ({ ...current, [option.name]: value }))}
                >
                  {value}
                </button>
              );
            })}
          </div>
        </div>
      ))}

      {variant && (
        <p className={styles.stock}>
          {variant.in_stock
            ? variant.available_quantity <= 5
              ? `Only ${variant.available_quantity} left`
              : 'In stock'
            : 'Sold out'}
          {options.length > 0 && ` - ${formatMoney(variant.price, currency)}`}
        </p>
      )}

      <form action={cartAction} className={styles.row}>
        <input type="hidden" name="variant_id" value={variant?.id ?? ''} />

        <div className={styles.quantity}>
          <Select
            label="Quantity"
            name="quantity"
            value={String(quantity)}
            onChange={(event) => setQuantity(Number(event.target.value))}
            disabled={!variant?.in_stock}
          >
            {Array.from({ length: Math.max(maxQuantity, 1) }, (_, index) => index + 1).map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </Select>
        </div>

        <Button type="submit" size="lg" disabled={adding || needsChoice || !variant?.in_stock}>
          {adding ? 'Adding' : needsChoice ? 'Choose an option' : variant?.in_stock ? 'Add to cart' : 'Sold out'}
        </Button>
      </form>

      {isSignedIn && variant && (
        <form action={wishAction}>
          <input type="hidden" name="variant_id" value={variant.id} />

          <Button type="submit" variant="secondary" disabled={saving}>
            {saving ? 'Saving' : 'Save to wishlist'}
          </Button>
        </form>
      )}

      {cartState.message && (
        <p
          className={`${styles.feedback} ${cartState.status === 'error' ? styles.error : styles.success}`}
          role="status"
        >
          {cartState.message}
        </p>
      )}

      {wishState.message && (
        <p
          className={`${styles.feedback} ${wishState.status === 'error' ? styles.error : styles.success}`}
          role="status"
        >
          {wishState.message}
        </p>
      )}
    </div>
  );
}
