'use client';

import { useActionState } from 'react';

import { toggleWishlist } from '@/lib/cart/actions';
import { initialCartState } from '@/lib/cart/state';

import styles from './CartView.module.css';

export default function WishlistRemove({ itemId }: { itemId: string }) {
  const [, action, pending] = useActionState(toggleWishlist, initialCartState);

  return (
    <form action={action}>
      <input type="hidden" name="item_id" value={itemId} />

      <button type="submit" className={styles.remove} disabled={pending}>
        {pending ? 'Removing' : 'Remove'}
      </button>
    </form>
  );
}
