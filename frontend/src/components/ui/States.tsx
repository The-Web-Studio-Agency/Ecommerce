import VisuallyHidden from './VisuallyHidden';
import styles from './States.module.css';

/** A placeholder shaped like the content it stands in for. */
export function Skeleton({
  width = '100%',
  height = '1rem',
  radius,
}: {
  width?: string;
  height?: string;
  radius?: string;
}) {
  return <div className={styles.skeleton} style={{ width, height, borderRadius: radius }} aria-hidden="true" />;
}

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return (
    <>
      <span className={styles.spinner} aria-hidden="true" />
      <VisuallyHidden>{label}</VisuallyHidden>
    </>
  );
}

/** An empty screen is an invitation to act, so it carries the next step. */
export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className={styles.state}>
      <h2 className={styles.title}>{title}</h2>
      {body && <p className={styles.body}>{body}</p>}
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}

/**
 * Says what went wrong and what to do about it. No apology, and never
 * vague -- the request id is included so support can trace the failure.
 */
export function ErrorState({
  title = 'That did not load',
  body = 'Something went wrong on our side. Try again in a moment.',
  requestId,
  action,
}: {
  title?: string;
  body?: string;
  requestId?: string | null;
  action?: React.ReactNode;
}) {
  return (
    <div className={styles.state} role="alert">
      <h2 className={styles.title}>{title}</h2>
      <p className={styles.body}>{body}</p>
      {requestId && <p className={styles.body}>Reference {requestId}</p>}
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}
