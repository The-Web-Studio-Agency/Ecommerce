'use client';

/**
 * ============================================================================
 * TEMPORARY DEV-ONLY CODE
 * ============================================================================
 * A stand-in for the not-yet-built Admin panel, so the catalogue can be
 * populated for testing without one. Delete this to remove it completely:
 *
 *   - This whole `_components/dev-catalogue/` folder
 *   - `src/lib/dev-catalogue/` (the server actions + API wrappers it calls)
 *   - The `{DEV_TOOLS_ENABLED && <DevCatalogueTools />}` line in
 *     shop-list/page.tsx, and its import
 *
 * Everything here calls the temporary `/dev/catalogue/*` endpoints
 * (`backend/app/catalogue/dev_router.py`) -- any signed-in shopper, not just
 * admin/staff, so this is usable without an admin account. That router
 * calls the same `CategoryService`/`ProductService`/`VariantService`/
 * `ProductImageService` the real admin endpoints do -- no duplicate business
 * logic -- and never exists in a production build (see dev_router.py and its
 * registration guard in app/api/v1.py). The real `/catalogue/*` admin
 * endpoints are untouched and still admin/staff-only.
 *
 * Rendered only when `DEV_TOOLS_ENABLED` (see page.tsx) is true, which is
 * `process.env.NODE_ENV !== 'production'` -- this never appears in a
 * production build.
 */

import { useEffect, useRef, useState } from 'react';

import {
  devCreateCategory,
  devCreateProduct,
  devCreateVariant,
  devListCategories,
  devListProductImages,
  devListProducts,
  devUploadVariantImage,
  type DevActionResult,
} from '@/lib/dev-catalogue/actions';
import type { DevCategory, DevProduct, DevProductImage } from '@/lib/dev-catalogue/api';

import styles from './DevCatalogueTools.module.css';

type ModalKind = null | 'category' | 'product' | 'variant';

function formDataFrom(fields: Record<string, string>): FormData {
  const formData = new FormData();
  for (const [key, value] of Object.entries(fields)) formData.set(key, value);
  return formData;
}

