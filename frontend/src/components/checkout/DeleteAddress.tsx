'use client';

import { useActionState } from 'react';

import Button from '@/components/ui/Button';
import { deleteAddress } from '@/lib/orders/actions';
import { initialCheckoutState } from '@/lib/orders/state';

export default function DeleteAddress({ addressId }: { addressId: string }) {
  const [, action, pending] = useActionState(deleteAddress, initialCheckoutState);

  return (
    <form action={action}>
      <input type="hidden" name="address_id" value={addressId} />

      <Button type="submit" variant="ghost" size="sm" disabled={pending}>
        {pending ? 'Removing' : 'Remove'}
      </Button>
    </form>
  );
}
