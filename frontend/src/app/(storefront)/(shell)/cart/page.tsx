import type { Metadata } from 'next';

import CartLine from '@/components/cart/CartLine';
import ButtonLink from '@/components/ui/ButtonLink';
import { Container, Section } from '@/components/ui/Layout';
import { EmptyState } from '@/components/ui/States';
import { checkoutApi } from '@/lib/api/orders';
import { getAccessToken } from '@/lib/auth/session';
import { getCart } from '@/lib/cart/read';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatMoney } from '@/lib/format';

import styles from '@/components/cart/CartView.module.css';

export const metadata: Metadata = {
  title: 'Your cart',
  robots: { index: false, follow: false },
};

export default async function CartPage() {
  const token = await getAccessToken();
  const cart = await getCart();

  /*
   * The cart itself only carries a subtotal. Shipping, tax and the real
   * total exist solely on the checkout preview, so a signed-in shopper gets
   * the true figures and a guest sees the subtotal with delivery quoted at
   * checkout -- rather than a total invented here.
   */
  const preview = token && cart.items.length > 0
    ? await checkoutApi.preview(token).catch(() => null)
    : null;

  const currency = STOREFRONT_CURRENCY;

  return (
    <main>
      <Section>
        <Container>
          <h1>Your cart</h1>

          {cart.items.length === 0 ? (
            <EmptyState
              title="Your cart is empty"
              body="Pieces you add will show up here."
              action={<ButtonLink href="/shop">Browse the collection</ButtonLink>}
            />
          ) : (
            <div className={styles.layout} style={{ marginTop: 'var(--space-6)' }}>
              <div className={styles.lines}>
                {cart.items.map((item) => (
                  <CartLine key={item.id} item={item} currency={currency} />
                ))}
              </div>

              <aside className={styles.summary}>
                <h2 className={styles.summaryTitle}>Summary</h2>

                <div className={styles.row}>
                  <span>Subtotal</span>
                  <span data-numeric>{formatMoney(preview?.subtotal ?? cart.subtotal, currency)}</span>
                </div>

                {preview && Number(preview.discount_amount) > 0 && (
                  <div className={styles.row}>
                    <span>Discount</span>
                    <span data-numeric>-{formatMoney(preview.discount_amount, currency)}</span>
                  </div>
                )}

                {preview && (
                  <>
                    <div className={styles.row}>
                      <span>Delivery</span>
                      <span data-numeric>
                        {Number(preview.shipping_amount) === 0
                          ? 'Free'
                          : formatMoney(preview.shipping_amount, currency)}
                      </span>
                    </div>

                    <div className={styles.row}>
                      <span>Tax</span>
                      <span data-numeric>{formatMoney(preview.tax_amount, currency)}</span>
                    </div>
                  </>
                )}

                <div className={`${styles.row} ${styles.total}`}>
                  <span>Total</span>
                  <span data-numeric>
                    {formatMoney(preview?.total_amount ?? cart.subtotal, currency)}
                  </span>
                </div>

                {!preview && (
                  <p className={styles.note}>Delivery and tax are calculated at checkout.</p>
                )}

                <div className={styles.cta}>
                  <ButtonLink href={token ? '/checkout' : '/signin?next=/checkout'} size="lg" block>
                    {token ? 'Checkout' : 'Sign in to check out'}
                  </ButtonLink>
                </div>
              </aside>
            </div>
          )}
        </Container>
      </Section>
    </main>
  );
}
