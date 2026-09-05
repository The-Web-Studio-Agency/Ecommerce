import Image from 'next/image';
import Link from 'next/link';

import Badge from '@/components/ui/Badge';
import { formatPriceRange } from '@/lib/format';
import type { ProductSummaryStorefront } from '@/types/catalogue';

import styles from './ProductCard.module.css';

export function ProductGrid({ children }: { children: React.ReactNode }) {
  return <div className={styles.grid}>{children}</div>;
}

/**
 * Prices come from the backend as a range across the product's variants.
 * Nothing here recomputes them, and there is no discount badge: the
 * catalogue holds one price per variant, and reductions only exist as
 * coupons applied at checkout.
 */
export default function ProductCard({
  product,
  currency,
  priority = false,
}: {
  product: ProductSummaryStorefront;
  currency: string;
  priority?: boolean;
}) {
  const image = product.primary_image;

  return (
    <Link href={`/products/${product.id}`} className={styles.card}>
      <div className={styles.frame}>
        {image && (
          <Image
            src={image.url}
            alt={image.alt_text ?? product.name}
            fill
            className={styles.image}
            sizes="(min-width: 72rem) 25vw, (min-width: 48rem) 33vw, 50vw"
            priority={priority}
          />
        )}

        {!product.in_stock && (
          <span className={styles.soldOut}>
            <Badge tone="neutral">Sold out</Badge>
          </span>
        )}
      </div>

      <div className={styles.body}>
        <h3 className={styles.name}>{product.name}</h3>

        {product.short_description && <p className={styles.meta}>{product.short_description}</p>}

        <p className={styles.price} data-numeric>
          {formatPriceRange(product.price_from, product.price_to, currency)}
        </p>
      </div>
    </Link>
  );
}
