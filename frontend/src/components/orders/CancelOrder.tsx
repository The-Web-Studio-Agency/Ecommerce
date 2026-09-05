'use client';

import { useActionState } from 'react';

import Button from '@/components/ui/Button';
import { cancelOrder } from '@/lib/orders/actions';
import { initialCheckoutState } from '@/lib/orders/state';

import styles from './Orders.module.css';

export default function CancelOrder({ orderId }: { orderId: string }) {
  const [state, action, pending] = useActionState(cancelOrder, initialCheckoutState);

  return (
    <form action={action}>
      <input type="hidden" name="order_id" value={orderId} />

      <Button type="submit" variant="secondary" disabled={pending}>
        {pending ? 'Cancelling' : 'Cancel order'}
      </Button>

      {state.status === 'error' && state.message && <p className={styles.cancelled}>{state.message}</p>}
    </form>
  );
}
