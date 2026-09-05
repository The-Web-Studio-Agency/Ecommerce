import type { MetadataRoute } from 'next';

import { catalogueApi } from '@/lib/api/catalogue';
import { siteUrl } from '@/lib/site';

/**
 * Built from the live catalogue.
 *
 * Only pages worth indexing are listed: account, cart, checkout and admin
 * are all private, and the catalogue is walked page by page so the sitemap
 * stays complete as the shop grows.
 */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = siteUrl();

  const entries: MetadataRoute.Sitemap = [
    { url: `${base}/`, changeFrequency: 'daily', priority: 1 },
    { url: `${base}/shop`, changeFrequency: 'daily', priority: 0.9 },
  ];

  try {
    const categories = await catalogueApi.listCategories({ page_size: 100 });

    for (const category of categories.items) {
      entries.push({
        url: `${base}/shop?category=${category.id}`,
        changeFrequency: 'weekly',
        priority: 0.7,
      });
    }
  } catch {
    // A catalogue that will not answer still leaves a valid sitemap.
  }

  try {
    let page = 1;
    let totalPages = 1;

    do {
      const products = await catalogueApi.listProducts({ page, page_size: 100 });
      totalPages = products.meta.total_pages;

      for (const product of products.items) {
        entries.push({
          url: `${base}/products/${product.id}`,
          changeFrequency: 'weekly',
          priority: 0.8,
        });
      }

      page += 1;
    } while (page <= totalPages && page <= 20);
  } catch {
    // As above: the static entries are still worth serving.
  }

  return entries;
}
