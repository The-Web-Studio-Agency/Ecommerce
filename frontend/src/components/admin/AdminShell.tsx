import Link from 'next/link';

import SignOutButton from '@/components/auth/SignOutButton';
import type { UserProfile } from '@/types/auth';

import styles from './AdminShell.module.css';

/** Only the areas the backend actually serves appear here. */
const NAV = [
  { href: '/admin', label: 'Dashboard' },
  { href: '/admin/orders', label: 'Orders' },
  { href: '/admin/products', label: 'Products' },
  { href: '/admin/coupons', label: 'Coupons' },
  { href: '/admin/reviews', label: 'Reviews' },
  { href: '/admin/settings', label: 'Settings' },
];

export default function AdminShell({
  user,
  children,
}: {
  user: UserProfile;
  children: React.ReactNode;
}) {
  return (
    <div className={styles.shell}>
      <header className={styles.bar}>
        <Link href="/admin" className={styles.brand}>
          Zeen
        </Link>

        <nav className={styles.nav} aria-label="Admin">
          {NAV.map((item) => (
            <Link key={item.href} href={item.href} className={styles.link}>
              {item.label}
            </Link>
          ))}
        </nav>

        <div className={styles.user}>
          <span>
            {user.email ?? user.phone} ({user.role})
          </span>
          <SignOutButton />
        </div>
      </header>

      <main className={styles.main}>{children}</main>
    </div>
  );
}
