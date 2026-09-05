import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';

import BuyBox from '@/components/product/BuyBox';
import Gallery from '@/components/product/Gallery';
import ProductCard, { ProductGrid } from '@/components/product/ProductCard';
import Reviews from '@/components/product/Reviews';
import SectionHead from '@/components/layout/SectionHead';
import { Container, Section } from '@/components/ui/Layout';
import { ApiError } from '@/lib/api/errors';
import { catalogueApi } from '@/lib/api/catalogue';
import { reviewApi } from '@/lib/api/reviews';
import { getCurrentUser } from '@/lib/auth/current-user';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { siteUrl } from '@/lib/site';
import { formatPriceRange } from '@/lib/format';

import styles from '@/components/product/ProductDetail.module.css';

async function loadProduct(id: string) {
  try {
    return await catalogueApi.getProduct(id);
  } catch (error) {
    if (error instanceof ApiError && error.isNotFound) return null;
    throw error;
  }
}

/** Metadata comes from the product's own SEO fields, never invented here. */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const product = await loadProduct(id);

  if (!product) return { title: 'Product not found' };

  const description =
    product.seo_description ?? product.short_description ?? product.description ?? undefined;

  // seo_title already carries the brand, so it bypasses the layout's
  // "%s | Zeen" template rather than being suffixed with it twice.
  const title = product.seo_title ? { absolute: product.seo_title } : product.name;

  return {
    title,
    description,
    alternates: { canonical: `/products/${product.id}` },
    openGraph: {
      title: product.seo_title ?? product.name,
      description,
      type: 'website',
      images: product.images[0] ? [{ url: product.images[0].url }] : undefined,
    },
    twitter: {
      card: 'summary_large_image',
      title: product.seo_title ?? product.name,
      description,
    },
  };
}

export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = await loadProduct(id);

  if (!product) notFound();

  const currency = STOREFRONT_CURRENCY;

  const [summary, reviews, related, user] = await Promise.all([
    reviewApi.summary(product.id).catch(() => null),
    reviewApi.listForProduct(product.id, { page_size: 5 }).catch(() => null),
    // There is no related-products endpoint, so siblings in the same
    // category stand in -- real data rather than an invented shelf.
    catalogueApi.listProducts({ category_id: product.category.id, page_size: 5 }).catch(() => null),
    getCurrentUser(),
  ]);

  const siblings = (related?.items ?? []).filter((item) => item.id !== product.id).slice(0, 4);

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.name,
    description: product.short_description ?? product.description ?? undefined,
    image: product.images.map((image) => image.url),
    brand: product.brand ? { '@type': 'Brand', name: product.brand } : undefined,
    offers: {
      '@type': 'AggregateOffer',
      priceCurrency: currency,
      lowPrice: product.price_from ?? undefined,
      highPrice: product.price_to ?? undefined,
      availability: product.in_stock
        ? 'https://schema.org/InStock'
        : 'https://schema.org/OutOfStock',
    },
    aggregateRating:
      summary && summary.total_reviews > 0
        ? {
            '@type': 'AggregateRating',
            ratingValue: summary.average_rating,
            reviewCount: summary.total_reviews,
          }
        : undefined,
  };

  const base = siteUrl();

  const breadcrumbs = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Shop', item: `${base}/shop` },
      {
        '@type': 'ListItem',
        position: 2,
        name: product.category.name,
        item: `${base}/shop?category=${product.category.id}`,
      },
      { '@type': 'ListItem', position: 3, name: product.name, item: `${base}/products/${product.id}` },
    ],
  };

  return (
    <main>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbs) }}
      />

      <Section>
        <Container>
          <p className={styles.crumbs}>
            <Link href="/shop">Shop</Link> / <Link href={`/shop?category=${product.category.id}`}>{product.category.name}</Link>
          </p>

          <div className={styles.layout}>
            <Gallery images={product.images} productName={product.name} />

            <div>
              <h1 className={styles.name}>{product.name}</h1>

              <p className={styles.price} data-numeric>
                {formatPriceRange(product.price_from, product.price_to, currency)}
              </p>

              {product.short_description && <p className={styles.lede}>{product.short_description}</p>}

              <div className={styles.buy}>
                <BuyBox
                  options={product.options}
                  variants={product.variants}
                  currency={currency}
                  isSignedIn={Boolean(user)}
                />
              </div>

              <div className={styles.details}>
                {product.description && (
                  <details className={styles.detail} open>
                    <summary className={styles.detailSummary}>Description</summary>
                    <div className={styles.detailBody}>{product.description}</div>
                  </details>
                )}

                <details className={styles.detail}>
                  <summary className={styles.detailSummary}>Details</summary>
                  <div className={styles.detailBody}>
                    <dl className={styles.specs}>
                      {product.brand && (
                        <>
                          <dt className={styles.specKey}>Brand</dt>
                          <dd>{product.brand}</dd>
                        </>
                      )}
                      <dt className={styles.specKey}>Category</dt>
                      <dd>{product.category.name}</dd>
                      <dt className={styles.specKey}>Reference</dt>
                      <dd>{product.variants[0]?.sku ?? '-'}</dd>
                    </dl>
                  </div>
                </details>

                <details className={styles.detail}>
                  <summary className={styles.detailSummary}>Delivery and returns</summary>
                  <div className={styles.detailBody}>
                    Cash on delivery across India. Contact us to arrange a return.
                  </div>
                </details>
              </div>
            </div>
          </div>
        </Container>
      </Section>

      <Section>
        <Container>
          <SectionHead title="Reviews" />
          <Reviews summary={summary} reviews={reviews?.items ?? []} />
        </Container>
      </Section>

      {siblings.length > 0 && (
        <Section>
          <Container>
            <SectionHead
              title={`More in ${product.category.name}`}
              href={`/shop?category=${product.category.id}`}
              linkLabel="See all"
            />

            <ProductGrid>
              {siblings.map((item) => (
                <ProductCard key={item.id} product={item} currency={currency} />
              ))}
            </ProductGrid>
          </Container>
        </Section>
      )}
    </main>
  );
}
