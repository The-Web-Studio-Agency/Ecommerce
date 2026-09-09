'use server';

/**
 * ============================================================================
 * TEMPORARY DEV-ONLY CODE -- see api.ts in this folder for the removal note.
 * ============================================================================
 *
 * Server Actions, one per form in DevCatalogueTools.tsx. Each:
 *  1. Refuses outright in a production build (belt-and-suspenders on top of
 *     the backend's own guard -- `dev_router.py` is never even registered
 *     when `settings.is_production`, so these calls 404 there regardless).
 *  2. Reads the *existing* httpOnly session cookie the same way every real
 *     authenticated call in this app does (`getAccessToken`, from
 *     `lib/auth/session.ts` -- nothing new, nothing weakened). Signed out,
 *     this gets exactly the same 401 a real customer-facing call would;
 *     unlike the real `/catalogue/*` admin endpoints, `/dev/catalogue/*`
 *     accepts *any* signed-in shopper, by design (see dev_router.py).
 *  3. Calls the temporary `/dev/catalogue/*` endpoints via `devCatalogueApi`.
 *  4. Revalidates the same cache tags the storefront read-path already uses
 *     (`categories`/`products`, see `lib/api/catalogue.ts`) so a newly
 *     created row shows up on this page without a hard refresh.
 */

import { revalidatePath, revalidateTag } from 'next/cache';

import { ApiError, ApiUnreachableError } from '@/lib/api/errors';
import { getAccessToken } from '@/lib/auth/session';
import {
  devCatalogueApi,
  type DevCategory,
  type DevProduct,
  type DevProductCreate,
  type DevProductImage,
  type DevVariant,
  type DevVariantCreate,
} from '@/lib/dev-catalogue/api';

export type DevActionResult<T> = { ok: true; data: T } | { ok: false; error: string };

const isProduction = process.env.NODE_ENV === 'production';

function toMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.isUnauthenticated) return 'Sign in first to use dev tools.';

    const fieldErrors = error.fieldErrors();
    const firstField = Object.values(fieldErrors)[0];
    return firstField ?? error.message;
  }

  if (error instanceof ApiUnreachableError) return error.message;

  return 'Unexpected error.';
}

async function requireDevToken(): Promise<DevActionResult<string>> {
  if (isProduction) {
    return { ok: false, error: 'Dev catalogue tools are disabled in production builds.' };
  }

  const token = await getAccessToken();
  if (!token) {
    return { ok: false, error: 'Sign in first to use dev tools.' };
  }

  return { ok: true, data: token };
}

/** Populates the category picker when the Add Product modal opens. */
export async function devListCategories(): Promise<DevActionResult<DevCategory[]>> {
  const tokenResult = await requireDevToken();
  if (!tokenResult.ok) return tokenResult;

  try {
    const page = await devCatalogueApi.listCategories(tokenResult.data, { page_size: 100 });
    return { ok: true, data: page.items };
  } catch (error) {
    return { ok: false, error: toMessage(error) };
  }
}

/** Populates the product picker when the Add Variant modal opens. */
export async function devListProducts(): Promise<DevActionResult<DevProduct[]>> {
  const tokenResult = await requireDevToken();
  if (!tokenResult.ok) return tokenResult;

  try {
    const page = await devCatalogueApi.listProducts(tokenResult.data, { page_size: 100 });
    return { ok: true, data: page.items };
  } catch (error) {
    return { ok: false, error: toMessage(error) };
  }
}

/** Populates the image picker once a product is chosen in the Add Variant modal. */
export async function devListProductImages(productId: string): Promise<DevActionResult<DevProductImage[]>> {
  const tokenResult = await requireDevToken();
  if (!tokenResult.ok) return tokenResult;

  try {
    const images = await devCatalogueApi.listProductImages(tokenResult.data, productId);
    return { ok: true, data: images };
  } catch (error) {
    return { ok: false, error: toMessage(error) };
  }
}

/** Uploads a new image file for the product and returns it, so the caller can select it as the variant's image. */
export async function devUploadVariantImage(
  productId: string,
  formData: FormData,
): Promise<DevActionResult<DevProductImage>> {
  const tokenResult = await requireDevToken();
  if (!tokenResult.ok) return tokenResult;

  const file = formData.get('file');
  if (!(file instanceof File) || file.size === 0) {
    return { ok: false, error: 'Choose an image file first.' };
  }

  try {
    const image = await devCatalogueApi.uploadProductImage(tokenResult.data, productId, file);
    revalidateTag('products');
    return { ok: true, data: image };
  } catch (error) {
    return { ok: false, error: toMessage(error) };
  }
}

