type PaymentStatus = 'Paid' | 'Pending' | 'Failed' | 'Refunded';

interface Payment {
  orderId: string;
  paymentId: string | null;
  method: string;
  amount: number;
  status: PaymentStatus;
}

/* ---------- Data ----------
   In a real app, fetch this page of payments from your API instead. */

const STATUS_CLASS: Record<PaymentStatus, string> = {
  Paid: 'payment-history-status-paid',
  Pending: 'payment-history-status-pending',
  Failed: 'payment-history-status-failed',
  Refunded: 'payment-history-status-refunded',
};

const PAYMENTS: Payment[] = [
  { orderId: 'ORD-1234', paymentId: 'pay_ABC123', method: 'UPI', amount: 2814, status: 'Paid' },
  { orderId: 'ORD-1235', paymentId: null, method: 'COD', amount: 1500, status: 'Pending' },
  { orderId: 'ORD-1236', paymentId: 'pay_DEF456', method: 'Card', amount: 4999, status: 'Paid' },
  { orderId: 'ORD-1237', paymentId: 'pay_GHI789', method: 'Net Banking', amount: 899, status: 'Failed' },
  { orderId: 'ORD-1238', paymentId: 'pay_JKL012', method: 'UPI', amount: 1250, status: 'Refunded' },
];

/* ---------- Component ---------- */

function StatusBadge({ status }: { status: PaymentStatus }) {
  return <span className={`payment-history-status-badge ${STATUS_CLASS[status]}`}>{status}</span>;
}

export default function PaymentHistory() {
  return (
    <div className="payment-history-page">
      <div className="payment-history-container">
        <h1 className="payment-history-title">Payment History</h1>

        <div className="payment-history-table-wrap">
          <table className="payment-history-table">
            <thead>
              <tr className="payment-history-thead-row">
                <th className="payment-history-th">Order ID</th>
                <th className="payment-history-th">Payment ID</th>
                <th className="payment-history-th">Method</th>
                <th className="payment-history-th">Amount</th>
                <th className="payment-history-th">Status</th>
              </tr>
            </thead>
            <tbody>
              {PAYMENTS.map((p, idx) => (
                <tr
                  key={p.orderId}
                  className={
                    idx !== PAYMENTS.length - 1
                      ? 'payment-history-row payment-history-row-divider'
                      : 'payment-history-row'
                  }>
                  <td className="payment-history-td payment-history-td-id">{p.orderId}</td>
                  <td className="payment-history-td payment-history-td-payment-id payment-history-mono">
                    {p.paymentId ?? '—'}
                  </td>
                  <td className="payment-history-td payment-history-td-method">{p.method}</td>
                  <td className="payment-history-td payment-history-td-amount payment-history-mono">
                    ₹{p.amount.toLocaleString('en-IN')}
                  </td>
                  <td className="payment-history-td">
                    <StatusBadge status={p.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
