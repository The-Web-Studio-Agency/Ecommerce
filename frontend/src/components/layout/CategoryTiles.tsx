import Link from 'next/link';

import type { CategoryStorefront } from '@/types/catalogue';

import styles from './CategoryTiles.module.css';

export default function CategoryTiles({ categories }: { categories: CategoryStorefront[] }) {
  return (
    <div className={styles.grid}>
      {categories.map((category) => (
        <Link key={category.id} href={`/shop?category=${category.id}`} className={styles.tile}>
          <span className={styles.name}>{category.name}</span>
          {category.description && <span className={styles.description}>{category.description}</span>}
        </Link>
      ))}
    </div>
  );
}
