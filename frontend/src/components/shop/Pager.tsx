import Link from 'next/link';

import type { PageMeta } from '@/types/api';

import styles from './Filters.module.css';

/** Pages through the API's own meta rather than counting rows client-side. */
export default function Pager({ meta, params }: { meta: PageMeta; params: URLSearchParams }) {
  if (meta.total_pages <= 1) return null;

  const href = (page: number) => {
    const next = new URLSearchParams(params.toString());
    next.set('page', String(page));
    return `/shop?${next.toString()}`;
  };

  const hasPrevious = meta.page > 1;
  const hasNext = meta.page < meta.total_pages;

  return (
    <nav className={styles.pager} aria-label="Pagination">
      <Link
        href={hasPrevious ? href(meta.page - 1) : '#'}
        className={hasPrevious ? undefined : styles.disabled}
        aria-disabled={!hasPrevious}
      >
        Previous
      </Link>

      <span className={styles.pageInfo} data-numeric>
        Page {meta.page} of {meta.total_pages}
      </span>

      <Link
        href={hasNext ? href(meta.page + 1) : '#'}
        className={hasNext ? undefined : styles.disabled}
        aria-disabled={!hasNext}
      >
        Next
      </Link>
    </nav>
  );
}
