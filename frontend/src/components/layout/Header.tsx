import Link from 'next/link';

import { Container } from '@/components/ui/Layout';
import { catalogueApi } from '@/lib/api/catalogue';
import { getCurrentUser } from '@/lib/auth/current-user';
import { getCartCount } from '@/lib/cart/read';

import styles from './Header.module.css';

/**
 * Categories come from the catalogue rather than a hardcoded menu, so the
 * navigation is whatever the shop actually sells. A failure to load them
 * leaves the header working instead of taking the page down with it.
 */
async function navCategories() {
  try {
    const { items } = await catalogueApi.listCategories({ page_size: 8 });
    return items;
  } catch {
    return [];
  }
}

export default async function Header() {
  const [categories, user, cartCount] = await Promise.all([
    navCategories(),
    getCurrentUser(),
    getCartCount(),
  ]);

  return (
    <header className={styles.header}>
      <Container>
        <div className={styles.bar}>
          <Link href="/" className={styles.wordmark}>
            Zeen
          </Link>

          <nav className={styles.nav} aria-label="Categories">
            {categories.slice(0, 5).map((category) => (
              <Link key={category.id} href={`/shop?category=${category.id}`} className={styles.navLink}>
                {category.name}
              </Link>
            ))}
          </nav>

          <div className={styles.actions}>
            <Link href="/shop" className={styles.action}>
              Search
            </Link>

            <Link href={user ? '/account' : '/signin'} className={styles.action}>
              {user ? 'Account' : 'Sign in'}
            </Link>

            <Link href="/cart" className={styles.action}>
              Cart
              {cartCount > 0 && (
                <span className={styles.count} data-numeric>
                  ({cartCount})
                </span>
              )}
            </Link>
          </div>
        </div>

        {categories.length > 0 && (
          <nav className={styles.rail} aria-label="Categories">
            {categories.map((category) => (
              <Link key={category.id} href={`/shop?category=${category.id}`} className={styles.railLink}>
                {category.name}
              </Link>
            ))}
          </nav>
        )}
      </Container>
    </header>
  );
}
