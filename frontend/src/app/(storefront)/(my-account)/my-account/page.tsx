import Link from 'next/link';
import { redirect } from 'next/navigation';

import CommanLayout from '@/components/CommanLayout';
import CommonBanner2 from '@/components/CommonBanner2';
import DeleteAccountButton from '@/components/DeleteAccountButton';
import SignOutButton from '@/components/SignOutButton';
import { addressApi } from '@/lib/api/addresses';
import { orderApi } from '@/lib/api/orders';
import { getCurrentUser } from '@/lib/auth/current-user';
import { getAccessToken } from '@/lib/auth/session';
import { formatDate, formatMoney } from '@/lib/format';

/** How many recent orders the account page lists before linking on. */
const RECENT_ORDERS = 5;

export default async function MyAccountPage() {
  const token = await getAccessToken();
  const user = await getCurrentUser();

  /* Middleware guards this route, so an absent session here means the token
     was rejected between the redirect and the render. */
  if (!token || !user) redirect('/signin?next=/my-account');

  const [orders, addresses] = await Promise.all([
    orderApi.list(token, { page_size: RECENT_ORDERS }).then(page => page.items).catch(() => []),
    addressApi.list(token).catch(() => []),
  ]);

  return (
    <CommanLayout>
      <CommonBanner2 parentText="Home" currentText="My Account" mainText="My Account" />

      <div className="myorderPage">
        <div className="myorderContainer">
          <div className="myorderHeader">
            <div>
              <h1 className="myorderTitle">My account</h1>
            </div>
          </div>

          {/* PROFILE */}

          <div className="myorderTableCard">
            <div className="myorderTableScroll">
              <table className="myorderTable">
                <tbody>
                  <tr className="myorderRow myorderRowBorder">
                    <td className="myorderTd myorderTdDate">Name</td>
                    <td className="myorderTd myorderTdOrderId">{user.name ?? '—'}</td>
                  </tr>
                  <tr className="myorderRow myorderRowBorder">
                    <td className="myorderTd myorderTdDate">Phone</td>
                    <td className="myorderTd myorderTdOrderId">{user.phone}</td>
                  </tr>
                  <tr className="myorderRow myorderRowBorder">
                    <td className="myorderTd myorderTdDate">Email</td>
                    <td className="myorderTd myorderTdOrderId">{user.email ?? '—'}</td>
                  </tr>
                  <tr className="myorderRow">
                    <td className="myorderTd myorderTdDate">Addresses</td>
                    <td className="myorderTd myorderTdOrderId">{addresses.length}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* RECENT ORDERS */}

          <div className="myorderHeader">
            <div>
              <h2 className="myorderTitle">Recent orders</h2>
            </div>
          </div>

          <div className="myorderTableCard">
            <div className="myorderTableScroll">
              <table className="myorderTable">
                <thead>
                  <tr className="myorderHeadRow">
                    <th className="myorderTh">Order Id</th>
                    <th className="myorderTh">Order Place</th>
                    <th className="myorderTh">Total Amount</th>
                    <th className="myorderTh">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order, index) => (
                    <tr
                      key={order.id}
                      className={`myorderRow ${index === orders.length - 1 ? '' : 'myorderRowBorder'}`}>
                      <td className="myorderTd myorderTdOrderId">
                        <Link href={`/order-success/${order.id}`}>#{order.order_number}</Link>
                      </td>
                      <td className="myorderTd myorderTdDate">{formatDate(order.created_at)}</td>
                      <td className="myorderTd myorderTdAmount">
                        {formatMoney(order.total_amount, order.currency)}
                      </td>
                      <td className="myorderTd myorderTdDate">{order.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {orders.length === 0 && (
              <div className="myorderEmptyState">
                <p className="myorderEmptyText">You haven&apos;t placed any orders yet</p>
              </div>
            )}
          </div>

          <div className="myorderFilters">
            <Link href="/my-orders" className="myorderFilterButton">
              All orders
            </Link>

            <Link href="/payment-history" className="myorderFilterButton">
              Payments
            </Link>

            <SignOutButton />

            <DeleteAccountButton />
          </div>
        </div>
      </div>
    </CommanLayout>
  );
}
