import AdminShell from '@/components/admin/AdminShell';
import ModerateReview from '@/components/admin/ModerateReview';
import Badge from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/States';
import { adminApi } from '@/lib/api/admin';
import { ApiError } from '@/lib/api/errors';
import { requireStaff } from '@/lib/auth/require-staff';
import { formatDate } from '@/lib/format';

import styles from '@/components/admin/AdminShell.module.css';

export default async function AdminReviewsPage({
  searchParams,
}: {
  searchParams: Promise<{ approved?: string }>;
}) {
  const { user, token } = await requireStaff();
  const { approved } = await searchParams;

  // Moderation listing is admin-only; staff see a clear refusal rather
  // than an empty table that looks like there is nothing to do.
  let reviews;
  let forbidden = false;

  try {
    reviews = await adminApi.listReviews(token, {
      page_size: 50,
      is_approved: approved === 'true' ? true : approved === 'false' ? false : undefined,
    });
  } catch (error) {
    if (error instanceof ApiError && error.isForbidden) forbidden = true;
    else throw error;
  }

  const items = reviews?.items ?? [];

  return (
    <AdminShell user={user}>
      <h1 className={styles.sectionTitle}>Reviews</h1>

      {forbidden ? (
        <EmptyState
          title="Admins only"
          body="Review moderation needs an admin account. Ask an admin to take a look."
        />
      ) : items.length === 0 ? (
        <EmptyState title="Nothing to moderate" body="New reviews will appear here." />
      ) : (
        <div className={styles.scroll}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Rating</th>
                <th>Review</th>
                <th>Left</th>
                <th>State</th>
                <th />
              </tr>
            </thead>

            <tbody>
              {items.map((review) => (
                <tr key={review.id}>
                  <td data-numeric>{review.rating} / 5</td>
                  <td>
                    {review.title && <strong>{review.title}</strong>}
                    {review.title && <br />}
                    {review.comment ?? <span className={styles.tileLabel}>No comment</span>}
                  </td>
                  <td>{formatDate(review.created_at)}</td>
                  <td>
                    {review.is_approved ? (
                      <Badge tone="positive">Visible</Badge>
                    ) : (
                      <Badge tone="caution">Hidden</Badge>
                    )}
                  </td>
                  <td>
                    {user.role === 'ADMIN' && (
                      <ModerateReview reviewId={review.id} isApproved={review.is_approved} />
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
