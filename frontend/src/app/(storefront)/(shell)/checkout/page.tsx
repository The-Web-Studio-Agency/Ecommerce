import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

import CheckoutForm from '@/components/checkout/CheckoutForm';
import ButtonLink from '@/components/ui/ButtonLink';
import { Container, Section } from '@/components/ui/Layout';
import { EmptyState } from '@/components/ui/States';
import { addressApi } from '@/lib/api/addresses';
import { checkoutApi } from '@/lib/api/orders';
import { getAccessToken } from '@/lib/auth/session';
import { getCart } from '@/lib/cart/read';
import { STOREFRONT_CURRENCY } from '@/lib/currency';

export const metadata: Metadata = {
  title: 'Checkout',
  robots: { index: false, follow: false },
};

export default async function CheckoutPage({
  searchParams,
}: {
  searchParams: Promise<{ coupon?: string }>;
}) {
  const token = await getAccessToken();
  if (!token) redirect('/signin?next=/checkout');

  const { coupon } = await searchParams;
  const cart = await getCart();

  if (cart.items.length === 0) {
    return (
      <main>
        <Section>
          <Container>
            <h1>Checkout</h1>
            <EmptyState
              title="Your cart is empty"
              body="Add something before checking out."
              action={<ButtonLink href="/shop">Browse the collection</ButtonLink>}
            />
          </Container>
        </Section>
      </main>
    );
  }

  const [addresses, preview] = await Promise.all([
    addressApi.list(token).catch(() => []),
    // Every figure shown comes from here. The frontend never adds up a total.
    checkoutApi.preview(token, { couponCode: coupon }).catch(() => null),
  ]);

  return (
    <main>
      <Section>
        <Container>
          <h1>Checkout</h1>

          <div style={{ marginTop: 'var(--space-6)' }}>
            <CheckoutForm
              addresses={addresses}
              preview={preview}
              currency={STOREFRONT_CURRENCY}
              appliedCoupon={coupon ?? null}
            />
          </div>
        </Container>
      </Section>
    </main>
  );
}
