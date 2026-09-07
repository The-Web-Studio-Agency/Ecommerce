import StorefrontShell from '@/components/StorefrontShell';
import { getCurrentUser } from '@/lib/auth/current-user';
import { getCart } from '@/lib/cart/read';
import type { UserProfile } from '@/types/auth';
import type { Cart } from '@/types/cart';

const EMPTY_CART: Cart = { id: 'guest', items: [], subtotal: '0.00', item_count: 0 };

/**
 * Resolve the session and cart for every storefront page.
 *
 * A backend that is down degrades to a signed-out visitor with an empty
 * cart rather than an error page: the catalogue still reads, and the pages
 * that genuinely need a session say so themselves.
 */
async function loadShellData(): Promise<{ user: UserProfile | null; cart: Cart }> {
  const [user, cart] = await Promise.all([
    getCurrentUser().catch(() => null),
    getCart().catch(() => EMPTY_CART),
  ]);

  return { user, cart };
}

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const { user, cart } = await loadShellData();

  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Roboto:wght@100;300;400;500;700;900&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <StorefrontShell user={user} cart={cart}>
          {children}
        </StorefrontShell>
      </body>
    </html>
  );
}
