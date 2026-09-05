import type { Metadata } from 'next';

import Filters from '@/components/shop/Filters';
import Pager from '@/components/shop/Pager';
import ProductCard, { ProductGrid } from '@/components/product/ProductCard';
import ButtonLink from '@/components/ui/ButtonLink';
import { Container, Section } from '@/components/ui/Layout';
import { EmptyState, ErrorState } from '@/components/ui/States';
import { ApiError } from '@/lib/api/errors';
import { catalogueApi } from '@/lib/api/catalogue';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import type { ProductSort } from '@/types/catalogue';

export const metadata: Metadata = {
  title: 'Shop',
  description: 'The full Zeen collection: clothing, bags, footwear and jewellery.',
};

const SORTS: ProductSort[] = ['newest', 'name_asc', 'name_desc', 'price_low', 'price_high'];

const PAGE_SIZE = 12;

/** Only values the backend accepts get through; anything else is a 422. */
function parseSort(value: string | undefined): ProductSort {
  return SORTS.includes(value as ProductSort) ? (value as ProductSort) : 'newest';
}

function parsePage(value: string | undefined): number {
  const page = Number.parseInt(value ?? '1', 10);
  return Number.isFinite(page) && page > 0 ? page : 1;
}

function parsePrice(value: string | undefined): string | undefined {
  if (!value) return undefined;
  const price = Number(value);
  return Number.isFinite(price) && price >= 0 ? String(price) : undefined;
}

export default async function ShopPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const query = await searchParams;

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value) params.set(key, value);
  }

  const categories = await catalogueApi.listCategories({ page_size: 20 }).catch(() => null);

  let products;
  let failure: ApiError | null = null;

  try {
    // Filtering, sorting and paging all happen in the API. The browser
    // never receives more than the page it is showing.
    products = await catalogueApi.listProducts({
      page: parsePage(query.page),
      page_size: PAGE_SIZE,
      category_id: query.category,
      search: query.q,
      sort: parseSort(query.sort),
      min_price: parsePrice(query.min_price),
      max_price: parsePrice(query.max_price),
    });
  } catch (error) {
    if (error instanceof ApiError) failure = error;
    else throw error;
  }

  return (
    <main>
      <Section>
        <Container>
          <h1>Shop</h1>

          <div style={{ marginTop: 'var(--space-5)' }}>
            <Filters categories={categories?.items ?? []} total={products?.meta.total_items ?? 0} />
          </div>

          {failure ? (
            <ErrorState
              title="Could not load the collection"
              body="The catalogue did not respond. Try again in a moment."
              requestId={failure.requestId}
            />
          ) : products && products.items.length > 0 ? (
            <>
              <ProductGrid>
                {products.items.map((product, index) => (
                  <ProductCard
                    key={product.id}
                    product={product}
                    currency={STOREFRONT_CURRENCY}
                    priority={index < 4}
                  />
                ))}
              </ProductGrid>

              <Pager meta={products.meta} params={params} />
            </>
          ) : (
            <EmptyState
              title="Nothing matches those filters"
              body="Try a broader search, or browse the whole collection."
              action={<ButtonLink href="/shop">Clear filters</ButtonLink>}
            />
          )}
        </Container>
      </Section>
    </main>
  );
}
