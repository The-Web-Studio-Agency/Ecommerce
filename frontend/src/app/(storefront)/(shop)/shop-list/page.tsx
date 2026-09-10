import Link from 'next/link';

import LuxeFooter from '@/components/luxe/LuxeFooter';
import LuxeHeader from '@/components/luxe/LuxeHeader';
import { catalogueApi } from '@/lib/api/catalogue';
import { searchApi } from '@/lib/api/search';
import type { ProductSort, ProductSummaryStorefront } from '@/types/catalogue';
import type { SearchSort } from '@/types/search';

import homeStyles from '../../(home)/home/_components/luxe/Home.module.css';
import listingStyles from './_components/luxe/Listing.module.css';
import ListingControls, { type ListingSort } from './_components/luxe/ListingControls';
import MobileBottomNav from '@/components/luxe/MobileBottomNav';
import ProductCard from './_components/luxe/ProductCard';

export const metadata = {
  title: 'Shop All | Zeen',
  description: 'Browse the Zeen collection of kurtas and tops.',
};

const PAGE_SIZE = 12;
/** The catalogue also carries a handful of empty/QA categories left over from
 *  backend testing (Bags, Accessories, "QA Category", ...). The storefront
 *  only actually sells kurtas and tops, so the listing is scoped to those. */
const ALLOWED_CATEGORY_NAMES = ['Women Kurtas', 'Tops'];
/** Seed/test rows that sit inside an otherwise-real category and don't
 *  belong in the storefront. */
const EXCLUDED_PRODUCT_NAMES = new Set(['Ira Poplin Shirt']);
/** A single backend page comfortably covers the whole (small) real catalogue,
 *  so filtering/pagination can be finished off in the route itself rather
 *  than needing a multi-category query the API doesn't offer. */
const CATALOGUE_FETCH_SIZE = 100;

const SORTS: ListingSort[] = [
  'newest',
  'name_asc',
  'name_desc',
  'price_low',
  'price_high',
  'rating_desc',
  'popularity',
];

function isSort(value: string | undefined): value is ListingSort {
  return !!value && (SORTS as string[]).includes(value);
}

/** Sorts only the real `ProductSort` values map onto the primary listing
 *  endpoint. Rating and popularity need the search endpoint instead (see
 *  `usesVariantData` below). */
function isProductSort(value: ListingSort): value is ProductSort {
  return value !== 'rating_desc' && value !== 'popularity';
}

/**
 * `rating_desc`/`popularity` and color/size filters only exist on
 * `/storefront/search-products` -- the primary listing endpoint has no
 * rating, popularity, color or size at all. That endpoint requires an
 * ACTIVE variant per product to return a row, so today (no catalogue
 * variants populated yet) it returns nothing for the real categories. The
 * controls stay live regardless -- real backend calls, real (currently
 * empty) data -- rather than being hidden until the catalogue catches up.
 */
function usesVariantData(sort: ListingSort, color: string, size: string): boolean {
  return sort === 'rating_desc' || sort === 'popularity' || !!color || !!size;
}

function toSearchSort(sort: ListingSort): SearchSort {
  if (sort === 'price_low') return 'price';
  if (sort === 'price_high') return '-price';
  if (sort === 'popularity') return 'RECOMMENDED';
  // 'newest' and 'rating_desc' both fetch newest-first; rating_desc is
  // re-sorted client-side afterwards since the backend has no rating order.
  return 'NEWEST';
}

/** Windowed page numbers around the current page, e.g. 1 … 4 5 [6] 7 8 … 12. */
function pageWindow(current: number, total: number): (number | 'gap')[] {
  const pages = new Set<number>([1, total, current, current - 1, current + 1]);
  const sorted = [...pages].filter(p => p >= 1 && p <= total).sort((a, b) => a - b);

  const out: (number | 'gap')[] = [];
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) out.push('gap');
    out.push(sorted[i]);
  }
  return out;
}

function isReal(allowedIds: Set<string>, product: { category_id: string; name: string }): boolean {
  return allowedIds.has(product.category_id) && !EXCLUDED_PRODUCT_NAMES.has(product.name);
}

