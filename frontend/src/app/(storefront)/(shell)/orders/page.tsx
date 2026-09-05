import type { Metadata } from 'next';
import Link from 'next/link';
import { redirect } from 'next/navigation';

import { OrderStatusBadge, PaymentStatusBadge } from '@/components/orders/OrderStatus';
import ButtonLink from '@/components/ui/ButtonLink';
import { Container, Section } from '@/components/ui/Layout';
import { EmptyState } from '@/components/ui/States';
import { orderApi } from '@/lib/api/orders';
import { getAccessToken } from '@/lib/auth/session';
import { formatDate, formatMoney } from '@/lib/format';

import styles from '@/components/orders/Orders.module.css';

export const metadata: Metadata = {
  title: 'Your orders',
  robots: { index: false, follow: false },
};

export default async function OrdersPage() {
  const token = await getAccessToken();
  if (!token) redirect('/signin?next=/orders');

  const orders = await orderApi.list(token, { page_size: 20 }).catch(() => null);
  const items = orders?.items ?? [];

  return (
    <main>
      <Section>
        <Container>
          <h1>Your orders</h1>

          {items.length === 0 ? (
            <EmptyState
              title="No orders yet"
              body="When you order, it will show up here with its progress."
              action={<ButtonLink href="/shop">Browse the collection</ButtonLink>}
            />
          ) : (
            <div className={styles.list} style={{ marginTop: 'var(--space-6)' }}>
              {items.map((order) => (
                <Link key={order.id} href={`/orders/${order.id}`} className={styles.row}>
                  <div>
                    <p className={styles.number}>{order.order_number}</p>
                    <p className={styles.date}>{formatDate(order.created_at)}</p>
                  </div>

                  <div className={styles.badges}>
                    <OrderStatusBadge status={order.status} />
                    <PaymentStatusBadge status={order.payment_status} />
                  </div>

                  <p className={styles.amount} data-numeric>
                    {formatMoney(order.total_amount, order.currency)}
                  </p>
                </Link>
              ))}
            </div>
          )}
        </Container>
      </Section>
    </main>
  );
}
