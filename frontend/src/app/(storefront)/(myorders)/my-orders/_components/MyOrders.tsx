'use client';

import { useState } from 'react';


function ArrowUpRightIcon({ className }: { className?: string }) {
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
      <path d="M7 17 17 7" />
      <path d="M7 7h10v10" />
    </svg>
  );
}

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

type OrderStatus = 'in_progress' | 'delayed' | 'canceled' | 'delivered';

interface Order {
  id: string;
  date: string;
  amount: number;
  status: OrderStatus;
}

interface StatusMeta {
  label: string;
  dotClassName: string;
  textClassName: string;
}

const ORDERS: Order[] = [
  { id: '34VB5540K83', date: '2025-01-21', amount: 358.75, status: 'in_progress' },
  { id: '78A643CD409', date: '2025-02-09', amount: 760.5, status: 'canceled' },
  { id: '112P45A9OV2', date: '2025-01-15', amount: 1264.0, status: 'delayed' },
  { id: '28BA67UO981', date: '2025-01-19', amount: 198.35, status: 'delivered' },
  { id: '5O2TR872W2', date: '2025-01-04', amount: 2133.9, status: 'delivered' },
  { id: '47H76GO9F33', date: '2025-01-30', amount: 86.4, status: 'delivered' },
  { id: '53U76GO9E38', date: '2025-01-21', amount: 86.4, status: 'delivered' },
  { id: '31M76GO9G76', date: '2025-01-07', amount: 112.4, status: 'delivered' },
];

const STATUS_META: Record<OrderStatus, StatusMeta> = {
  in_progress: {
    label: 'In progress',
    dotClassName: 'myorderDotBlue',
    textClassName: 'myorderTextBlue',
  },
  delayed: {
    label: 'Delayed',
    dotClassName: 'myorderDotAmber',
    textClassName: 'myorderTextAmber',
  },
  canceled: {
    label: 'Canceled',
    dotClassName: 'myorderDotRose',
    textClassName: 'myorderTextRose',
  },
  delivered: {
    label: 'Delivered',
    dotClassName: 'myorderDotEmerald',
    textClassName: 'myorderTextEmerald',
  },
};

type FilterValue = 'all' | OrderStatus;

const FILTERS: FilterValue[] = ['all', 'in_progress', 'delayed', 'delivered', 'canceled'];

function formatDate(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' });
}

function formatAmount(n: number): string {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
}

export default function MyOrders() {
  const [filter, setFilter] = useState<FilterValue>('all');

  const orders = filter === 'all' ? ORDERS : ORDERS.filter(o => o.status === filter);

//   const [orders, setOrders] = useState([]);
// const [loading, setLoading] = useState(true);
// const [error, setError] = useState('');

// useEffect(() => {
//   const fetchOrders = async () => {
//     try {
//       setLoading(true);
//       setError('');

//       const response = await fetch(
//         'http://localhost:5000/api/orders/my-orders',
//         {
//           method: 'GET',
//           credentials: 'include',
//         }
//       );

//       const data = await response.json();

//       if (!response.ok) {
//         throw new Error(data.message || 'Failed to fetch orders');
//       }

//       setOrders(data.orders);
//     } catch (error) {
//       console.error('Failed to fetch orders:', error);

//       if (error instanceof Error) {
//         setError(error.message);
//       } else {
//         setError('Something went wrong while fetching orders');
//       }
//     } finally {
//       setLoading(false);
//     }
//   };

//   fetchOrders();
// }, []);







  return (
    <div className="myorderPage">
      <div className="myorderContainer">
        <div className="myorderHeader">
          <div>
            <h1 className="myorderTitle">My orders</h1>
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
                  <th className="myorderTh">Order Id</th>
                  <th className="myorderTh">Order Place</th>
                  <th className="myorderTh">Total Amount</th>
                  <th className="myorderTh">Status</th>
                  <th className="myorderTh"></th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order, i) => {
                  const meta = STATUS_META[order.status];
                  const isLast = i === orders.length - 1;
                  return (
                    <tr key={order.id} className={`myorderRow ${!isLast ? 'myorderRowBorder' : ''}`}>
                      <td className="myorderTd myorderTdOrderId">#{order.id}</td>
                      <td className="myorderTd myorderTdDate">{formatDate(order.date)}</td>
                      <td className="myorderTd myorderTdAmount">{formatAmount(order.amount)}</td>
                      <td className="myorderTd">
                        <span className={`myorderStatusBadge ${meta.textClassName}`}>
                          <span className={`myorderStatusDot ${meta.dotClassName}`} />
                          {meta.label}
                        </span>
                      </td>
                      <td className="myorderTd myorderTdAction">
                        <button type="button" className="myorderViewButton">
                          View
                          <ArrowUpRightIcon className="myorderViewIcon" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {orders.length === 0 && (
            <div className="myorderEmptyState">
              <PackageSearchIcon className="myorderEmptyIcon" />
              <p className="myorderEmptyText">No orders with this status.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
