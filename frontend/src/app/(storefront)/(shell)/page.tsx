import Image from 'next/image';
import Link from 'next/link';

import CategoryTiles from '@/components/layout/CategoryTiles';
import SectionHead from '@/components/layout/SectionHead';
import ProductCard, { ProductGrid } from '@/components/product/ProductCard';
import ButtonLink from '@/components/ui/ButtonLink';
import { Container, Section } from '@/components/ui/Layout';
import { EmptyState } from '@/components/ui/States';
import { catalogueApi } from '@/lib/api/catalogue';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatPriceRange } from '@/lib/format';

import heroStyles from '@/components/layout/Hero.module.css';

/**
 * Everything here is the real catalogue. Each section answers a different
 * question -- what is this shop, what does it sell, what is new -- so none
 * of them exist only to make the page longer.
 */
export default async function HomePage() {
  const [featured, newest, categories] = await Promise.all([
    catalogueApi.listProducts({ featured: true, page_size: 8 }).catch(() => null),
    catalogueApi.listProducts({ sort: 'newest', page_size: 8 }).catch(() => null),
    catalogueApi.listCategories({ page_size: 8 }).catch(() => null),
  ]);

  // A featured shelf is the intent; if nothing is flagged, the newest
  // arrivals stand in rather than leaving a hole.
  const shelf = featured?.items.length ? featured.items : (newest?.items ?? []);
  const lead = shelf[0] ?? null;
  const currency = STOREFRONT_CURRENCY;

  return (
    <main>
      <section className={heroStyles.hero}>
        <Container>
          <div className={heroStyles.inner}>
            <div>
              <h1 className={heroStyles.title}>
                Clothes that keep <em>turning up</em> in your week.
              </h1>

              <p className={heroStyles.lede}>
                Considered fabrics, quiet shapes and a small collection that earns its place. Cash on
                delivery across India.
              </p>

              <div className={heroStyles.actions}>
                <ButtonLink href="/shop" size="lg">
                  Shop the collection
                </ButtonLink>
              </div>
            </div>

            {lead?.primary_image && (
              <Link href={`/products/${lead.id}`} className={heroStyles.figure}>
                <Image
                  src={lead.primary_image.url}
                  alt={lead.primary_image.alt_text ?? lead.name}
                  fill
                  className={heroStyles.figureImage}
                  sizes="(min-width: 56rem) 40vw, 100vw"
                  priority
                />

                <span className={heroStyles.caption}>
                  <span className={heroStyles.captionName}>{lead.name}</span>
                  <br />
                  <span className={heroStyles.captionPrice} data-numeric>
                    {formatPriceRange(lead.price_from, lead.price_to, currency)}
                  </span>
                </span>
              </Link>
            )}
          </div>
        </Container>
      </section>

      {categories && categories.items.length > 0 && (
        <Section>
          <Container>
            <SectionHead title="Shop by category" href="/shop" linkLabel="All products" />
            <CategoryTiles categories={categories.items} />
          </Container>
        </Section>
      )}

      <Section>
        <Container>
          <SectionHead
            title={featured?.items.length ? 'Featured' : 'New arrivals'}
            href="/shop"
            linkLabel="See everything"
          />

          {shelf.length > 0 ? (
            <ProductGrid>
              {shelf.map((product) => (
                <ProductCard key={product.id} product={product} currency={currency} />
              ))}
            </ProductGrid>
          ) : (
            <EmptyState
              title="Nothing to show yet"
              body="The collection is not published. Check back shortly."
            />
          )}
        </Container>
      </Section>
    </main>
  );
}
