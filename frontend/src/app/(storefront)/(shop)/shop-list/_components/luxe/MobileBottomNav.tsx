'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { BagIcon, UserIcon } from '@/app/(storefront)/(home)/home/_components/luxe/Icons';
import { useWishlist } from '@/context/WishlistContext';

import { HeartIcon, HomeIcon } from './Icons';
import listingStyles from './Listing.module.css';

/**
 * App-style bottom tab bar, shown only on small viewports (see
 * `.mobileBottomNav` in Listing.module.css) -- matches the reference mobile
 * mockup's Home/Shop/Wishlist/Account bar. Scoped to the Product Listing
 * page only, not the shared layout, per the task's "modify only the Product
 * Listing page" constraint.
 *
 * The wishlist badge is the real saved-item count from WishlistContext; the
 * other tabs carry no counts because nothing real backs one here (cart count
 * already lives on the header's cart pill, untouched by this page).
 */
export default function MobileBottomNav() {
  const pathname = usePathname();
  const { wishlist } = useWishlist();
  const wishlistCount = wishlist.items.length;

  const items = [
    { href: '/', label: 'Home', Icon: HomeIcon },
    { href: '/shop-list', label: 'Shop', Icon: BagIcon },
    { href: '/shop-wishlist', label: 'Wishlist', Icon: HeartIcon, badge: wishlistCount },
    { href: '/my-account', label: 'Account', Icon: UserIcon },
  ];

  return (
    <nav className={listingStyles.mobileBottomNav} aria-label="Mobile">
      {items.map(({ href, label, Icon, badge }) => {
        const active = pathname === href;
        return (
          <Link
            key={label}
            href={href}
            className={`${listingStyles.mobileNavItem} ${active ? listingStyles.mobileNavItemActive : ''}`}
            aria-current={active ? 'page' : undefined}
          >
            <span className={listingStyles.mobileNavIconWrap}>
              <Icon size={20} />
              {!!badge && <span className={listingStyles.mobileNavBadge}>{badge}</span>}
            </span>
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
