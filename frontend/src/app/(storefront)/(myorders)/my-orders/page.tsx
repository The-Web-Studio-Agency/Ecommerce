import CommanLayout from '@/components/CommanLayout';
import ProtectedRoute from '@/components/ProtectedRoute';
import { orderApi } from '@/lib/api/orders';
import { getAccessToken } from '@/lib/auth/session';
import MyOrders from './_components/MyOrders';

/** Order history. Middleware guarantees a session by the time this runs. */
export default async function MyOrdersPage() {
  const token = await getAccessToken();
  const page = token ? await orderApi.list(token, { page_size: 50 }) : null;

  return (
    <CommanLayout>
      <ProtectedRoute>
        <MyOrders orders={page ? page.items : []} />
      </ProtectedRoute>
    </CommanLayout>
  );
}
