import Badge from '@/components/ui/Badge';
import { formatDate } from '@/lib/format';
import type { RatingSummary, Review } from '@/types/reviews';

import styles from './Reviews.module.css';

function Stars({ rating }: { rating: number }) {
  return (
    <span className={styles.stars} aria-label={`${rating} out of 5`}>
      {'★'.repeat(rating)}
      {'☆'.repeat(5 - rating)}
    </span>
  );
}

export default function Reviews({ summary, reviews }: { summary: RatingSummary | null; reviews: Review[] }) {
  if (!summary || summary.total_reviews === 0) {
    return <p className={styles.count}>No reviews yet. Reviews open once an order has been delivered.</p>;
  }

  return (
    <>
      <div className={styles.summary}>
        <span className={styles.average} data-numeric>
          {summary.average_rating.toFixed(1)}
        </span>
        <Stars rating={Math.round(summary.average_rating)} />
        <span className={styles.count} data-numeric>
          {summary.total_reviews} {summary.total_reviews === 1 ? 'review' : 'reviews'}
        </span>
      </div>

      <div className={styles.list}>
        {reviews.map((review) => (
          <article key={review.id} className={styles.review}>
            <div className={styles.head}>
              <Stars rating={review.rating} />
              <span className={styles.date}>{formatDate(review.created_at)}</span>
              {review.is_verified_purchase && <Badge tone="positive">Verified purchase</Badge>}
            </div>

            {review.title && <p className={styles.title}>{review.title}</p>}
            {review.comment && <p className={styles.comment}>{review.comment}</p>}
          </article>
        ))}
      </div>
    </>
  );
}
