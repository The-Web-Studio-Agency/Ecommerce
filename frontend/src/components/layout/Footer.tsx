import Link from 'next/link';

import { Container } from '@/components/ui/Layout';
import { catalogueApi } from '@/lib/api/catalogue';

import styles from './Footer.module.css';

async function footerCategories() {
  try {
    const { items } = await catalogueApi.listCategories({ page_size: 6 });
    return items;
  } catch {
    return [];
  }
}

export default async function Footer() {
  const categories = await footerCategories();

  return (
    <footer className={styles.footer}>
      <Container>
        <div className={styles.grid}>
          <div>
            <p className={styles.brand}>Zeen</p>
            <p className={styles.blurb}>
              Everyday pieces in considered fabrics, made to be worn far more than once.
            </p>
          </div>

          <div>
            <h2 className={styles.heading}>Shop</h2>
            <ul className={styles.list}>
              <li>
                <Link href="/shop" className={styles.link}>
                  All products
                </Link>
              </li>
              {categories.slice(0, 4).map((category) => (
                <li key={category.id}>
                  <Link href={`/shop?category=${category.id}`} className={styles.link}>
                    {category.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h2 className={styles.heading}>Your account</h2>
            <ul className={styles.list}>
              <li>
                <Link href="/account" className={styles.link}>
                  Account
                </Link>
              </li>
              <li>
                <Link href="/orders" className={styles.link}>
                  Orders
                </Link>
              </li>
              <li>
                <Link href="/account/addresses" className={styles.link}>
                  Addresses
                </Link>
              </li>
              <li>
                <Link href="/wishlist" className={styles.link}>
                  Wishlist
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h2 className={styles.heading}>Help</h2>
            <ul className={styles.list}>
              <li>
                <Link href="/orders" className={styles.link}>
                  Track an order
                </Link>
              </li>
              <li>
                <Link href="/shop" className={styles.link}>
                  Size and fit
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <p className={styles.base}>&copy; {new Date().getFullYear()} Zeen. Cash on delivery across India.</p>
      </Container>
    </footer>
  );
}
