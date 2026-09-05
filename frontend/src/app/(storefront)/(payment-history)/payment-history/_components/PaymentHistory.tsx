'use client';

import { useState } from 'react';

function PackageSearchIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true">
      <path d="M21 10V7a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 7v10a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l1.5-.86" />
      <path d="M3.29 7 12 12l8.71-5" />
      <path d="M12 22V12" />
      <circle cx="18.5" cy="15.5" r="2.5" />
      <path d="M20.27 17.27 22 19" />
    </svg>
  );
}

type PaymentStatus = 'paid' | 'pending' | 'failed' | 'refunded';

interface Payment {
  orderId: string;
  paymentId: string;
  method: string;
  amount: string;
  status: PaymentStatus;
}

interface StatusMeta {
  label: string;
  dotClassName: string;
  textClassName: string;
}

const PAYMENTS: Payment[] = [
  { orderId: 'ORD-1234', paymentId: 'pay_ABC123', method: 'UPI', amount: '₹2,814', status: 'paid' },
  { orderId: 'ORD-1235', paymentId: '—', method: 'COD', amount: '₹1,500', status: 'pending' },
  { orderId: 'ORD-1236', paymentId: 'pay_DEF456', method: 'Card', amount: '₹4,999', status: 'paid' },
  { orderId: 'ORD-1237', paymentId: 'pay_GHI789', method: 'Net Banking', amount: '₹899', status: 'failed' },
  { orderId: 'ORD-1238', paymentId: 'pay_JKL012', method: 'UPI', amount: '₹1,250', status: 'refunded' },
];

const STATUS_META: Record<PaymentStatus, StatusMeta> = {
  paid: {
    label: 'Paid',
    dotClassName: 'myorderDotEmerald',
    textClassName: 'myorderTextEmerald',
  },
  pending: {
    label: 'Pending',
    dotClassName: 'myorderDotAmber',
    textClassName: 'myorderTextAmber',
  },
  failed: {
    label: 'Failed',
    dotClassName: 'myorderDotRose',
    textClassName: 'myorderTextRose',
  },
  refunded: {
    label: 'Refunded',
    dotClassName: 'myorderDotBlue',
    textClassName: 'myorderTextBlue',
  },
};

type FilterValue = 'all' | PaymentStatus;

const FILTERS: FilterValue[] = ['all', 'paid', 'pending', 'failed', 'refunded'];

export default function PaymentHistory() {
  const [filter, setFilter] = useState<FilterValue>('all');

  const payments = filter === 'all' ? PAYMENTS : PAYMENTS.filter(p => p.status === filter);

  //   const [payments, setPayments] = useState([]);
  // const [loading, setLoading] = useState(true);
  // const [error, setError] = useState('');

  // useEffect(() => {
  //   const fetchPayments = async () => {
  //     try {
  //       setLoading(true);
  //       setError('');

  //       const response = await fetch(
  //         'http://localhost:5000/api/payments/my-payments',
  //         {
  //           method: 'GET',
  //           credentials: 'include',
  //         }
  //       );

  //       const data = await response.json();

  //       if (!response.ok) {
  //         throw new Error(data.message || 'Failed to fetch payments');
  //       }

  //       setPayments(data.payments);
  //     } catch (error) {
  //       console.error('Failed to fetch payments:', error);

  //       if (error instanceof Error) {
  //         setError(error.message);
  //       } else {
  //         setError('Something went wrong while fetching payments');
  //       }
  //     } finally {
  //       setLoading(false);
  //     }
  //   };

  //   fetchPayments();
  // }, []);

  return (
    <div className="myorderPage">
      <div className="myorderContainer">
        <div className="myorderHeader">
          <div>
            <h1 className="myorderTitle">Payments</h1>
          </div>
        </div>

        <div className="myorderFilters">
          {FILTERS.map(f => {
            const active = filter === f;
            const label = f === 'all' ? 'All' : STATUS_META[f].label;
            return (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className={`myorderFilterButton ${active ? 'myorderFilterButtonActive' : ''}`}>
                {label}
              </button>
            );
          })}
        </div>

        <div className="myorderTableCard">
          {/* Horizontal scroll wrapper: keeps the table usable on narrow screens */}
          <div className="myorderTableScroll">
            <table className="myorderTable">
              <thead>
                <tr className="myorderHeadRow">
                  <th className="myorderTh">Order ID</th>
                  <th className="myorderTh">Payment ID</th>
                  <th className="myorderTh">Method</th>
                  <th className="myorderTh">Amount</th>
                  <th className="myorderTh">Status</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((payment, i) => {
                  const meta = STATUS_META[payment.status];
                  const isLast = i === payments.length - 1;
                  return (
                    <tr key={payment.orderId} className={`myorderRow ${!isLast ? 'myorderRowBorder' : ''}`}>
                      <td className="myorderTd myorderTdOrderId">{payment.orderId}</td>
                      <td className="myorderTd myorderTdDate">{payment.paymentId}</td>
                      <td className="myorderTd myorderTdDate">{payment.method}</td>
                      <td className="myorderTd myorderTdAmount">{payment.amount}</td>
                      <td className="myorderTd">
                        <span className={`myorderStatusBadge ${meta.textClassName}`}>
                          <span className={`myorderStatusDot ${meta.dotClassName}`} />
                          {meta.label}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {payments.length === 0 && (
            <div className="myorderEmptyState">
              <PackageSearchIcon className="myorderEmptyIcon" />
              <p className="myorderEmptyText">No payments with this status.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}