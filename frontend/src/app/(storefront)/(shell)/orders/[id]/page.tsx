import type { Metadata } from 'next';
import { notFound, redirect } from 'next/navigation';

import CancelOrder from '@/components/orders/CancelOrder';
import { OrderStatusBadge, PaymentStatusBadge, ORDER_LABELS } from '@/components/orders/OrderStatus';
import ButtonLink from '@/components/ui/ButtonLink';
import { Container, Section } from '@/components/ui/Layout';
import { ApiError } from '@/lib/api/errors';
import { orderApi } from '@/lib/api/orders';
import { getAccessToken } from '@/lib/auth/session';
import { formatDateTime, formatMoney } from '@/lib/format';
import { CANCELLABLE_STATUSES, type OrderStatus } from '@/types/orders';

import styles from '@/components/orders/Orders.module.css';

export const metadata: Metadata = {
  title: 'Order',
  robots: { index: false, follow: false },
};

/** The only progress the backend records is this sequence of states. */
const TRACK: OrderStatus[] = ['PENDING', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED'];

export default async function OrderDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ placed?: string }>;
}) {
  const token = await getAccessToken();
  const { id } = await params;
  const { placed } = await searchParams;

  if (!token) redirect(`/signin?next=/orders/${id}`);

  let order;

  try {
    order = await orderApi.get(token, id);
  } catch (error) {
    if (error instanceof ApiError && (error.isNotFound || error.isForbidden)) notFound();
    throw error;
  }

  const reached = TRACK.indexOf(order.status);
  const canCancel = CANCELLABLE_STATUSES.includes(order.status);

  return (
    <main>
      <Section>
        <Container>
          {placed && (
            <p className={styles.placed}>
              Order placed. We&rsquo;ll text you when it ships.
            </p>
          )}

          <div className={styles.detailHead}>
            <div>
              <h1>{order.order_number}</h1>
              <p className={styles.date}>Placed {formatDateTime(order.created_at)}</p>
            </div>

            <div className={styles.badges}>
              <OrderStatusBadge status={order.status} />
              <PaymentStatusBadge status={order.payment_status} />
            </div>
          </div>

          <div className={styles.layout}>
            <div>
              <h2 className={styles.panelTitle}>Items</h2>

              {order.items.map((item) => (
                <div key={item.variant_id} className={styles.item}>
                  <div>
                    <p className={styles.itemName}>{item.product_name}</p>
                    <p className={styles.date}>
                      {item.variant_name} &middot; {item.sku} &middot; Qty {item.quantity}
                    </p>
                  </div>

                  <p className={styles.amount} data-numeric>
                    {formatMoney(item.subtotal, order.currency)}
                  </p>
                </div>
              ))}

              <div style={{ marginTop: 'var(--space-6)' }}>
                <h2 className={styles.panelTitle}>Progress</h2>

                {order.status === 'CANCELLED' ? (
                  <p className={styles.cancelled}>This order was cancelled.</p>
                ) : (
                  <ol className={styles.track}>
                    {TRACK.map((step, index) => (
                      <li
                        key={step}
                        className={`${styles.step} ${index <= reached ? styles.stepDone : ''}`}
                      >
                        <span className={`${styles.dot} ${index <= reached ? styles.dotDone : ''}`} />
                        {ORDER_LABELS[step]}
                      </li>
                    ))}
                  </ol>
                )}
              </div>

              {canCancel && (
                <div style={{ marginTop: 'var(--space-6)' }}>
                  <CancelOrder orderId={order.id} />
                </div>
              )}
            </div>

            <aside>
              <div className={styles.panel}>
                <h2 className={styles.panelTitle}>Payment</h2>

                <div className={styles.row2}>
                  <span>Subtotal</span>
                  <span data-numeric>{formatMoney(order.subtotal, order.currency)}</span>
                </div>

                {Number(order.discount_amount) > 0 && (
                  <div className={styles.row2}>
                    <span>Discount{order.coupon_code ? ` (${order.coupon_code})` : ''}</span>
                    <span data-numeric>-{formatMoney(order.discount_amount, order.currency)}</span>
                  </div>
                )}

                <div className={styles.row2}>
                  <span>Delivery</span>
                  <span data-numeric>
                    {Number(order.shipping_amount) === 0
                      ? 'Free'
                      : formatMoney(order.shipping_amount, order.currency)}
                  </span>
                </div>

                <div className={styles.row2}>
                  <span>Tax</span>
                  <span data-numeric>{formatMoney(order.tax_amount, order.currency)}</span>
                </div>

                <div className={`${styles.row2} ${styles.total}`}>
                  <span>Total</span>
                  <span data-numeric>{formatMoney(order.total_amount, order.currency)}</span>
                </div>

                {order.payment && (
                  <p className={styles.date} style={{ marginTop: 'var(--space-3)' }}>
                    {order.payment.provider === 'COD' ? 'Cash on delivery' : order.payment.provider}
                  </p>
                )}
              </div>

              <div className={styles.panel} style={{ marginTop: 'var(--space-4)' }}>
                <h2 className={styles.panelTitle}>Delivering to</h2>

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
                  <br />
                  {order.delivery_address.phone}
                </p>
              </div>

              <div style={{ marginTop: 'var(--space-4)' }}>
                <ButtonLink href={`/orders/${order.id}/invoice`} variant="secondary" block>
                  View invoice
                </ButtonLink>
              </div>
            </aside>
          </div>
        </Container>
      </Section>
    </main>
  );
}
