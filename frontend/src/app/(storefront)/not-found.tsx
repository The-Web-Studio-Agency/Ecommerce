import NotFoundPage from './_components/not-found/NotFoundPage';

export const metadata = {
  title: 'Page Not Found | ZEEN',
  description: "The page you're looking for doesn't exist or may have been moved.",
};

/**
 * Fires when a page inside the `(storefront)` group calls `notFound()`
 * (an invalid product id, an invalid order, etc). A truly unmatched URL
 * with no matching route at all is handled by the separate root
 * `src/app/not-found.tsx` instead -- see its comment.
 */
export default function NotFound() {
  return <NotFoundPage />;
}
