import type { Metadata } from 'next';
import { notFound, redirect } from 'next/navigation';

import { Container, Section } from '@/components/ui/Layout';
import { ApiError } from '@/lib/api/errors';
import { orderApi } from '@/lib/api/orders';
import { getAccessToken } from '@/lib/auth/session';
import { formatDate, formatMoney } from '@/lib/format';

import styles from './Invoice.module.css';

export const metadata: Metadata = {
  title: 'Invoice',
  robots: { index: false, follow: false },
};

/**
 * Rendered from the order itself.
 *
 * The backend has no invoice endpoint, but an order already carries every
 * line, the address, tax, delivery, totals and currency -- so this is real
 * data rather than a document invented to fill the page.
 */
export default async function InvoicePage({ params }: { params: Promise<{ id: string }> }) {
  const token = await getAccessToken();
  const { id } = await params;

  if (!token) redirect(`/signin?next=/orders/${id}/invoice`);

  let order;

  try {
    order = await orderApi.get(token, id);
  } catch (error) {
    if (error instanceof ApiError && (error.isNotFound || error.isForbidden || error.status === 422))
      notFound();
    throw error;
  }

  return (
    <main>
      <Section>
        <Container width="text">
          <article className={styles.sheet}>
            <header className={styles.head}>
              <div>
                <p className={styles.brand}>Zeen</p>
                <p className={styles.muted}>Cash on delivery across India</p>
              </div>

              <div className={styles.right}>
                <p className={styles.number}>{order.order_number}</p>
                <p className={styles.muted}>{formatDate(order.created_at)}</p>
              </div>
            </header>

            <section className={styles.parties}>
              <div>
                <h2 className={styles.label}>Billed to</h2>
                <p className={styles.address}>
                  {order.delivery_address.full_name}
                  <br />
                  {order.delivery_address.address_line_1}
                  {order.delivery_address.address_line_2
                    ? `, ${order.delivery_address.address_line_2}`
                    : ''}
                  <br />
                  {order.delivery_address.city}, {order.delivery_address.state}{' '}
                  {order.delivery_address.postal_code}
                  <br />
                  {order.delivery_address.country}
                </p>
              </div>

              <div>
                <h2 className={styles.label}>Payment</h2>
                <p className={styles.address}>
                  {order.payment?.provider === 'COD' ? 'Cash on delivery' : (order.payment?.provider ?? '-')}
                  <br />
                  {order.payment_status === 'PAID' ? 'Paid' : 'Due on delivery'}
                </p>
              </div>
            </section>

            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Item</th>
                  <th className={styles.numCell}>Qty</th>
                  <th className={styles.numCell}>Unit</th>
                  <th className={styles.numCell}>Amount</th>
                </tr>
              </thead>

              <tbody>
                {order.items.map((item) => (
                  <tr key={item.variant_id}>
                    <td>
                      {item.product_name}
                      <br />
                      <span className={styles.muted}>{item.sku}</span>
                    </td>
                    <td className={styles.numCell} data-numeric>
                      {item.quantity}
                    </td>
                    <td className={styles.numCell} data-numeric>
                      {formatMoney(item.unit_price, order.currency)}
                    </td>
                    <td className={styles.numCell} data-numeric>
                      {formatMoney(item.subtotal, order.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className={styles.totals}>
              <div className={styles.totalRow}>
                <span>Subtotal</span>
                <span data-numeric>{formatMoney(order.subtotal, order.currency)}</span>
              </div>

              {Number(order.discount_amount) > 0 && (
                <div className={styles.totalRow}>
                  <span>Discount{order.coupon_code ? ` (${order.coupon_code})` : ''}</span>
                  <span data-numeric>-{formatMoney(order.discount_amount, order.currency)}</span>
                </div>
              )}

              <div className={styles.totalRow}>
                <span>Delivery</span>
                <span data-numeric>{formatMoney(order.shipping_amount, order.currency)}</span>
              </div>

              <div className={styles.totalRow}>
                <span>Tax</span>
                <span data-numeric>{formatMoney(order.tax_amount, order.currency)}</span>
              </div>

              <div className={`${styles.totalRow} ${styles.grand}`}>
                <span>Total</span>
                <span data-numeric>{formatMoney(order.total_amount, order.currency)}</span>
              </div>
            </div>
          </article>
        </Container>
      </Section>
    </main>
  );
}
