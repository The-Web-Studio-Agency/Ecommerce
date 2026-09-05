import AdminShell from '@/components/admin/AdminShell';
import Badge from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/States';
import { catalogueApi } from '@/lib/api/catalogue';
import { requireStaff } from '@/lib/auth/require-staff';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatPriceRange } from '@/lib/format';

import styles from '@/components/admin/AdminShell.module.css';

/**
 * Reads the storefront catalogue.
 *
 * The admin catalogue endpoints exist for writes, but product creation
 * needs multipart image upload and variant and inventory management that
 * belong in their own phase. This lists what is published so stock and
 * pricing can be seen; it does not pretend to edit.
 */
export default async function AdminProductsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const { user } = await requireStaff();
  const { page } = await searchParams;

  const parsed = Number.parseInt(page ?? '1', 10);
  const products = await catalogueApi.listProducts({
    page: Number.isFinite(parsed) && parsed > 0 ? parsed : 1,
    page_size: 25,
  });

  return (
    <AdminShell user={user}>
      <h1 className={styles.sectionTitle}>Products</h1>

      {products.items.length === 0 ? (
        <EmptyState title="No products published" body="Publish a product to see it here." />
      ) : (
        <div className={styles.scroll}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Product</th>
                <th>Brand</th>
                <th>Stock</th>
                <th className={styles.num}>Price</th>
              </tr>
            </thead>

            <tbody>
              {products.items.map((product) => (
                <tr key={product.id}>
                  <td>
                    {product.name}
                    <br />
                    <span className={styles.tileLabel}>{product.short_description}</span>
                  </td>
                  <td>{product.brand ?? '-'}</td>
                  <td>
                    {product.in_stock ? (
                      <Badge tone="positive">In stock</Badge>
                    ) : (
                      <Badge tone="critical">Out of stock</Badge>
                    )}
                  </td>
                  <td className={styles.num} data-numeric>
                    {formatPriceRange(product.price_from, product.price_to, STOREFRONT_CURRENCY)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className={styles.tileLabel} style={{ marginTop: 'var(--space-4)' }} data-numeric>
        {products.meta.total_items} products
      </p>
    </AdminShell>
  );
}
