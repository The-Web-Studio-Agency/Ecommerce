import { notFound } from 'next/navigation';

import AdminShell from '@/components/admin/AdminShell';
import StatusControl from '@/components/admin/StatusControl';
import { OrderStatusBadge, PaymentStatusBadge } from '@/components/orders/OrderStatus';
import { adminApi } from '@/lib/api/admin';
import { ApiError } from '@/lib/api/errors';
import { requireStaff } from '@/lib/auth/require-staff';
import { formatDateTime, formatMoney } from '@/lib/format';

import styles from '@/components/admin/AdminShell.module.css';

export default async function AdminOrderPage({ params }: { params: Promise<{ id: string }> }) {
  const { user, token } = await requireStaff();
  const { id } = await params;

  let order;

  try {
    order = await adminApi.getOrder(token, id);
  } catch (error) {
    if (error instanceof ApiError && error.isNotFound) notFound();
    throw error;
  }

  return (
    <AdminShell user={user}>
      <h1 className={styles.sectionTitle}>{order.order_number}</h1>

      <p className={styles.tileLabel} style={{ marginBottom: 'var(--space-4)' }}>
        Placed {formatDateTime(order.created_at)} &middot; <OrderStatusBadge status={order.status} />{' '}
        <PaymentStatusBadge status={order.payment_status} />
      </p>

      {user.role === 'ADMIN' ? (
        <StatusControl orderId={order.id} status={order.status} />
      ) : (
        <p className={styles.tileLabel}>Only an admin can change an order&rsquo;s status.</p>
      )}

      <div className={styles.blocks} style={{ marginTop: 'var(--space-6)' }}>
        <section>
          <h2 className={styles.sectionTitle}>Items</h2>

          <div className={styles.scroll}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>SKU</th>
                  <th className={styles.num}>Qty</th>
                  <th className={styles.num}>Amount</th>
                </tr>
              </thead>

              <tbody>
                {order.items.map((item) => (
                  <tr key={item.variant_id}>
                    <td>{item.product_name}</td>
                    <td>{item.sku}</td>
                    <td className={styles.num} data-numeric>
                      {item.quantity}
                    </td>
                    <td className={styles.num} data-numeric>
                      {formatMoney(item.subtotal, order.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className={styles.sectionTitle}>Totals and delivery</h2>

          <div className={styles.scroll}>
            <table className={styles.table}>
              <tbody>
                <tr>
                  <td>Subtotal</td>
                  <td className={styles.num} data-numeric>
                    {formatMoney(order.subtotal, order.currency)}
                  </td>
                </tr>
                <tr>
                  <td>Discount{order.coupon_code ? ` (${order.coupon_code})` : ''}</td>
                  <td className={styles.num} data-numeric>
                    {formatMoney(order.discount_amount, order.currency)}
                  </td>
                </tr>
                <tr>
                  <td>Delivery</td>
                  <td className={styles.num} data-numeric>
                    {formatMoney(order.shipping_amount, order.currency)}
                  </td>
                </tr>
                <tr>
                  <td>Tax</td>
                  <td className={styles.num} data-numeric>
                    {formatMoney(order.tax_amount, order.currency)}
                  </td>
                </tr>
                <tr>
                  <td>Total</td>
                  <td className={styles.num} data-numeric>
                    {formatMoney(order.total_amount, order.currency)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <p className={styles.tileLabel} style={{ marginTop: 'var(--space-4)' }}>
            {order.delivery_address.full_name}
            <br />
            {order.delivery_address.address_line_1}
            {order.delivery_address.address_line_2 ? `, ${order.delivery_address.address_line_2}` : ''}
            <br />
            {order.delivery_address.city}, {order.delivery_address.state}{' '}
            {order.delivery_address.postal_code}
            <br />
            {order.delivery_address.phone}
          </p>
        </section>
      </div>
    </AdminShell>
  );
}