export default async function ShopListPage({
  searchParams,
}: {
  searchParams: Promise<{
    category?: string;
    q?: string;
    sort?: string;
    page?: string;
    brand?: string;
    min_price?: string;
    max_price?: string;
    color?: string;
    product_size?: string;
  }>;
}) {
  const {
    category,
    q = '',
    sort: sortParam,
    page: pageParam,
    brand: brandParam = '',
    min_price: minPriceParam = '',
    max_price: maxPriceParam = '',
    color: colorParam = '',
    product_size: sizeParam = '',
  } = await searchParams;
  const sort: ListingSort = isSort(sortParam) ? sortParam : 'newest';
  const page = Math.max(1, Number(pageParam ?? 1) || 1);
  const search = q.trim();
  const brand = brandParam.trim();
  const minPrice = minPriceParam.trim();
  const maxPrice = maxPriceParam.trim();
  const color = colorParam.trim();
  const size = sizeParam.trim();

  const categoriesPage = await catalogueApi.listCategories({ page_size: 50 });
  const categories = categoriesPage.items.filter(c => ALLOWED_CATEGORY_NAMES.includes(c.name));
  const allowedIds = new Set(categories.map(c => c.id));
  const categoryById = new Map(categories.map(c => [c.id, c.name]));

  // A category from the URL only applies if it's one of the two the store
  // actually sells -- a stale or tampered link just falls back to "All".
  const activeCategory = category && allowedIds.has(category) ? category : undefined;

  // The brand facet reflects the real, full catalogue for the current
  // category scope (ignoring search/brand/price), so the dropdown always
  // offers every brand that's actually there -- not just what survived the
  // shopper's current filters.
  const facetSource = await catalogueApi.listProducts({
    page_size: CATALOGUE_FETCH_SIZE,
    category_id: activeCategory,
  });
  // Color/Size only exist as variant options, which only the search
  // endpoint exposes -- fetched unfiltered (besides category) so the
  // dropdowns always reflect what's really there, same pattern as brands
  // above. Real call, real (currently empty) data; see usesVariantData.
  const variantFacetSource = await searchApi.searchProducts({
    category_id: activeCategory,
    size: CATALOGUE_FETCH_SIZE,
  });
  const realVariantItems = variantFacetSource.items.filter(p => isReal(allowedIds, p));
  const colors = [
    ...new Set(realVariantItems.flatMap(p => p.variants.map(v => v.options.Color).filter((c): c is string => !!c))),
  ].sort((a, b) => a.localeCompare(b));
  const sizes = [
    ...new Set(realVariantItems.flatMap(p => p.variants.map(v => v.options.Size).filter((s): s is string => !!s))),
  ].sort((a, b) => a.localeCompare(b));

  type ListedProduct = ProductSummaryStorefront & { rating?: number | null; colors?: string[] };

  // Per-product color swatches, sourced the same way as the Color filter's
  // option list above -- real variant data from the search endpoint,
  // unfiltered by the shopper's current sort/filters so a card's swatches
  // don't change just because a filter is applied.
  const colorsByProductId = new Map<string, string[]>(
    realVariantItems
      .map((p): [string, string[]] => [
        p.id,
        [...new Set(p.variants.map(v => v.options.Color).filter((c): c is string => !!c))],
      ])
      .filter(([, cs]) => cs.length > 0),
  );

  let products: ListedProduct[];
  let total_items: number;

  if (usesVariantData(sort, color, size)) {
    // Rating/popularity sort or a color/size filter -- none of that exists
    // on the primary listing endpoint, so this branch asks the search
    // endpoint instead. It carries no image/stock, so those are stitched
    // back in from `facetSource` (already fetched, same tenant/category,
    // real data either way) by product id.
    const discovery = await searchApi.searchProducts({
      category_id: activeCategory,
      q: search || undefined,
      brand: brand || undefined,
      min_price: minPrice || undefined,
      max_price: maxPrice || undefined,
      color: color || undefined,
      product_size: size || undefined,
      sort: toSearchSort(sort),
      size: CATALOGUE_FETCH_SIZE,
    });
    let items = discovery.items.filter(p => isReal(allowedIds, p));
    if (sort === 'rating_desc') {
      items = [...items].sort((a, b) => (b.rating ?? -1) - (a.rating ?? -1));
    }
    const summaryById = new Map(facetSource.items.map(p => [p.id, p]));
    const merged = items
      .map((item): ListedProduct | null => {
        const summary = summaryById.get(item.id);
        return summary ? { ...summary, rating: item.rating } : null;
      })
      .filter((p): p is ListedProduct => p !== null);

    total_items = merged.length;
    products = merged.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  } else {
    // The API has no multi-category filter, so "All" fetches the (small)
    // real catalogue -- search/sort/brand/price all applied by the backend
    // -- and the route itself drops anything outside the two allowed
    // categories and the known-excluded rows before paginating what's left.
    const resultsPage = await catalogueApi.listProducts({
      page_size: CATALOGUE_FETCH_SIZE,
      category_id: activeCategory,
      search: search || undefined,
      sort: isProductSort(sort) ? sort : 'newest',
      brand: brand || undefined,
      min_price: minPrice || undefined,
      max_price: maxPrice || undefined,
    });
    const filtered = resultsPage.items.filter(p => isReal(allowedIds, p));
    total_items = filtered.length;
    products = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  }

  products = products.map(p => ({ ...p, colors: colorsByProductId.get(p.id) ?? [] }));

  const total_pages = Math.max(1, Math.ceil(total_items / PAGE_SIZE));

  const categoryName = activeCategory ? categoryById.get(activeCategory) : undefined;

  function hrefFor(next: Record<string, string | number | undefined>) {
    const params = new URLSearchParams();
    if (activeCategory) params.set('category', activeCategory);
    if (search) params.set('q', search);
    if (sort !== 'newest') params.set('sort', sort);
    if (brand) params.set('brand', brand);
    if (minPrice) params.set('min_price', minPrice);
    if (maxPrice) params.set('max_price', maxPrice);
    if (color) params.set('color', color);
    if (size) params.set('product_size', size);
    if (page > 1) params.set('page', String(page));
    for (const [key, value] of Object.entries(next)) {
      if (value === undefined) params.delete(key);
      else params.set(key, String(value));
    }
    const qs = params.toString();
    return qs ? `/shop-list?${qs}` : '/shop-list';
  }

  const hasFilters = !!(search || brand || minPrice || maxPrice || color || size || activeCategory);
  const subtitle = categoryName
    ? `Browse our ${categoryName} collection.`
    : 'Everyday and versatile wear, thoughtfully curated for every occasion.';

  return (
    <div className={homeStyles.page}>
      <LuxeHeader />

      <section className={listingStyles.banner}>
        <div className={homeStyles.container}>
          <p className={listingStyles.crumb}>
            <Link href="/">Home</Link>
            <span>/</span>
            <span aria-current="page">{categoryName ?? 'Shop'}</span>
          </p>
          <h1 className={homeStyles.h2}>{categoryName ?? 'Shop All'}</h1>
          <p className={listingStyles.subtitle}>{subtitle}</p>
        </div>
      </section>

      <section className={listingStyles.listingSection}>
        <div className={homeStyles.container}>
          <div className={listingStyles.toolbarRow}>
            <div className={listingStyles.chipRow}>
              <Link
                href={hrefFor({ category: undefined })}
                className={`${homeStyles.filterPill} ${!activeCategory ? homeStyles.active : ''}`}
              >
                All
              </Link>
              {categories.map(cat => (
                <Link
                  key={cat.id}
                  href={hrefFor({ category: cat.id })}
                  className={`${homeStyles.filterPill} ${activeCategory === cat.id ? homeStyles.active : ''}`}
                >
                  {cat.name}
                </Link>
              ))}
            </div>

            <div className={listingStyles.metaRow}>
              <p className={listingStyles.resultsCount}>
                {total_items === 0 ? 'No products found' : `${total_items} product${total_items === 1 ? '' : 's'}`}
              </p>
              <span className={listingStyles.metaDivider} aria-hidden="true" />
              <ListingControls
                sort={sort}
                minPrice={minPrice}
                maxPrice={maxPrice}
                color={color}
                colors={colors}
                size={size}
                sizes={sizes}
              />
            </div>
          </div>

          {products.length === 0 ? (
            <div className={listingStyles.emptyState}>
              <p>
                {hasFilters
                  ? 'No products matched these filters.'
                  : 'No products in this category yet.'}
              </p>
              <Link href="/shop-list" className={homeStyles.pillOutline}>
                Clear filters
              </Link>
            </div>
          ) : (
            <div className={listingStyles.grid}>
              {products.map(product => (
                <ProductCard key={product.id} product={product} colors={product.colors} />
              ))}
            </div>
          )}

          {total_pages > 1 && (
            <nav className={listingStyles.pagination} aria-label="Pagination">
              {page > 1 && (
                <Link href={hrefFor({ page: page - 1 })} className={homeStyles.btnCircle} aria-label="Previous page">
                  ←
                </Link>
              )}
              {pageWindow(page, total_pages).map((p, i) =>
                p === 'gap' ? (
                  <span key={`gap-${i}`} className={listingStyles.pageEllipsis}>
                    …
                  </span>
                ) : (
                  <Link
                    key={p}
                    href={hrefFor({ page: p })}
                    className={`${listingStyles.pageNum} ${p === page ? listingStyles.active : ''}`}
                    aria-current={p === page ? 'page' : undefined}
                  >
                    {p}
                  </Link>
                ),
              )}
              {page < total_pages && (
                <Link href={hrefFor({ page: page + 1 })} className={homeStyles.btnCircle} aria-label="Next page">
                  →
                </Link>
              )}
            </nav>
          )}
        </div>
      </section>

      <LuxeFooter />
      <MobileBottomNav />
    </div>
  );
}