function ModalShell({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div
      className={styles.overlay}
      onMouseDown={event => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className={styles.panel} role="dialog" aria-modal="true" aria-label={title}>
        <div className={styles.panelHead}>
          <h2 className={styles.panelTitle}>{title}</h2>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function CategoryModal({ onClose }: { onClose: () => void }) {
  const formRef = useRef<HTMLFormElement>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setSuccess(null);

    const result = await devCreateCategory(new FormData(event.currentTarget));

    setPending(false);
    if (result.ok) {
      setSuccess(`Category "${result.data.name}" created.`);
      formRef.current?.reset();
    } else {
      setError(result.error);
    }
  }

  return (
    <ModalShell title="+ Add Category" onClose={onClose}>
      <form ref={formRef} onSubmit={handleSubmit}>
        {error && <p className={styles.errorText}>{error}</p>}
        {success && <p className={styles.successText}>{success}</p>}

        <label className={styles.field}>
          <span>Name</span>
          <input className={styles.input} name="name" required maxLength={150} />
        </label>

        <label className={styles.field}>
          <span>Description (optional)</span>
          <textarea className={styles.textarea} name="description" maxLength={2000} />
        </label>

        <div className={styles.actions}>
          <button type="button" className={styles.cancelBtn} onClick={onClose}>
            Close
          </button>
          <button type="submit" className={styles.submitBtn} disabled={pending}>
            {pending ? 'Creating…' : 'Create Category'}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}

interface ImageRow {
  url: string;
  alt: string;
}

function ProductModal({ onClose }: { onClose: () => void }) {
  const formRef = useRef<HTMLFormElement>(null);
  const [categories, setCategories] = useState<DevCategory[] | null>(null);
  const [categoriesError, setCategoriesError] = useState<string | null>(null);
  const [selectedCategoryId, setSelectedCategoryId] = useState('');
  const [newCategoryName, setNewCategoryName] = useState('');
  const [images, setImages] = useState<ImageRow[]>([{ url: '', alt: '' }]);
  const [primaryIndex, setPrimaryIndex] = useState(0);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    devListCategories().then((result: DevActionResult<DevCategory[]>) => {
      if (cancelled) return;
      if (result.ok) {
        setCategories(result.data);
        if (result.data.length > 0) setSelectedCategoryId(result.data[0].id);
      } else {
        setCategoriesError(result.error);
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  function updateImage(index: number, patch: Partial<ImageRow>) {
    setImages(rows => rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  function addImageRow() {
    setImages(rows => [...rows, { url: '', alt: '' }]);
  }

  function removeImageRow(index: number) {
    setImages(rows => rows.filter((_, i) => i !== index));
    setPrimaryIndex(current => (current === index ? 0 : current > index ? current - 1 : current));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setSuccess(null);

    let categoryId = selectedCategoryId;

    if (newCategoryName.trim()) {
      const categoryResult = await devCreateCategory(formDataFrom({ name: newCategoryName.trim() }));
      if (!categoryResult.ok) {
        setPending(false);
        setError(categoryResult.error);
        return;
      }
      categoryId = categoryResult.data.id;
      setCategories(prev => (prev ? [...prev, categoryResult.data] : [categoryResult.data]));
    }

    if (!categoryId) {
      setPending(false);
      setError('Pick a category, or type a new one.');
      return;
    }

    const formData = new FormData(event.currentTarget);
    formData.set('category_id', categoryId);

    const result = await devCreateProduct(formData);

    setPending(false);
    if (result.ok) {
      setSuccess(`Product "${result.data.name}" created.`);
      formRef.current?.reset();
      setNewCategoryName('');
      setImages([{ url: '', alt: '' }]);
      setPrimaryIndex(0);
    } else {
      setError(result.error);
    }
  }

  return (
    <ModalShell title="+ Add Product" onClose={onClose}>
      <form ref={formRef} onSubmit={handleSubmit}>
        {error && <p className={styles.errorText}>{error}</p>}
        {success && <p className={styles.successText}>{success}</p>}
        {categoriesError && <p className={styles.errorText}>Categories: {categoriesError}</p>}

        <label className={styles.field}>
          <span>Category</span>
          <select
            className={styles.select}
            value={selectedCategoryId}
            onChange={event => setSelectedCategoryId(event.target.value)}
            disabled={!!newCategoryName.trim()}
          >
            {categories === null && <option value="">Loading…</option>}
            {categories?.length === 0 && <option value="">No categories yet</option>}
            {categories?.map(category => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.field}>
          <span>Or create a new category</span>
          <input
            className={styles.input}
            value={newCategoryName}
            onChange={event => setNewCategoryName(event.target.value)}
            placeholder="New category name"
            maxLength={150}
          />
        </label>

        <label className={styles.field}>
          <span>Name</span>
          <input className={styles.input} name="name" required maxLength={150} />
        </label>

        <label className={styles.field}>
          <span>Short description (optional)</span>
          <input className={styles.input} name="short_description" maxLength={500} />
        </label>

        <label className={styles.field}>
          <span>Description (optional)</span>
          <textarea className={styles.textarea} name="description" maxLength={2000} />
        </label>

        <label className={styles.field}>
          <span>Brand (optional)</span>
          <input className={styles.input} name="brand" maxLength={150} />
        </label>

        <label className={styles.field}>
          <span>Gender (optional)</span>
          <select className={styles.select} name="gender" defaultValue="">
            <option value="">—</option>
            <option value="MEN">Men</option>
            <option value="WOMEN">Women</option>
            <option value="UNISEX">Unisex</option>
          </select>
        </label>

        <label className={styles.checkboxRow}>
          <input type="checkbox" name="is_featured" />
          Featured
        </label>

        <label className={styles.checkboxRow}>
          <input type="checkbox" name="active" defaultChecked />
          Active (visible in the shop grid immediately)
        </label>

        <div className={styles.divider} />

        <span>Images</span>
        <p className={styles.hint}>
          Paste a hosted image URL per row (this listing shows whatever the URL points to -- there is
          no file upload here).
        </p>

        {images.map((row, index) => (
          <div className={styles.imageRow} key={index}>
            <input
              className={styles.input}
              name="image_url"
              placeholder="https://…"
              value={row.url}
              onChange={event => updateImage(index, { url: event.target.value })}
            />
            <input
              className={styles.input}
              name="image_alt"
              placeholder="Alt text (optional)"
              value={row.alt}
              onChange={event => updateImage(index, { alt: event.target.value })}
            />
            <label className={styles.radioLabel}>
              <input
                type="radio"
                name="image_primary_index"
                value={index}
                checked={primaryIndex === index}
                onChange={() => setPrimaryIndex(index)}
              />
              Primary
            </label>
            {images.length > 1 && (
              <button
                type="button"
                className={styles.removeRowBtn}
                onClick={() => removeImageRow(index)}
                aria-label="Remove image row"
              >
                ×
              </button>
            )}
          </div>
        ))}
        <button type="button" className={styles.addRowBtn} onClick={addImageRow}>
          + Add another image
        </button>

        <div className={styles.actions}>
          <button type="button" className={styles.cancelBtn} onClick={onClose}>
            Close
          </button>
          <button type="submit" className={styles.submitBtn} disabled={pending}>
            {pending ? 'Creating…' : 'Create Product'}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}

interface OptionRow {
  name: string;
  value: string;
}

function VariantModal({ onClose }: { onClose: () => void }) {
  const formRef = useRef<HTMLFormElement>(null);
  const [products, setProducts] = useState<DevProduct[] | null>(null);
  const [productsError, setProductsError] = useState<string | null>(null);
  const [selectedProductId, setSelectedProductId] = useState('');
  const [images, setImages] = useState<DevProductImage[] | null>(null);
  const [imagesError, setImagesError] = useState<string | null>(null);
  const [selectedImageId, setSelectedImageId] = useState('');
  const [uploading, setUploading] = useState(false);
  const [options, setOptions] = useState<OptionRow[]>([{ name: '', value: '' }]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    devListProducts().then((result: DevActionResult<DevProduct[]>) => {
      if (cancelled) return;
      if (result.ok) {
        setProducts(result.data);
        if (result.data.length > 0) setSelectedProductId(result.data[0].id);
      } else {
        setProductsError(result.error);
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  // Which images can be attached to a variant changes with the product,
  // since an image belongs to (and can only be attached to a variant of) one
  // specific product -- see VariantService._validate_image on the backend.
  useEffect(() => {
    if (!selectedProductId) {
      setImages(null);
      return;
    }

    let cancelled = false;
    setImages(null);
    setImagesError(null);
    setSelectedImageId('');

    devListProductImages(selectedProductId).then(result => {
      if (cancelled) return;
      if (result.ok) setImages(result.data);
      else setImagesError(result.error);
    });

    return () => {
      cancelled = true;
    };
  }, [selectedProductId]);

  async function handleUploadImage(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || !selectedProductId) return;

    setUploading(true);
    setImagesError(null);

    const formData = new FormData();
    formData.set('file', file);

    const result = await devUploadVariantImage(selectedProductId, formData);

    setUploading(false);
    if (result.ok) {
      setImages(current => (current ? [...current, result.data] : [result.data]));
      setSelectedImageId(result.data.id);
    } else {
      setImagesError(result.error);
    }
  }

  function updateOption(index: number, patch: Partial<OptionRow>) {
    setOptions(rows => rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  function addOptionRow() {
    setOptions(rows => (rows.length >= 3 ? rows : [...rows, { name: '', value: '' }]));
  }

  function removeOptionRow(index: number) {
    setOptions(rows => rows.filter((_, i) => i !== index));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedProductId) {
      setError('Pick a product.');
      return;
    }

    setPending(true);
    setError(null);
    setSuccess(null);

    const formData = new FormData(event.currentTarget);
    formData.set('product_id', selectedProductId);
    formData.set('image_id', selectedImageId);

    const result = await devCreateVariant(formData);

    setPending(false);
    if (result.ok) {
      setSuccess(`Variant "${result.data.name}" (${result.data.sku}) created.`);
      formRef.current?.reset();
      setOptions([{ name: '', value: '' }]);
      setSelectedImageId('');
    } else {
      setError(result.error);
    }
  }

  return (
    <ModalShell title="+ Add Variant" onClose={onClose}>
      <form ref={formRef} onSubmit={handleSubmit}>
        {error && <p className={styles.errorText}>{error}</p>}
        {success && <p className={styles.successText}>{success}</p>}
        {productsError && <p className={styles.errorText}>Products: {productsError}</p>}

        <label className={styles.field}>
          <span>Product</span>
          <select
            className={styles.select}
            value={selectedProductId}
            onChange={event => setSelectedProductId(event.target.value)}
          >
            {products === null && <option value="">Loading…</option>}
            {products?.length === 0 && <option value="">No products yet -- add one first</option>}
            {products?.map(product => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.field}>
          <span>SKU</span>
          <input className={styles.input} name="sku" required maxLength={64} placeholder="e.g. KURTA-BLK-M" />
        </label>

        <label className={styles.field}>
          <span>Name</span>
          <input className={styles.input} name="name" required maxLength={150} placeholder="e.g. Black / M" />
        </label>

        <label className={styles.field}>
          <span>Price</span>
          <input className={styles.input} name="price" type="number" min="0" step="0.01" required />
        </label>

        <div className={styles.divider} />

        <span>Image for this variant (optional)</span>
        <p className={styles.hint}>
          Shown on the Product Detail page when a shopper picks this exact variant. Leave nothing
          selected to keep showing the product's usual photo.
        </p>
        {imagesError && <p className={styles.errorText}>{imagesError}</p>}
        {!selectedProductId && <p className={styles.hint}>Pick a product above first.</p>}
        {selectedProductId && images === null && <p className={styles.hint}>Loading images…</p>}
        {selectedProductId && images?.length === 0 && (
          <p className={styles.hint}>This product has no images yet.</p>
        )}
        {images && images.length > 0 && (
          <div className={styles.imagePickerRow}>
            <label className={styles.imagePickerOption}>
              <input
                type="radio"
                name="_image_pick"
                checked={selectedImageId === ''}
                onChange={() => setSelectedImageId('')}
              />
              None
            </label>
            {images.map(image => (
              <label key={image.id} className={styles.imagePickerOption}>
                <input
                  type="radio"
                  name="_image_pick"
                  checked={selectedImageId === image.id}
                  onChange={() => setSelectedImageId(image.id)}
                />
                {/* Plain <img>, not next/image -- this thumbnail is a fixed
                    small size and not worth the optimizer for a dev tool. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={image.url} alt={image.alt_text ?? ''} className={styles.imagePickerThumb} />
              </label>
            ))}
          </div>
        )}
        <label className={styles.field}>
          <span>Or upload a new image for this product</span>
          <input
            className={styles.input}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            disabled={!selectedProductId || uploading}
            onChange={handleUploadImage}
          />
          {uploading && <span className={styles.hint}>Uploading…</span>}
        </label>

        <div className={styles.divider} />

        <label className={styles.checkboxRow}>
          <input type="checkbox" name="active" defaultChecked />
          Active (purchasable / counted in the shop's price range immediately)
        </label>

        <label className={styles.field}>
          <span>Opening stock quantity</span>
          <input className={styles.input} name="initial_quantity" type="number" min="0" defaultValue={0} />
        </label>

        <label className={styles.field}>
          <span>Low-stock threshold</span>
          <input className={styles.input} name="low_stock_threshold" type="number" min="0" defaultValue={0} />
        </label>

        <div className={styles.divider} />

        <span>Options (up to 3, e.g. Color / Red)</span>
        {options.map((row, index) => (
          <div className={styles.optionRow} key={index}>
            <input
              className={styles.input}
              name="option_name"
              placeholder="Name (e.g. Color)"
              value={row.name}
              onChange={event => updateOption(index, { name: event.target.value })}
            />
            <input
              className={styles.input}
              name="option_value"
              placeholder="Value (e.g. Red)"
              value={row.value}
              onChange={event => updateOption(index, { value: event.target.value })}
            />
            {options.length > 1 && (
              <button
                type="button"
                className={styles.removeRowBtn}
                onClick={() => removeOptionRow(index)}
                aria-label="Remove option row"
              >
                ×
              </button>
            )}
          </div>
        ))}
        {options.length < 3 && (
          <button type="button" className={styles.addRowBtn} onClick={addOptionRow}>
            + Add another option
          </button>
        )}

        <div className={styles.actions}>
          <button type="button" className={styles.cancelBtn} onClick={onClose}>
            Close
          </button>
          <button type="submit" className={styles.submitBtn} disabled={pending}>
            {pending ? 'Creating…' : 'Create Variant'}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}

export default function DevCatalogueTools() {
  const [openModal, setOpenModal] = useState<ModalKind>(null);

  return (
    <>
      <div className={styles.bar}>
        <span className={styles.label}>Dev tools (temporary)</span>
        <button type="button" className={styles.btn} onClick={() => setOpenModal('category')}>
          + Add Category
        </button>
        <button type="button" className={styles.btn} onClick={() => setOpenModal('product')}>
          + Add Product
        </button>
        <button type="button" className={styles.btn} onClick={() => setOpenModal('variant')}>
          + Add Variant
        </button>
      </div>

      {openModal === 'category' && <CategoryModal onClose={() => setOpenModal(null)} />}
      {openModal === 'product' && <ProductModal onClose={() => setOpenModal(null)} />}
      {openModal === 'variant' && <VariantModal onClose={() => setOpenModal(null)} />}
    </>
  );
}
