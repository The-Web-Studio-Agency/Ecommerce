import AdminShell from '@/components/admin/AdminShell';
import Badge from '@/components/ui/Badge';
import { adminApi } from '@/lib/api/admin';
import { requireStaff } from '@/lib/auth/require-staff';
import { STOREFRONT_CURRENCY } from '@/lib/currency';
import { formatMoney } from '@/lib/format';

import styles from '@/components/admin/AdminShell.module.css';

/**
 * Delivery and tax are single tenant-wide settings, which is what makes
 * every order's shipping and tax figure. Shown read-only here: the API
 * takes writes, but changing pricing for the whole shop deserves its own
 * confirmed flow rather than an inline field.
 */
export default async function AdminSettingsPage() {
  const { user, token } = await requireStaff();

  const [shipping, tax] = await Promise.all([
    adminApi.getShippingSettings(token).catch(() => null),
    adminApi.getTaxSettings(token).catch(() => null),
  ]);

  return (
    <AdminShell user={user}>
      <h1 className={styles.sectionTitle}>Settings</h1>

      <div className={styles.tiles}>
        <div className={styles.tile}>
          <p className={styles.tileLabel}>Delivery charge</p>
          <p className={styles.tileValue} data-numeric>
            {shipping ? formatMoney(shipping.shipping_amount, STOREFRONT_CURRENCY) : '-'}
          </p>
          {shipping?.free_shipping_minimum && (
            <p className={styles.tileLabel}>
              Free over {formatMoney(shipping.free_shipping_minimum, STOREFRONT_CURRENCY)}
            </p>
          )}
          {shipping && (
            <p style={{ marginTop: 'var(--space-2)' }}>
              {shipping.is_active ? <Badge tone="positive">Applied</Badge> : <Badge tone="neutral">Off</Badge>}
            </p>
          )}
        </div>

        <div className={styles.tile}>
          <p className={styles.tileLabel}>Tax</p>
          <p className={styles.tileValue} data-numeric>
            {tax ? `${tax.tax_percentage}%` : '-'}
          </p>
          {tax && (
            <p style={{ marginTop: 'var(--space-2)' }}>
              {tax.is_active ? <Badge tone="positive">Applied</Badge> : <Badge tone="neutral">Off</Badge>}
            </p>
          )}
        </div>

        <div className={styles.tile}>
          <p className={styles.tileLabel}>Payment</p>
          <p className={styles.tileValue}>COD</p>
          <p className={styles.tileLabel}>Cash on delivery is the only method the API supports.</p>
        </div>
      </div>
    </AdminShell>
  );
}
