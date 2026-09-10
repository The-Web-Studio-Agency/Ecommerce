import Link from 'next/link';

import styles from '@/app/(storefront)/(home)/home/_components/luxe/Home.module.css';
import {
  InstagramIcon,
  TikTokIcon,
  XSocialIcon,
} from '@/app/(storefront)/(home)/home/_components/luxe/Icons';

const FOOTER_COLUMNS = [
  {
    title: 'Shop',
    links: [
      { label: 'New Arrivals', href: '/shop-list' },
      { label: 'Collections', href: '/shop-list' },
      { label: 'Best Sellers', href: '/shop-list' },
      { label: 'Gift Cards', href: '/our-gift-vouchers' },
    ],
  },
  {
    title: 'About',
    links: [
      { label: 'Our Story', href: '/about-us' },
      { label: 'Sustainability', href: '/about-us' },
      { label: 'Journal', href: '/blog-list-no-sidebar' },
      { label: 'Contact Us', href: '/contact-us-1' },
    ],
  },
  {
    title: 'Customer Care',
    links: [
      { label: 'Shipping & Returns', href: '/faqs-1' },
      { label: 'FAQs', href: '/faqs-1' },
      { label: 'Product Care', href: '/faqs-1' },
      { label: 'Track Order', href: '/my-orders' },
    ],
  },
];

/** The Zeen footer, shared by every page in the luxe design system. See LuxeHeader for why it's a copy, not an import, of the Home page's own markup. */
export default function LuxeFooter() {
  return (
    <footer className={styles.footer}>
      <div className={styles.container}>
        <div className={styles.footerTop}>
          <div>
            <p className={styles.footerBrand}>ZEEN</p>
            <p className={styles.footerTagline}>
              Crafting timeless leather handbags with exceptional craftsmanship, premium materials, and modern
              elegance.
            </p>
            <div className={styles.footerSocials}>
              <a href="#" aria-label="X (Twitter)">
                <XSocialIcon />
              </a>
              <a href="#" aria-label="Instagram">
                <InstagramIcon />
              </a>
              <a href="#" aria-label="TikTok">
                <TikTokIcon />
              </a>
            </div>
          </div>

          {FOOTER_COLUMNS.map(col => (
            <div key={col.title} className={styles.footerCol}>
              <p className={styles.footerColTitle}>{col.title}</p>
              <ul>
                {col.links.map(link => (
                  <li key={link.label}>
                    <Link href={link.href}>{link.label}</Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className={styles.footerImage}>
          <img src="/home/footer-showroom.jpg" alt="Zeen flagship showroom" />
        </div>

        <div className={styles.footerBottom}>
          <span>© {new Date().getFullYear()} Zeen. All rights reserved.</span>
          <span>Crafted with care.</span>
        </div>
      </div>
    </footer>
  );
}
