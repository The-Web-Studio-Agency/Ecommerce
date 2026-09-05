import type { Metadata } from 'next';
import Link from 'next/link';
import { redirect } from 'next/navigation';

import SignOutButton from '@/components/auth/SignOutButton';
import { Container, Section } from '@/components/ui/Layout';
import { getCurrentUser } from '@/lib/auth/current-user';

import styles from './Account.module.css';

export const metadata: Metadata = {
  title: 'Your account',
  robots: { index: false, follow: false },
};

const LINKS = [
  { href: '/orders', title: 'Orders', body: 'Track what you have ordered and download invoices.' },
  { href: '/account/addresses', title: 'Addresses', body: 'Where your orders are delivered.' },
  { href: '/wishlist', title: 'Wishlist', body: 'Pieces you have saved for later.' },
  { href: '/account/payments', title: 'Payments', body: 'What you have paid, and what is still due.' },
];

export default async function AccountPage() {
  const user = await getCurrentUser();

  // Middleware turns guests away first; this holds even if that is bypassed.
  if (!user) redirect('/signin?next=/account');

  return (
    <main>
      <Section>
        <Container>
          <h1>Your account</h1>

          <div className={styles.details}>
            <dl className={styles.pairs}>
              <dt>Phone</dt>
              <dd>{user.phone}</dd>

              <dt>Name</dt>
              <dd>{user.name ?? <span className={styles.muted}>Not set</span>}</dd>

              <dt>Email</dt>
              <dd>{user.email ?? <span className={styles.muted}>Not set</span>}</dd>
            </dl>

            {/* The backend exposes no profile update, so this is read-only
                rather than a form that cannot save. */}
            <p className={styles.note}>
              To change your name or email, get in touch and we will update it for you.
            </p>
          </div>

          <div className={styles.grid}>
            {LINKS.map((link) => (
              <Link key={link.href} href={link.href} className={styles.tile}>
                <span className={styles.tileTitle}>{link.title}</span>
                <span className={styles.tileBody}>{link.body}</span>
              </Link>
            ))}
          </div>

          <div className={styles.signout}>
            <SignOutButton />
          </div>
        </Container>
      </Section>
    </main>
  );
}
