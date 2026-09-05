'use client';

import Image from 'next/image';
import { useState } from 'react';

import type { ProductImageStorefront } from '@/types/catalogue';

import styles from './Gallery.module.css';

export default function Gallery({
  images,
  productName,
}: {
  images: ProductImageStorefront[];
  productName: string;
}) {
  const [active, setActive] = useState(0);

  if (images.length === 0) {
    return <div className={styles.main} aria-hidden="true" />;
  }

  const current = images[Math.min(active, images.length - 1)];

  return (
    <div className={styles.root}>
      <div className={styles.main}>
        <Image
          src={current.url}
          alt={current.alt_text ?? productName}
          fill
          className={styles.mainImage}
          sizes="(min-width: 56rem) 50vw, 100vw"
          priority
        />
      </div>

      {images.length > 1 && (
        <div className={styles.thumbs}>
          {images.map((image, index) => (
            <button
              key={image.id}
              type="button"
              className={`${styles.thumb} ${index === active ? styles.thumbActive : ''}`}
              onClick={() => setActive(index)}
              aria-label={`View image ${index + 1} of ${images.length}`}
              aria-current={index === active}
            >
              <Image
                src={image.url}
                alt=""
                fill
                className={styles.thumbImage}
                sizes="72px"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
