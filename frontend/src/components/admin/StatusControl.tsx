'use client';

import { useActionState, useState } from 'react';

import Button from '@/components/ui/Button';
import { updateOrderStatus } from '@/lib/admin/actions';
import { initialCheckoutState } from '@/lib/orders/state';
import { ALLOWED_TRANSITIONS, type OrderStatus } from '@/types/orders';

import styles from './AdminShell.module.css';

/**
 * Offers only the statuses this order may legally move to. The backend
 * enforces the same table, so an illegal move fails there too.
 */
export default function StatusControl({
  orderId,
  status,
}: {
  orderId: string;
  status: OrderStatus;
}) {
  const allowed = ALLOWED_TRANSITIONS[status];
  const [next, setNext] = useState<string>(allowed[0] ?? '');
  const [state, action, pending] = useActionState(updateOrderStatus, initialCheckoutState);

  if (allowed.length === 0) {
    return <p className={styles.tileLabel}>This order is finished. No further changes.</p>;
  }

  return (
    <form action={action} style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center', flexWrap: 'wrap' }}>
      <input type="hidden" name="order_id" value={orderId} />

      <label htmlFor="next-status" className={styles.tileLabel}>
        Move to
      </label>

      <select
        id="next-status"
        name="status"
        value={next}
        onChange={(event) => setNext(event.target.value)}
        style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--line-strong)', borderRadius: 'var(--radius-control)' }}
      >
        {allowed.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>

      <Button type="submit" size="sm" disabled={pending}>
        {pending ? 'Updating' : 'Update status'}
      </Button>

      {state.message && <span className={styles.tileLabel}>{state.message}</span>}
    </form>
  );
}
