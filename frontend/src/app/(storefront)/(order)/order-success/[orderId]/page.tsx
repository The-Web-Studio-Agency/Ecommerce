import { notFound } from 'next/navigation';

import CommanLayout from '@/components/CommanLayout';
import CommonBanner2 from '@/components/CommonBanner2';
import { ApiError } from '@/lib/api/errors';
import { orderApi } from '@/lib/api/orders';
import { getAccessToken } from '@/lib/auth/session';
import type { Order } from '@/types/orders';
import OrderSuccess from '../_components/OrderSuccess';

export default async function OrderSuccessPage({ params }: { params: Promise<{ orderId: string }> }) {
  const { orderId } = await params;

  const token = await getAccessToken();
  if (!token) notFound();

  let order: Order;

  try {
    order = await orderApi.get(token, orderId);
  } catch (error) {
    /* Someone else's order reads as 403; either way there is nothing to show. */
    if (error instanceof ApiError && (error.isNotFound || error.isForbidden)) notFound();
    throw error;
  }

  return (
    <CommanLayout>
      <CommonBanner2 parentText="CheckOut" currentText="Order Success" mainText="Shop Standard" />
      <OrderSuccess order={order} />
    </CommanLayout>
  );
}
