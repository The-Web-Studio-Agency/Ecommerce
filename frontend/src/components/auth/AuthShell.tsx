import Link from 'next/link';

import styles from './AuthShell.module.css';

export default function AuthShell({
  title,
  lede,
  children,
}: {
  title: string;
  lede?: string;
  children: React.ReactNode;
}) {
  return (
    <main className={styles.root}>
      <div className={styles.panel}>
        <Link href="/" className={styles.wordmark}>
          Zeen
        </Link>

        <h1 className={styles.title}>{title}</h1>
        {lede && <p className={styles.lede}>{lede}</p>}

        {children}
      </div>
    </main>
  );
}

export { styles as authStyles };
