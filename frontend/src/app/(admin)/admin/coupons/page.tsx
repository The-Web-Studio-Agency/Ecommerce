import AdminShell from '@/components/admin/AdminShell';
import Badge from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/States';
import { adminApi } from '@/lib/api/admin';
import { requireStaff } from '@/lib/auth/require-staff';
import { formatDate, formatMoney } from '@/lib/format';

import styles from '@/components/admin/AdminShell.module.css';

export default async function AdminCouponsPage() {
  const { user, token } = await requireStaff();
  const coupons = await adminApi.listCoupons(token, { page_size: 50 }).catch(() => null);
  const items = coupons?.items ?? [];

  return (
    <AdminShell user={user}>
      <h1 className={styles.sectionTitle}>Coupons</h1>

      {items.length === 0 ? (
        <EmptyState title="No coupons" body="Coupons created in the API appear here." />
      ) : (
        <div className={styles.scroll}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Code</th>
                <th>Discount</th>
                <th>Window</th>
                <th className={styles.num}>Used</th>
                <th>State</th>
              </tr>
            </thead>

            <tbody>
              {items.map((coupon) => (
                <tr key={coupon.id}>
                  <td>{coupon.code}</td>
                  <td data-numeric>
                    {coupon.discount_type === 'PERCENTAGE'
                      ? `${coupon.discount_value}%`
                      : formatMoney(coupon.discount_value, coupon.currency)}
                    {coupon.min_order_amount &&
                      ` over ${formatMoney(coupon.min_order_amount, coupon.currency)}`}
                  </td>
                  <td>
                    {coupon.starts_at ? formatDate(coupon.starts_at) : 'Any time'}
                    {coupon.expires_at ? ` to ${formatDate(coupon.expires_at)}` : ''}
                  </td>
                  <td className={styles.num} data-numeric>
                    {coupon.times_used}
                    {coupon.usage_limit ? ` / ${coupon.usage_limit}` : ''}
                  </td>
                  <td>
                    {coupon.is_active ? (
                      <Badge tone="positive">Active</Badge>
                    ) : (
                      <Badge tone="neutral">Off</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AdminShell>
  );
}
