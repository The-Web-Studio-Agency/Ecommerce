'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useState } from 'react';

import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatPriceRange } from '@/lib/format';
import type { ProductStorefront, ProductSummaryStorefront } from '@/types/catalogue';

import styles from './Home.module.css';
import {
  ArrowRightIcon,
  BagIcon,
  ChevronDownIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  CloseIcon,
  GiftIcon,
  HandshakeIcon,
  InstagramIcon,
  MenuIcon,
  MinusIcon,
  PlusIcon,
  SearchIcon,
  StarIcon,
  TikTokIcon,
  TruckIcon,
  UserIcon,
  XSocialIcon,
} from './Icons';

const NAV_LINKS = [
  { label: 'Shop', href: '/shop-list', chevron: true },
  { label: 'Best Sellers', href: '/shop-list' },
  { label: 'About', href: '/about-us' },
  { label: 'Contact', href: '/contact-us-1' },
];

const FILTERS = ['Best Sellers', 'New Arrivals', 'Limited Edition', 'Accessories'];

const CATEGORY_FALLBACK = ['Bucket Bags', 'Flap Bags', 'Shoulder Bags', 'Crossbody Bags', 'Shopper & Tote'];
const CATEGORY_IMAGES = [
  '/home/cat-bucket.jpg',
  '/home/cat-flap.jpg',
  '/home/cat-shoulder.jpg',
  '/home/cat-crossbody.jpg',
  '/home/cat-shopper.jpg',
];

const GRID_IMAGES = ['/home/prod-elan.jpg', '/home/prod-marais.jpg', '/home/prod-noire.jpg', '/home/prod-lumiere.jpg', '/home/prod-aveline.jpg'];

const SIZES = ['Small', 'Medium', 'Large'];
const COLOR_SWATCHES = ['/home/prod-elan.jpg', '/home/spotlight-model.jpg', '/home/cat-flap.jpg', '/home/cat-shoulder.jpg'];

const TESTIMONIALS = [
  {
    quote:
      '“The Lumière is everything I was looking for — beautifully crafted, lightweight, versatile enough for both work and weekends. It’s become my everyday essential.”',
    name: 'Rosella Milly',
    thumb: '/home/testimonial-thumb.jpg',
  },
  {
    quote:
      '“From the stitching to the hardware, every detail feels intentional. Two years in and mine still looks brand new.”',
    name: 'Amara Whitfield',
    thumb: '/home/prod-marais.jpg',
  },
  {
    quote:
      '“Customer care shipped a replacement strap within days. Rare to see that kind of service paired with this kind of craftsmanship.”',
    name: 'Delphine Cross',
    thumb: '/home/spotlight-detail-1.jpg',
  },
];

const COMMITMENTS = [
  {
    icon: GiftIcon,
    title: 'Premium Craftsmanship',
    text: 'Handmade with meticulous attention to detail using premium materials.',
  },
  {
    icon: TruckIcon,
    title: 'Free Worldwide Shipping',
    text: 'Complimentary shipping on every order with secure packaging.',
  },
  {
    icon: HandshakeIcon,
    title: 'Secure Payment',
    text: 'Multiple trusted payment methods with protected transactions.',
  },
];

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

function money(product: { price_from: string | null; price_to: string | null } | null | undefined) {
  if (!product) return '';
  return formatPriceRange(product.price_from, product.price_to, STOREFRONT_CURRENCY);
}