export async function devCreateCategory(formData: FormData): Promise<DevActionResult<DevCategory>> {
  const tokenResult = await requireDevToken();
  if (!tokenResult.ok) return tokenResult;

  const name = String(formData.get('name') ?? '').trim();
  if (!name) return { ok: false, error: 'Category name is required.' };

  const description = String(formData.get('description') ?? '').trim();

  try {
    const category = await devCatalogueApi.createCategory(tokenResult.data, {
      name,
      description: description || null,
    });
    revalidateTag('categories');
    revalidatePath('/shop-list');
    return { ok: true, data: category };
  } catch (error) {
    return { ok: false, error: toMessage(error) };
  }
}

export async function devCreateProduct(formData: FormData): Promise<DevActionResult<DevProduct>> {
  const tokenResult = await requireDevToken();
  if (!tokenResult.ok) return tokenResult;

  const categoryId = String(formData.get('category_id') ?? '').trim();
  const name = String(formData.get('name') ?? '').trim();
  if (!categoryId) return { ok: false, error: 'Pick a category.' };
  if (!name) return { ok: false, error: 'Product name is required.' };

  const shortDescription = String(formData.get('short_description') ?? '').trim();
  const description = String(formData.get('description') ?? '').trim();
  const brand = String(formData.get('brand') ?? '').trim();
  const gender = String(formData.get('gender') ?? '').trim();
  const isFeatured = formData.get('is_featured') === 'on';
  const active = formData.get('active') === 'on';

  // Repeatable image rows: image_url[], image_alt[], image_primary (single index).
  const urls = formData.getAll('image_url').map(v => String(v).trim());
  const alts = formData.getAll('image_alt').map(v => String(v).trim());
  const primaryIndex = Number(formData.get('image_primary_index') ?? -1);

  // `primaryIndex` is the radio button's value -- the row's position in the
  // *original*, unfiltered list -- so blank rows have to be tagged with
  // their original position before any of them are dropped, or dropping one
  // ahead of the chosen primary would shift every later index and mark the
  // wrong row.
  const images = urls
    .map((url, index) => ({ url, alt: alts[index] ?? '', originalIndex: index }))
    .filter(row => row.url)
    .map((row, index) => ({
      url: row.url,
      alt_text: row.alt || null,
      sort_order: index,
      is_primary: row.originalIndex === primaryIndex,
    }));

  if (images.length === 0) {
    return { ok: false, error: 'At least one product image URL is required.' };
  }

  const data: DevProductCreate = {
    category_id: categoryId,
    name,
    short_description: shortDescription || null,
    description: description || null,
    brand: brand || null,
    status: active ? 'ACTIVE' : 'DRAFT',
    gender: (gender as DevProductCreate['gender']) || null,
    is_featured: isFeatured,
    images,
  };

  try {
    const product = await devCatalogueApi.createProduct(tokenResult.data, data);
    revalidateTag('products');
    revalidatePath('/shop-list');
    return { ok: true, data: product };
  } catch (error) {
    return { ok: false, error: toMessage(error) };
  }
}

export async function devCreateVariant(formData: FormData): Promise<DevActionResult<DevVariant>> {
  const tokenResult = await requireDevToken();
  if (!tokenResult.ok) return tokenResult;

  const productId = String(formData.get('product_id') ?? '').trim();
  const sku = String(formData.get('sku') ?? '').trim();
  const name = String(formData.get('name') ?? '').trim();
  const price = String(formData.get('price') ?? '').trim();

  if (!productId) return { ok: false, error: 'Pick a product.' };
  if (!sku) return { ok: false, error: 'SKU is required.' };
  if (!name) return { ok: false, error: 'Variant name is required.' };
  if (!price) return { ok: false, error: 'Price is required.' };

  const active = formData.get('active') === 'on';
  const imageId = String(formData.get('image_id') ?? '').trim();
  const initialQuantity = Number(formData.get('initial_quantity') ?? 0) || 0;
  const lowStockThreshold = Number(formData.get('low_stock_threshold') ?? 0) || 0;

  // Repeatable option rows: option_name[] / option_value[].
  const optionNames = formData.getAll('option_name').map(v => String(v).trim());
  const optionValues = formData.getAll('option_value').map(v => String(v).trim());
  const options = optionNames
    .map((n, index) => ({ name: n, value: optionValues[index] ?? '' }))
    .filter(row => row.name && row.value);

  const data: DevVariantCreate = {
    sku,
    name,
    price,
    status: active ? 'ACTIVE' : 'DRAFT',
    image_id: imageId || null,
    options,
    initial_quantity: Math.max(0, initialQuantity),
    low_stock_threshold: Math.max(0, lowStockThreshold),
  };

  try {
    const variant = await devCatalogueApi.createVariant(tokenResult.data, productId, data);
    revalidateTag('products');
    revalidatePath('/shop-list');
    return { ok: true, data: variant };
  } catch (error) {
    return { ok: false, error: toMessage(error) };
  }
}
