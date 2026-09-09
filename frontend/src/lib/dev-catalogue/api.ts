/**
 * ============================================================================
 * TEMPORARY DEV-ONLY CODE -- delete this whole `dev-catalogue` folder (and
 * its two call sites: the import + render line in shop-list/page.tsx) once
 * the real Admin panel ships.
 * ============================================================================
 *
 * Thin wrappers around the `/dev/catalogue/*` endpoints
 * (`backend/app/catalogue/dev_router.py`) -- a temporary, customer-usable
 * mirror of the real admin catalogue endpoints (`router.py`, untouched,
 * still admin/staff-only). No duplicate business logic backend-side: the
 * dev router calls the exact same Services this app's real Admin panel will
 * eventually call too.
 *
 * Kept separate from `src/lib/api/catalogue.ts` (the real storefront reads
 * that page uses today) so this can be deleted as one unit later without
 * touching production code.
 */

import { apiRequest, apiRequestPage } from '@/lib/api/client';
import type { Page, PageParams } from '@/types/api';
import type { CatalogueStatus, ProductGender } from '@/types/catalogue';

export interface DevCategory {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  status: CatalogueStatus;
}

export interface DevCategoryCreate {
  name: string;
  description?: string | null;
}

export interface DevProductImageCreate {
  url: string;
  alt_text?: string | null;
  sort_order?: number;
  is_primary?: boolean;
}

export interface DevProductImage extends DevProductImageCreate {
  id: string;
  tenant_id: string;
  product_id: string;
  sort_order: number;
  is_primary: boolean;
}

export interface DevProductOption {
  id: string;
  name: string;
  position: number;
}

export interface DevProduct {
  id: string;
  tenant_id: string;
  category_id: string;
  name: string;
  short_description: string | null;
  description: string | null;
  brand: string | null;
  status: CatalogueStatus;
  gender: ProductGender | null;
  is_featured: boolean;
  seo_title: string | null;
  seo_description: string | null;
  images: DevProductImage[];
  options: DevProductOption[];
}

export interface DevProductCreate {
  category_id: string;
  name: string;
  short_description?: string | null;
  description?: string | null;
  brand?: string | null;
  status?: CatalogueStatus;
  gender?: ProductGender | null;
  is_featured?: boolean;
  images: DevProductImageCreate[];
}

export interface DevVariantOptionValue {
  name: string;
  value: string;
}

export interface DevVariant {
  id: string;
  tenant_id: string;
  product_id: string;
  sku: string;
  name: string;
  price: string;
  status: CatalogueStatus;
  image_id: string | null;
  options: Record<string, string>;
}

export interface DevVariantCreate {
  sku: string;
  name: string;
  price: string;
  status?: CatalogueStatus;
  /** Must belong to the same product this variant is being created on. */
  image_id?: string | null;
  options?: DevVariantOptionValue[];
  initial_quantity?: number;
  low_stock_threshold?: number;
}

/**
 * The temporary `/dev/catalogue/*` endpoints -- any signed-in shopper, not
 * just admin/staff. See dev_router.py: this only exists outside production.
 */
export const devCatalogueApi = {
  listCategories(token: string, params: PageParams = {}): Promise<Page<DevCategory>> {
    return apiRequestPage<DevCategory>('/dev/catalogue/categories', {
      query: { ...params },
      token,
      cache: 'no-store',
    });
  },

  createCategory(token: string, data: DevCategoryCreate): Promise<DevCategory> {
    return apiRequest<DevCategory>('/dev/catalogue/categories', {
      method: 'POST',
      body: data,
      token,
      cache: 'no-store',
    });
  },

  listProducts(token: string, params: PageParams = {}): Promise<Page<DevProduct>> {
    return apiRequestPage<DevProduct>('/dev/catalogue/products', {
      query: { ...params, sort: 'name_asc' },
      token,
      cache: 'no-store',
    });
  },

  createProduct(token: string, data: DevProductCreate): Promise<DevProduct> {
    return apiRequest<DevProduct>('/dev/catalogue/products', {
      method: 'POST',
      body: data,
      token,
      cache: 'no-store',
    });
  },

  createVariant(token: string, productId: string, data: DevVariantCreate): Promise<DevVariant> {
    return apiRequest<DevVariant>(`/dev/catalogue/products/${productId}/variants`, {
      method: 'POST',
      body: data,
      token,
      cache: 'no-store',
    });
  },

  listProductImages(token: string, productId: string): Promise<DevProductImage[]> {
    return apiRequest<DevProductImage[]>(`/dev/catalogue/products/${productId}/images`, {
      token,
      cache: 'no-store',
    });
  },

  addProductImageByUrl(token: string, productId: string, data: DevProductImageCreate): Promise<DevProductImage> {
    return apiRequest<DevProductImage>(`/dev/catalogue/products/${productId}/images`, {
      method: 'POST',
      body: data,
      token,
      cache: 'no-store',
    });
  },

  /** A real file upload, multipart -- see the FormData passthrough in `lib/api/client.ts`. */
  uploadProductImage(
    token: string,
    productId: string,
    file: File,
    options: { altText?: string; sortOrder?: number; isPrimary?: boolean } = {},
  ): Promise<DevProductImage> {
    const formData = new FormData();
    formData.set('file', file);
    if (options.altText) formData.set('alt_text', options.altText);
    formData.set('sort_order', String(options.sortOrder ?? 0));
    formData.set('is_primary', String(!!options.isPrimary));

    return apiRequest<DevProductImage>(`/dev/catalogue/products/${productId}/images/upload`, {
      method: 'POST',
      body: formData,
      token,
      cache: 'no-store',
    });
  },
};
