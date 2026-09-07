'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useActionState, useEffect, useState } from 'react';

import { deleteReview, submitReview } from '@/lib/reviews/actions';
import { formatDate } from '@/lib/format';
import type { RatingSummary, Review } from '@/types/reviews';

const initialState = { status: 'idle' as const, message: null as string | null };

function Stars({ value }: { value: number }) {
  return (
    <span className="single-product-rating" style={{ display: 'inline-flex' }}>
      {Array.from({ length: 5 }).map((_, index) => (
        <i
          key={index}
          className={index < value ? 'fa-solid fa-star filled' : 'fa-regular fa-star'}
        />
      ))}
    </span>
  );
}

/** Clickable 1-5 star input, since there is no rating input elsewhere to match. */
function StarPicker({ name, value, onChange }: { name: string; value: number; onChange: (value: number) => void }) {
  const [hover, setHover] = useState(0);

  return (
    <div onMouseLeave={() => setHover(0)} style={{ display: 'inline-flex', gap: 4, cursor: 'pointer' }}>
      <input type="hidden" name={name} value={value} />
      {Array.from({ length: 5 }).map((_, index) => {
        const star = index + 1;
        const filled = star <= (hover || value);

        return (
          <i
            key={star}
            onMouseEnter={() => setHover(star)}
            onClick={() => onChange(star)}
            className={filled ? 'fa-solid fa-star filled' : 'fa-regular fa-star'}
            style={{ fontSize: 20 }}
          />
        );
      })}
    </div>
  );
}

function WriteReviewForm({ productId }: { productId: string }) {
  const router = useRouter();
  const [state, formAction, pending] = useActionState(submitReview, initialState);
  const [rating, setRating] = useState(0);

  useEffect(() => {
    if (state.status === 'success') router.refresh();
  }, [state, router]);

  if (state.status === 'success') {
    return <p className="product-cart-message">{state.message}</p>;
  }

  return (
    <form action={formAction} className="mt-4">
      <input type="hidden" name="product_id" value={productId} />

      <div className="mb-3">
        <p className="mb-2">Your rating</p>
        <StarPicker name="rating" value={rating} onChange={setRating} />
        {state.fieldErrors?.rating && <p className="product-cart-message">{state.fieldErrors.rating}</p>}
      </div>

      <div className="mb-3">
        <input type="text" name="title" maxLength={150} placeholder="Title (optional)" className="form-control" />
      </div>

      <div className="mb-3">
        <textarea name="comment" maxLength={2000} rows={4} placeholder="Tell others what you thought" className="form-control" />
      </div>

      {state.message && state.status === 'error' && <p className="product-cart-message">{state.message}</p>}

      <button type="submit" disabled={pending} className="add-to-cart-btn">
        {pending ? 'Submitting...' : 'Submit Review'}
      </button>
    </form>
  );
}

function DeleteReviewButton({ reviewId, productId }: { reviewId: string; productId: string }) {
  const router = useRouter();
  const [state, formAction, pending] = useActionState(deleteReview, initialState);

  useEffect(() => {
    if (state.status === 'success') router.refresh();
  }, [state, router]);

  return (
    <form action={formAction}>
      <input type="hidden" name="review_id" value={reviewId} />
      <input type="hidden" name="product_id" value={productId} />
      <button type="submit" disabled={pending} className="product-cart-message" style={{ background: 'none', border: 'none', textDecoration: 'underline', padding: 0 }}>
        {pending ? 'Deleting...' : 'Delete'}
      </button>
    </form>
  );
}

export default function ProductReviews({
  productId,
  reviews,
  summary,
  currentUserId,
}: {
  productId: string;
  reviews: Review[];
  summary: RatingSummary | null;
  currentUserId: string | null;
}) {
  const total = summary?.total_reviews ?? 0;

  return (
    <section className="wrapper">
      <div className="single-product-details-section mt-5" style={{ maxWidth: 800 }}>
        <p className="description-heading">REVIEWS ({total})</p>

      {summary && total > 0 && (
        <div className="d-flex align-items-center gap-3 mb-4">
          <Stars value={Math.round(summary.average_rating)} />
          <span>{summary.average_rating.toFixed(1)} out of 5</span>
        </div>
      )}

      {reviews.length === 0 ? (
        <p>No reviews yet. Be the first to share your thoughts.</p>
      ) : (
        <div className="d-flex flex-column gap-4 mb-4">
          {reviews.map(review => (
            <div key={review.id} style={{ borderBottom: '1px solid #eee', paddingBottom: 16 }}>
              <Stars value={review.rating} />
              {review.is_verified_purchase && (
                <span className="product-cart-message" style={{ marginLeft: 8 }}>
                  Verified purchase
                </span>
              )}
              {review.title && <p className="mb-1" style={{ fontWeight: 600 }}>{review.title}</p>}
              {review.comment && <p className="mb-1">{review.comment}</p>}
              <p className="product-cart-message">{formatDate(review.created_at)}</p>
              {currentUserId && review.user_id === currentUserId && (
                <DeleteReviewButton reviewId={review.id} productId={productId} />
              )}
            </div>
          ))}
        </div>
      )}

      {currentUserId ? (
        <WriteReviewForm productId={productId} />
      ) : (
        <p>
          <Link href={`/signin?next=/single-product/${productId}`}>Sign in</Link> to write a review.
        </p>
      )}
      </div>
    </section>
  );
}
