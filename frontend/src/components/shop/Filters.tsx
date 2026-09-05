'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useCallback } from 'react';

import Button from '@/components/ui/Button';
import { Input, Select } from '@/components/ui/Field';
import type { CategoryStorefront, ProductSort } from '@/types/catalogue';

import styles from './Filters.module.css';

const SORT_OPTIONS: { value: ProductSort; label: string }[] = [
  { value: 'newest', label: 'Newest' },
  { value: 'price_low', label: 'Price, low to high' },
  { value: 'price_high', label: 'Price, high to low' },
  { value: 'name_asc', label: 'Name, A to Z' },
  { value: 'name_desc', label: 'Name, Z to A' },
];

/**
 * Filters are held in the URL, so a filtered view can be shared, bookmarked
 * and reached by the back button. The server reads the same parameters to
 * query the API, which is why nothing is filtered in the browser.
 */
export default function Filters({
  categories,
  total,
}: {
  categories: CategoryStorefront[];
  total: number;
}) {
  const router = useRouter();
  const params = useSearchParams();

  const apply = useCallback(
    (changes: Record<string, string>) => {
      const next = new URLSearchParams(params.toString());

      for (const [key, value] of Object.entries(changes)) {
        if (value) next.set(key, value);
        else next.delete(key);
      }

      // Any change to the filters invalidates the page number.
      next.delete('page');
      router.push(`/shop?${next.toString()}`);
    },
    [params, router],
  );

  const hasFilters = ['q', 'category', 'sort', 'min_price', 'max_price'].some((key) => params.get(key));

  return (
    <form
      className={styles.bar}
      action={(formData) =>
        apply({
          q: String(formData.get('q') ?? ''),
          min_price: String(formData.get('min_price') ?? ''),
          max_price: String(formData.get('max_price') ?? ''),
        })
      }
    >
      <div className={styles.search}>
        <Input label="Search" name="q" type="search" placeholder="Silk, loafer, tote" defaultValue={params.get('q') ?? ''} />
      </div>

      <div className={styles.control}>
        <Select
          label="Category"
          name="category"
          defaultValue={params.get('category') ?? ''}
          onChange={(event) => apply({ category: event.target.value })}
        >
          <option value="">All categories</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </Select>
      </div>

      <div className={styles.control}>
        <Select
          label="Sort"
          name="sort"
          defaultValue={params.get('sort') ?? 'newest'}
          onChange={(event) => apply({ sort: event.target.value })}
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      </div>

      <div className={styles.actions}>
        <Button type="submit" variant="secondary">
          Apply
        </Button>

        {hasFilters && (
          <Button type="button" variant="ghost" onClick={() => router.push('/shop')}>
            Clear
          </Button>
        )}
      </div>

      <p className={styles.count} data-numeric>
        {total} {total === 1 ? 'product' : 'products'}
      </p>
    </form>
  );
}
