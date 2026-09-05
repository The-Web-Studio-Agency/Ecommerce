import Link from 'next/link';

import AdminShell from '@/components/admin/AdminShell';
import { OrderStatusBadge, PaymentStatusBadge } from '@/components/orders/OrderStatus';
import { adminApi } from '@/lib/api/admin';
import { requireStaff } from '@/lib/auth/require-staff';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatDate, formatMoney } from '@/lib/format';

import styles from '@/components/admin/AdminShell.module.css';

function Delta({ value }: { value: number | null }) {
  if (value === null) return null;

  const rounded = Math.round(value * 10) / 10;
  const tone = rounded >= 0 ? styles.up : styles.down;

  return (
    <p className={`${styles.tileDelta} ${tone}`} data-numeric>
      {rounded >= 0 ? '+' : ''}
      {rounded}% on the period before
    </p>
  );
}

export default async function AdminDashboard() {
  const { user, token } = await requireStaff();
  const data = await adminApi.dashboard(token);
  const currency = STOREFRONT_CURRENCY;

  return (
    <AdminShell user={user}>
      <h1 className={styles.sectionTitle}>Today</h1>

      <div className={styles.tiles}>
        <div className={styles.tile}>
          <p className={styles.tileLabel}>Revenue today</p>
          <p className={styles.tileValue} data-numeric>
            {formatMoney(data.sales.today.revenue, currency)}
          </p>
          <Delta value={data.sales.today.revenue_change_pct} />
        </div>

        <div className={styles.tile}>
          <p className={styles.tileLabel}>Orders today</p>
          <p className={styles.tileValue} data-numeric>
            {data.sales.today.order_count}
          </p>
          <Delta value={data.sales.today.order_count_change_pct} />
        </div>

        <div className={styles.tile}>
          <p className={styles.tileLabel}>Revenue this month</p>
          <p className={styles.tileValue} data-numeric>
            {formatMoney(data.sales.month.revenue, currency)}
          </p>
          <Delta value={data.sales.month.revenue_change_pct} />
        </div>

        <div className={styles.tile}>
          <p className={styles.tileLabel}>Awaiting action</p>
          <p className={styles.tileValue} data-numeric>
            {data.orders.pending + data.orders.processing}
          </p>
          <p className={styles.tileLabel}>
            {data.orders.pending} placed, {data.orders.processing} being packed
          </p>
        </div>

        <div className={styles.tile}>
          <p className={styles.tileLabel}>Low or out of stock</p>
          <p className={styles.tileValue} data-numeric>
            {data.inventory.low_stock_count + data.inventory.out_of_stock_count}
          </p>
          <p className={styles.tileLabel}>
            {data.inventory.out_of_stock_count} out, {data.inventory.low_stock_count} running low
          </p>
        </div>

        <div className={styles.tile}>
          <p className={styles.tileLabel}>Customers</p>
          <p className={styles.tileValue} data-numeric>
            {data.customers.total}
          </p>
          <p className={styles.tileLabel}>{data.customers.new_this_month} new this month</p>
        </div>
      </div>

      <div className={styles.blocks}>
        <section>
          <h2 className={styles.sectionTitle}>Recent orders</h2>

          <div className={styles.scroll}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Status</th>
                  <th className={styles.num}>Total</th>
                </tr>
              </thead>

              <tbody>
                {data.recent_orders.map((order) => (
                  <tr key={order.order_id}>
                    <td>
                      <Link href={`/admin/orders/${order.order_id}`} className={styles.link2}>
                        {order.order_number}
                      </Link>
                      <br />
                      <span className={styles.tileLabel}>{formatDate(order.created_at)}</span>
                    </td>
                    <td>
                      <OrderStatusBadge status={order.order_status} />{' '}
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
        </section>

        <section>
          <h2 className={styles.sectionTitle}>Needs restocking</h2>

          <div className={styles.scroll}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>SKU</th>
                  <th className={styles.num}>Available</th>
                </tr>
              </thead>

              <tbody>
                {[...data.inventory.out_of_stock_variants, ...data.inventory.low_stock_variants]
                  .slice(0, 8)
                  .map((variant) => (
                    <tr key={variant.sku}>
                      <td>{variant.product_name}</td>
                      <td>{variant.sku}</td>
                      <td className={styles.num} data-numeric>
                        {variant.available_quantity}
                      </td>
                    </tr>
                  ))}

                {data.inventory.out_of_stock_variants.length === 0 &&
                  data.inventory.low_stock_variants.length === 0 && (
                    <tr>
                      <td colSpan={3}>Everything is in stock.</td>
                    </tr>
                  )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </AdminShell>
  );
}
