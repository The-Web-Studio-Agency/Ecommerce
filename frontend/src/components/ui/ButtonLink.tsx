import Link from 'next/link';

import styles from './Button.module.css';
import type { ButtonSize, ButtonVariant } from './Button';

/**
 * A link that reads as a button. Kept separate from Button so navigation
 * stays an anchor -- openable in a new tab, and announced as a link.
 */
export default function ButtonLink({
  href,
  variant = 'primary',
  size = 'md',
  block = false,
  className,
  children,
}: {
  href: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  block?: boolean;
  className?: string;
  children: React.ReactNode;
}) {
  const classes = [styles.root, styles[variant], styles[size], block ? styles.block : '', className]
    .filter(Boolean)
    .join(' ');

  return (
    <Link href={href} className={classes} style={{ textDecoration: 'none' }}>
      {children}
    </Link>
  );
}
