'use client';

import { useActionState } from 'react';

import Button from '@/components/ui/Button';
import { Input } from '@/components/ui/Field';
import { saveAddress } from '@/lib/orders/actions';
import { initialCheckoutState } from '@/lib/orders/state';

import styles from './Checkout.module.css';

/**
 * Validation is the backend's. Field errors come straight from its 422
 * details, so the postal code rule that actually applies is the one shown.
 */
export default function AddressForm() {
  const [state, action, pending] = useActionState(saveAddress, initialCheckoutState);
  const errors = state.fieldErrors ?? {};

  return (
    <form action={action} className={styles.newAddress}>
      {state.status === 'error' && state.message && <p className={styles.alert}>{state.message}</p>}

      <Input label="Full name" name="full_name" autoComplete="name" required error={errors.full_name} />

      <Input
        label="Mobile number"
        name="phone"
        type="tel"
        inputMode="numeric"
        autoComplete="tel"
        required
        error={errors.phone}
      />

      <Input
        label="Address"
        name="address_line_1"
        autoComplete="address-line1"
        required
        error={errors.address_line_1}
      />

      <Input
        label="Apartment, floor"
        name="address_line_2"
        autoComplete="address-line2"
        optional
        error={errors.address_line_2}
      />

      <div className={styles.pair}>
        <Input label="City" name="city" autoComplete="address-level2" required error={errors.city} />
        <Input label="State" name="state" autoComplete="address-level1" required error={errors.state} />
      </div>

      <div className={styles.pair}>
        <Input
          label="PIN code"
          name="postal_code"
          inputMode="numeric"
          autoComplete="postal-code"
          required
          error={errors.postal_code}
        />
        <Input label="Country" name="country" defaultValue="India" required error={errors.country} />
      </div>

      <Button type="submit" disabled={pending}>
        {pending ? 'Saving' : 'Save address'}
      </Button>
    </form>
  );
}
