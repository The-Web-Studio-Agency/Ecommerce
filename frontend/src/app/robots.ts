import type { MetadataRoute } from 'next';

import { siteUrl } from '@/lib/site';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      // Nothing private or personal is worth crawling.
      disallow: ['/account', '/orders', '/cart', '/checkout', '/wishlist', '/admin', '/signin'],
    },
    sitemap: `${siteUrl()}/sitemap.xml`,
  };
}
