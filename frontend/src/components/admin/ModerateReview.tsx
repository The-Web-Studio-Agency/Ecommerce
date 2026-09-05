'use client';

import { useActionState } from 'react';

import Button from '@/components/ui/Button';
import { moderateReview } from '@/lib/admin/actions';
import { initialCheckoutState } from '@/lib/orders/state';

export default function ModerateReview({
  reviewId,
  isApproved,
}: {
  reviewId: string;
  isApproved: boolean;
}) {
  const [, action, pending] = useActionState(moderateReview, initialCheckoutState);

  return (
    <form action={action}>
      <input type="hidden" name="review_id" value={reviewId} />
      <input type="hidden" name="is_approved" value={String(!isApproved)} />

      <Button type="submit" size="sm" variant={isApproved ? 'secondary' : 'primary'} disabled={pending}>
        {pending ? 'Saving' : isApproved ? 'Hide' : 'Approve'}
      </Button>
    </form>
  );
}
