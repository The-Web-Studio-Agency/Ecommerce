import styles from './VisuallyHidden.module.css';

export default function VisuallyHidden({ children }: { children: React.ReactNode }) {
  return <span className={styles.root}>{children}</span>;
}
