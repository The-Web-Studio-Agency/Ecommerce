import Link from 'next/link';

import AdminShell from '@/components/admin/AdminShell';
import { OrderStatusBadge, PaymentStatusBadge } from '@/components/orders/OrderStatus';
import { EmptyState } from '@/components/ui/States';
import { adminApi } from '@/lib/api/admin';
import { requireStaff } from '@/lib/auth/require-staff';
import { formatDate, formatMoney } from '@/lib/format';
import type { OrderStatus, PaymentStatus } from '@/types/orders';

import styles from '@/components/admin/AdminShell.module.css';

const ORDER_STATUSES: OrderStatus[] = [
  'PENDING',
  'CONFIRMED',
  'PROCESSING',
  'SHIPPED',
  'DELIVERED',
  'CANCELLED',
];

const PAYMENT_STATUSES: PaymentStatus[] = ['PENDING', 'PAID', 'FAILED', 'REFUNDED'];

export default async function AdminOrdersPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; payment_status?: string; order_number?: string; page?: string }>;
}) {
  const { user, token } = await requireStaff();
  const query = await searchParams;

  const page = Number.parseInt(query.page ?? '1', 10);

  // Unknown enum values are dropped rather than sent, since the backend
  // rejects them with a 422.
  const orders = await adminApi.listOrders(token, {
    page: Number.isFinite(page) && page > 0 ? page : 1,
    page_size: 25,
    order_number: query.order_number,
    status: ORDER_STATUSES.includes(query.status as OrderStatus)
      ? (query.status as OrderStatus)
      : undefined,
    payment_status: PAYMENT_STATUSES.includes(query.payment_status as PaymentStatus)
      ? (query.payment_status as PaymentStatus)
      : undefined,
  });

  return (
    <AdminShell user={user}>
      <h1 className={styles.sectionTitle}>Orders</h1>

      <form style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-5)', flexWrap: 'wrap' }}>
        <input
          name="order_number"
          placeholder="Order number"
          defaultValue={query.order_number ?? ''}
          style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--line-strong)', borderRadius: 'var(--radius-control)' }}
        />

        <select
          name="status"
          defaultValue={query.status ?? ''}
          style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--line-strong)', borderRadius: 'var(--radius-control)' }}
        >
          <option value="">Any status</option>
          {ORDER_STATUSES.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>

        <select
          name="payment_status"
          defaultValue={query.payment_status ?? ''}
          style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--line-strong)', borderRadius: 'var(--radius-control)' }}
        >
          <option value="">Any payment</option>
          {PAYMENT_STATUSES.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>

        <button
          type="submit"
          style={{ padding: '0.5rem 1rem', background: 'var(--ink)', color: 'var(--on-dark)', border: 'none', borderRadius: 'var(--radius-control)', cursor: 'pointer' }}
        >
          Filter
        </button>
      </form>

      {orders.items.length === 0 ? (
        <EmptyState title="No orders match" body="Try clearing the filters." />
      ) : (
        <div className={styles.scroll}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Order</th>
                <th>Placed</th>
                <th>Status</th>
                <th>Payment</th>
                <th className={styles.num}>Total</th>
              </tr>
            </thead>

            <tbody>
              {orders.items.map((order) => (
                <tr key={order.id}>
                  <td>
                    <Link href={`/admin/orders/${order.id}`} className={styles.link2}>
                      {order.order_number}
                    </Link>
                  </td>
                  <td>{formatDate(order.created_at)}</td>
                  <td>
                    <OrderStatusBadge status={order.status} />
                  </td>
                  <td>
                    <PaymentStatusBadge status={order.payment_status} />
                  </td>
                  <td className={styles.num} data-numeric>
                    {formatMoney(order.total_amount, order.currency)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className={styles.tileLabel} style={{ marginTop: 'var(--space-4)' }} data-numeric>
        {orders.meta.total_items} orders, page {orders.meta.page} of {orders.meta.total_pages}
      </p>
    </AdminShell>
  );
}
