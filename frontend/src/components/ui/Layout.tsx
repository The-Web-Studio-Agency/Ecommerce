import styles from './Layout.module.css';

type Width = 'default' | 'narrow' | 'text';

export function Container({
  width = 'default',
  className,
  children,
}: {
  width?: Width;
  className?: string;
  children: React.ReactNode;
}) {
  const widthClass = width === 'narrow' ? styles.narrow : width === 'text' ? styles.text : '';

  return <div className={[styles.container, widthClass, className].filter(Boolean).join(' ')}>{children}</div>;
}

export function Section({ className, children }: { className?: string; children: React.ReactNode }) {
  return <section className={[styles.section, className].filter(Boolean).join(' ')}>{children}</section>;
}

type Gap = 2 | 3 | 4 | 5 | 6;

/** Vertical rhythm from one place, so siblings never fight over margins. */
export function Stack({
  gap = 4,
  className,
  children,
}: {
  gap?: Gap;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={[styles.stack, styles[`gap${gap}`], className].filter(Boolean).join(' ')}>{children}</div>
  );
}
