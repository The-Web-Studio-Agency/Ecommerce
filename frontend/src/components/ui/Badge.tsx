import styles from './Badge.module.css';

export type BadgeTone = 'neutral' | 'accent' | 'positive' | 'caution' | 'critical';

/** Encodes state, so status reads at a glance rather than only as text. */
export default function Badge({
  tone = 'neutral',
  children,
}: {
  tone?: BadgeTone;
  children: React.ReactNode;
}) {
  return <span className={`${styles.root} ${styles[tone]}`}>{children}</span>;
}
