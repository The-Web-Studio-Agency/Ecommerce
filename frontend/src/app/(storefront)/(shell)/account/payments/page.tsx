import type { Metadata } from 'next';
import Link from 'next/link';
import { redirect } from 'next/navigation';

import { PaymentStatusBadge } from '@/components/orders/OrderStatus';
import ButtonLink from '@/components/ui/ButtonLink';
import { Container, Section } from '@/components/ui/Layout';
import { EmptyState } from '@/components/ui/States';
import { orderApi } from '@/lib/api/orders';
import { getAccessToken } from '@/lib/auth/session';
import { formatDate, formatMoney } from '@/lib/format';

import styles from '../Account.module.css';

export const metadata: Metadata = {
  title: 'Payments',
  robots: { index: false, follow: false },
};

/**
 * Built from the order list.
 *
 * There is no customer payment listing on the backend -- only a lookup for
 * a single payment by id -- but every order carries its own payment, so the
 * history is assembled from real records rather than invented.
 */
export default async function PaymentsPage() {
  const token = await getAccessToken();
  if (!token) redirect('/signin?next=/account/payments');

  const orders = await orderApi.list(token, { page_size: 50 }).catch(() => null);
  const items = orders?.items ?? [];

  return (
    <main>
      <Section>
        <Container width="text">
          <h1>Payments</h1>

          {items.length === 0 ? (
            <EmptyState
              title="Nothing to show yet"
              body="Payments appear here once you have placed an order."
              action={<ButtonLink href="/shop">Browse the collection</ButtonLink>}
            />
          ) : (
            <div style={{ marginTop: 'var(--space-5)' }}>
              {items.map((order) => (
                <div key={order.id} className={styles.row}>
                  <div>
                    <Link href={`/orders/${order.id}`} className={styles.name}>
                      {order.order_number}
                    </Link>
                    <p className={styles.muted}>{formatDate(order.created_at)}</p>
                  </div>

                  <PaymentStatusBadge status={order.payment_status} />

                  <p className={styles.amount} data-numeric>
                    {formatMoney(order.total_amount, order.currency)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Container>
      </Section>
    </main>
  );
}
