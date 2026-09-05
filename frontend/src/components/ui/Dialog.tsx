'use client';

import { useEffect, useRef } from 'react';

import styles from './Dialog.module.css';

/**
 * Built on the native dialog element, which brings focus trapping, Escape
 * and inertness for free rather than reimplementing them.
 */
export default function Dialog({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;

    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog ref={ref} className={styles.dialog} onCancel={onClose} onClose={onClose}>
      <div className={styles.head}>
        <h2 className={styles.title}>{title}</h2>

        <button type="button" className={styles.close} onClick={onClose} aria-label="Close">
          &times;
        </button>
      </div>

      <div className={styles.body}>{children}</div>
    </dialog>
  );
}
