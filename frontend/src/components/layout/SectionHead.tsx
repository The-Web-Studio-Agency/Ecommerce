import Link from 'next/link';

import styles from './SectionHead.module.css';

export default function SectionHead({
  title,
  href,
  linkLabel,
}: {
  title: string;
  href?: string;
  linkLabel?: string;
}) {
  return (
    <div className={styles.head}>
      <h2 className={styles.title}>{title}</h2>

      {href && linkLabel && (
        <Link href={href} className={styles.link}>
          {linkLabel}
        </Link>
      )}
    </div>
  );
}