export default function HomeClient({
  products,
  spotlightProduct,
}: {
  products: ProductSummaryStorefront[];
  spotlightProduct: ProductStorefront | null;
}) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [heroThumb, setHeroThumb] = useState(0);
  const [activeFilter, setActiveFilter] = useState(FILTERS[0]);
  const [size, setSize] = useState('Medium');
  const [color, setColor] = useState(0);
  const [qty, setQty] = useState(1);
  const [testiIndex, setTestiIndex] = useState(0);

  const heroThumbs = ['/home/hero-thumb-1.jpg', '/home/hero-thumb-2.jpg', '/home/hero-thumb-3.jpg'];
  const heroProduct = products[0];
  const gridProducts = products.slice(0, 5);
  const signatureProducts = products.slice(0, 4);

  // A styled "shop by silhouette" strip -- decorative wayfinding, not bound
  // to the live category taxonomy, so its imagery always matches its label.
  const strip = CATEGORY_FALLBACK.map((label, i) => ({
    label,
    image: CATEGORY_IMAGES[i],
  }));

  const spotlightImages = spotlightProduct?.images?.length
    ? spotlightProduct.images.slice(0, 3).map(img => img.url)
    : [];
  const spotlightMainImage = spotlightImages[0] ?? '/home/spotlight-model.jpg';
  const spotlightDetail1 = spotlightImages[1] ?? spotlightImages[0] ?? '/home/spotlight-detail-1.jpg';
  const spotlightDetail2 = spotlightImages[2] ?? spotlightImages[0] ?? '/home/spotlight-detail-2.jpg';

  const testimonial = TESTIMONIALS[testiIndex];

  return (
    <div className={styles.page}>
      {/* ---------------------------------- Header ---------------------------------- */}
      <header className={styles.header}>
        <div className={`${styles.container} ${styles.headerInner}`}>
          <nav aria-label="Primary">
            <ul className={styles.nav}>
              {NAV_LINKS.map(link => (
                <li key={link.label}>
                  <Link href={link.href}>
                    {link.label}
                    {link.chevron && <ChevronDownIcon size={12} />}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          <Link href="/" className={styles.logo}>
            AVERA
          </Link>

          <div className={styles.headerRight}>
            <Link href="/search-result" className={styles.headerIconBtn} aria-label="Search">
              <SearchIcon />
            </Link>
            <Link href="/signin" className={styles.headerIconBtn} aria-label="Account">
              <UserIcon />
            </Link>
            <Link href="/cart-items" className={styles.cartPill}>
              <span>My Cart</span>
              <BagIcon />
            </Link>
            <button
              type="button"
              className={styles.menuBtn}
              aria-label="Toggle menu"
              onClick={() => setMobileNavOpen(v => !v)}
            >
              {mobileNavOpen ? <CloseIcon /> : <MenuIcon />}
            </button>
          </div>
        </div>

        <div className={`${styles.container} ${styles.mobileNav} ${mobileNavOpen ? styles.open : ''}`}>
          {NAV_LINKS.map(link => (
            <Link key={link.label} href={link.href} onClick={() => setMobileNavOpen(false)}>
              {link.label}
            </Link>
          ))}
        </div>
      </header>

      {/* ---------------------------------- Hero ---------------------------------- */}
      <section className={styles.hero}>
        <div className={styles.heroWatermark}>LUMIÈRE AVERA</div>
        <div className={`${styles.container} ${styles.heroGrid}`}>
          <div className={styles.heroCopy}>
            <span className={styles.eyebrow}>New Arrival</span>
            <h1 className={styles.heroTitle}>The Art of Everyday Luxury</h1>
            <p className={styles.heroDesc}>
              Discover the signature Lumière bag, thoughtfully designed with premium materials and enduring
              style.
            </p>
            <Link href={heroProduct ? `/single-product/${heroProduct.id}` : '/shop-list'} className={styles.pill}>
              Explore Collection
              <span className={styles.pillIcon}>
                <ArrowRightIcon size={15} />
              </span>
            </Link>
          </div>

          <div className={styles.heroImageWrap}>
            <Image
              src="/home/hero-model.jpg"
              alt="Model carrying the signature Lumière tote bag"
              width={800}
              height={960}
              className={styles.heroImage}
              priority
            />
          </div>

          <div className={styles.heroSide}>
            {heroThumbs.map((src, i) => (
              <button
                key={src}
                type="button"
                className={`${styles.heroThumb} ${i === heroThumb ? styles.active : ''}`}
                onClick={() => setHeroThumb(i)}
                aria-label={`View angle ${i + 1}`}
              >
                <img src={src} alt="" />
              </button>
            ))}
            <div className={styles.heroCounter}>
              <button
                type="button"
                className={styles.btnCircle}
                onClick={() => setHeroThumb(v => Math.max(0, v - 1))}
                disabled={heroThumb === 0}
                aria-label="Previous"
              >
                <ChevronLeftIcon size={14} />
              </button>
              <span>0{heroThumb + 1}/03</span>
              <button
                type="button"
                className={styles.btnCircle}
                onClick={() => setHeroThumb(v => Math.min(2, v + 1))}
                disabled={heroThumb === 2}
                aria-label="Next"
              >
                <ChevronRightIcon size={14} />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------------------------- Signature pieces ---------------------------------- */}
      <section className={styles.section}>
        <div className={styles.container}>
          <div className={styles.sectionHead}>
            <div>
              <span className={styles.eyebrow}>Featured</span>
              <h2 className={styles.h2}>Our Signature Pieces</h2>
            </div>
            <div className={styles.filterRow}>
              {FILTERS.map(f => (
                <button
                  key={f}
                  type="button"
                  className={`${styles.filterPill} ${activeFilter === f ? styles.active : ''}`}
                  onClick={() => setActiveFilter(f)}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          {signatureProducts.length > 0 ? (
            <div className={styles.productGrid}>
              {signatureProducts.map(product => (
                <Link key={product.id} href={`/single-product/${product.id}`} className={styles.productCard}>
                  <div className={styles.productMedia}>
                    {product.primary_image ? (
                      <Image
                        src={product.primary_image.url}
                        alt={product.primary_image.alt_text ?? product.name}
                        width={480}
                        height={520}
                      />
                    ) : (
                      <div className={styles.productMediaEmpty}>No image yet</div>
                    )}
                  </div>
                  <p className={styles.productName}>{product.name}</p>
                  <p className={styles.productPrice}>{money(product)}</p>
                </Link>
              ))}
            </div>
          ) : (
            <p className={styles.productPrice}>New pieces are on their way — check back soon.</p>
          )}
        </div>
      </section>

      {/* ---------------------------------- Category price grid ---------------------------------- */}
      <section className={styles.section}>
        <div className={styles.container}>
          <div className={styles.sectionHead}>
            <div>
              <span className={styles.eyebrow}>Our Collection</span>
              <h2 className={styles.h2}>Shop by Category</h2>
            </div>
          </div>

          <div className={styles.priceCardGrid}>
            <div className={styles.introCard}>
              <h3 className={styles.introTitle}>Crafted to Be Carried</h3>
              <p className={styles.introText}>
                Each design reflects our commitment to timeless style, exceptional craftsmanship, and everyday
                functionality.
              </p>
              <Link href="/shop-list" className={styles.pill}>
                Shop Now
                <span className={styles.pillIcon}>
                  <ArrowRightIcon size={15} />
                </span>
              </Link>
            </div>

            {gridProducts.map((product, i) => (
              <Link key={product.id} href={`/single-product/${product.id}`} className={styles.priceCard}>
                <div className={styles.priceMedia}>
                  <img src={product.primary_image?.url ?? GRID_IMAGES[i % GRID_IMAGES.length]} alt={product.name} />
                </div>
                <div className={styles.priceRow}>
                  <span className={styles.priceName}>{product.name}</span>
                  <span className={styles.priceValue}>{money(product)}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------------------------- Spotlight ---------------------------------- */}
      <section className={styles.section}>
        <div className={styles.container}>
          <div className={styles.spotlightHead}>
            <span className={styles.eyebrow}>New Collection</span>
            <h2 className={styles.h2}>Designed to Last Beyond Trends</h2>
            <hr className={styles.spotlightRule} />
          </div>

          <div className={styles.spotlightGrid}>
            <div className={styles.spotlightModel}>
              <img src={spotlightMainImage} alt={spotlightProduct?.name ?? 'Featured piece'} />
            </div>

            <div className={styles.spotlightDetails}>
              <div className={styles.spotlightDetail}>
                <img src={spotlightDetail1} alt="" />
              </div>
              <div className={styles.spotlightDetail}>
                <img src={spotlightDetail2} alt="" />
              </div>
            </div>

            <div className={styles.spotlightInfo}>
              <p className={styles.spotlightCategory}>{spotlightProduct?.category.name ?? 'Featured Piece'}</p>
              <h3 className={styles.spotlightTitle}>{spotlightProduct?.name ?? 'The Signature Piece'}</h3>
              <p className={styles.spotlightPrice}>{spotlightProduct ? money(spotlightProduct) : '—'}</p>

              <div className={styles.optionRow}>
                <span className={styles.optionLabel}>Size: {size}</span>
                <span className={styles.sizeGuide}>Size Guide</span>
              </div>
              <div className={styles.sizeRow}>
                {SIZES.map(s => (
                  <button
                    key={s}
                    type="button"
                    className={`${styles.sizeBtn} ${size === s ? styles.active : ''}`}
                    onClick={() => setSize(s)}
                  >
                    {s.slice(0, 1).toUpperCase() + s.slice(1).toLowerCase()}
                  </button>
                ))}
              </div>

              <div className={styles.optionRow}>
                <span className={styles.optionLabel}>Color: Beige</span>
              </div>
              <div className={styles.colorRow}>
                {COLOR_SWATCHES.map((src, i) => (
                  <button
                    key={src + i}
                    type="button"
                    className={`${styles.colorSwatch} ${color === i ? styles.active : ''}`}
                    onClick={() => setColor(i)}
                    aria-label={`Color option ${i + 1}`}
                  >
                    <img src={src} alt="" />
                  </button>
                ))}
              </div>

              <div className={styles.buyRow}>
                <div className={styles.qtyStepper}>
                  <button type="button" onClick={() => setQty(v => Math.max(1, v - 1))} aria-label="Decrease quantity">
                    <MinusIcon />
                  </button>
                  <span>{qty}</span>
                  <button type="button" onClick={() => setQty(v => v + 1)} aria-label="Increase quantity">
                    <PlusIcon />
                  </button>
                </div>
                <Link href={spotlightProduct ? `/single-product/${spotlightProduct.id}` : '/shop-list'} className={styles.addToCartBtn}>
                  <BagIcon size={15} />
                  Add to Cart
                </Link>
              </div>
              <Link href={spotlightProduct ? `/single-product/${spotlightProduct.id}` : '/shop-list'} className={styles.buyItNowBtn}>
                Buy It Now
                <ArrowRightIcon size={15} />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------------------------- Category strip ---------------------------------- */}
      <section className={styles.sectionTight}>
        <div className={styles.container}>
          <div className={styles.catStrip}>
            {strip.map(cat => (
              <Link key={cat.label} href="/shop-list" className={styles.catCard}>
                <div className={styles.catImage}>
                  <img src={cat.image} alt={cat.label} />
                </div>
                <span className={styles.catLabel}>{cat.label}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------------------------- Testimonials ---------------------------------- */}
      <section className={styles.section}>
        <div className={styles.container}>
          <span className={styles.eyebrow}>Testimonial</span>
          <h2 className={styles.h2}>What Our Customers Say</h2>

          <div className={styles.testiTop}>
            <div className={styles.testiSub}>
              <span>Loved by Women Around the World</span>
              <div className={styles.testiRule} />
            </div>
            <div className={styles.testiArrows}>
              <button
                type="button"
                className={styles.btnCircle}
                onClick={() => setTestiIndex(v => (v - 1 + TESTIMONIALS.length) % TESTIMONIALS.length)}
                aria-label="Previous testimonial"
              >
                <ChevronLeftIcon size={14} />
              </button>
              <button
                type="button"
                className={styles.btnCircleDark}
                onClick={() => setTestiIndex(v => (v + 1) % TESTIMONIALS.length)}
                aria-label="Next testimonial"
              >
                <ChevronRightIcon size={14} />
              </button>
            </div>
          </div>

          <div className={styles.testiGrid}>
            <div className={styles.testiCard}>
              <div className={styles.testiThumb}>
                <img src={testimonial.thumb} alt={testimonial.name} />
              </div>
              <div className={styles.stars}>
                {Array.from({ length: 5 }).map((_, i) => (
                  <StarIcon key={i} />
                ))}
              </div>
              <p className={styles.testiQuote}>{testimonial.quote}</p>
              <p className={styles.testiName}>{testimonial.name}</p>
            </div>

            <div className={styles.testiHero}>
              <img src="/home/testimonial-hero.jpg" alt="Customer wearing an Avera woven shoulder bag" />
              <div className={styles.testiBadge}>
                <span className={styles.testiBadgeNum}>15K+</span>
                <span className={styles.testiBadgeText}>
                  Satisfied
                  <br />
                  Customers
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------------------------- Commitment ---------------------------------- */}
      <section className={`${styles.section} ${styles.commitment}`}>
        <div className={styles.container}>
          <div className={styles.commitmentHead}>
            <span className={styles.eyebrow}>Our Commitment</span>
            <h2 className={styles.h2}>Luxury Beyond the Product</h2>
          </div>

          <div className={styles.commitGrid}>
            {COMMITMENTS.map(item => (
              <div key={item.title} className={styles.commitItem}>
                <div className={styles.commitIcon}>
                  <item.icon />
                </div>
                <h3 className={styles.commitTitle}>{item.title}</h3>
                <p className={styles.commitText}>{item.text}</p>
              </div>
            ))}
          </div>

          <div className={styles.commitStrip}>
            <div className={styles.commitStripImg}>
              <img src="/home/life-1.jpg" alt="" />
            </div>
            <div className={styles.commitStripImg}>
              <img src="/home/life-2.jpg" alt="" />
            </div>
            <div className={styles.commitStripImg}>
              <img src="/home/life-3.jpg" alt="" />
            </div>
          </div>
        </div>
      </section>

      {/* ---------------------------------- CTA ---------------------------------- */}
      <div className={styles.ctaWrap}>
        <Link href="/shop-list" className={styles.pill}>
          Shop Now
          <span className={styles.pillIcon}>
            <ArrowRightIcon size={15} />
          </span>
        </Link>
      </div>

      {/* ---------------------------------- Footer ---------------------------------- */}
      <footer className={styles.footer}>
        <div className={styles.container}>
          <div className={styles.footerTop}>
            <div>
              <p className={styles.footerBrand}>AVERA</p>
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
            <img src="/home/footer-showroom.jpg" alt="Avera flagship showroom" />
          </div>

          <div className={styles.footerBottom}>
            <span>© {new Date().getFullYear()} Avera. All rights reserved.</span>
            <span>Crafted with care.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
