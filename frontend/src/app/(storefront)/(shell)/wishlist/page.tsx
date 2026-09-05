import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import { redirect } from 'next/navigation';

import ButtonLink from '@/components/ui/ButtonLink';
import { Container, Section } from '@/components/ui/Layout';
import { EmptyState } from '@/components/ui/States';
import { wishlistApi } from '@/lib/api/cart';
import { getAccessToken } from '@/lib/auth/session';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatMoney } from '@/lib/format';
import WishlistRemove from '@/components/cart/WishlistRemove';

import styles from '@/components/cart/CartView.module.css';

export const metadata: Metadata = {
  title: 'Wishlist',
  robots: { index: false, follow: false },
};

export default async function WishlistPage() {
  const token = await getAccessToken();
  if (!token) redirect('/signin?next=/wishlist');

  const wishlist = await wishlistApi.get(token).catch(() => null);
  const items = wishlist?.items ?? [];

  return (
    <main>
      <Section>
        <Container>
          <h1>Wishlist</h1>

          {items.length === 0 ? (
            <EmptyState
              title="Nothing saved yet"
              body="Save pieces from a product page to keep them here."
              action={<ButtonLink href="/shop">Browse the collection</ButtonLink>}
            />
          ) : (
            <div className={styles.lines} style={{ marginTop: 'var(--space-6)' }}>
              {items.map((item) => (
                <div key={item.id} className={styles.line}>
                  <div className={styles.thumb}>
                    {item.image && (
                      <Image
                        src={item.image.url}
                        alt={item.image.alt_text ?? item.product_name}
                        fill
                        className={styles.thumbImage}
                        sizes="96px"
                      />
                    )}
                  </div>

                  <div>
                    <Link href={`/products/${item.product_id}`} className={styles.name}>
                      {item.product_name}
                    </Link>
                    <p className={styles.sku}>{item.variant_name}</p>
                    <p className={styles.unit} data-numeric>
                      {formatMoney(String(item.unit_price), STOREFRONT_CURRENCY)}
                    </p>

                    <div className={styles.controls}>
                      <WishlistRemove itemId={item.id} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Container>
      </Section>
    </main>
  );
}
