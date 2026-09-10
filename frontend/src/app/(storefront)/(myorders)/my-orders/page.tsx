import CommanLayout from '@/components/CommanLayout';
import ProtectedRoute from '@/components/ProtectedRoute';
import { orderApi } from '@/lib/api/orders';
import { getAccessToken } from '@/lib/auth/session';
import MyOrders from './_components/MyOrders';

/**
 * Order history. Middleware guarantees a session by the time this runs.
 *
 * A failed listing renders as no orders rather than a 500, matching the rest
 * of the account pages: the call is refused outright for a signed-in
 * non-customer, and an API blip should not take the page down with it.
 */
export default async function MyOrdersPage() {
  const token = await getAccessToken();
  const orders = token
    ? await orderApi
        .list(token, { page_size: 50 })
        .then(page => page.items)
        .catch(() => [])
    : [];

  return (
    <CommanLayout>
      <ProtectedRoute>
        <MyOrders orders={orders} />
      </ProtectedRoute>
    </CommanLayout>
  );
}
