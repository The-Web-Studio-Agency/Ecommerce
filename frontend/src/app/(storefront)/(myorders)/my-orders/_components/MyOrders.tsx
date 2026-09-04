'use client';

import { useState } from 'react';

/* ---------- Types ---------- */

type OrderStatus = 'In Progress' | 'Canceled' | 'Delayed' | 'Delivered';

interface Order {
  id: string;
  date: string;
  total: number;
  status: OrderStatus;
}

/* ---------- Data ----------
   In a real app, fetch this page of orders from your API instead. */

const STATUS_CLASS: Record<OrderStatus, string> = {
  'In Progress': 'my-order-status-in-progress',
  Canceled: 'my-order-status-canceled',
  Delayed: 'my-order-status-delayed',
  Delivered: 'my-order-status-delivered',
};

const ORDERS: Order[] = [
  { id: '#34VB5540K83', date: 'Jan 21, 2025', total: 358.75, status: 'In Progress' },
  { id: '#78A643CD409', date: 'Feb 09, 2025', total: 760.5, status: 'Canceled' },
  { id: '#112P45A90V2', date: 'Jan 15, 2025', total: 1264.0, status: 'Delayed' },
  { id: '#28BA67U0981', date: 'Jan 19, 2025', total: 198.35, status: 'Delivered' },
  { id: '#502TR872W2', date: 'Jan 04, 2025', total: 2133.9, status: 'Delivered' },
  { id: '#47H76G09F33', date: 'Jan 30, 2025', total: 86.4, status: 'Delivered' },
  { id: '#53U76G09E38', date: 'Jan 21, 2025', total: 86.4, status: 'Delivered' },
  { id: '#31M76G09G76', date: 'Jan 07, 2025', total: 112.4, status: 'Delivered' },
];

const TOTAL_PAGES = 3;

/* ---------- Component ---------- */

function StatusBadge({ status }: { status: OrderStatus }) {
  return <span className={`my-order-status-badge ${STATUS_CLASS[status]}`}>{status}</span>;
}

export default function MyOrders() {
  const [page, setPage] = useState(1);

  return (
    <div className="my-order-page">
      <div className="my-order-container">
        <h1 className="my-order-title">My Orders</h1>

        <div className="my-order-table-wrap">
          <table className="my-order-table">
            <thead>
              <tr className="my-order-thead-row">
                <th className="my-order-th my-order-th-left">Order ID</th>
                <th className="my-order-th my-order-th-left">Order Date</th>
                <th className="my-order-th my-order-th-left">Total Amount</th>
                <th className="my-order-th my-order-th-left">Order Status</th>
                <th className="my-order-th my-order-th-right">View Order</th>
              </tr>
            </thead>
            <tbody>
              {ORDERS.map((order, idx) => (
                <tr
                  key={order.id}
                  className={idx !== ORDERS.length - 1 ? 'my-order-row my-order-row-divider' : 'my-order-row'}>
                  <td className="my-order-td my-order-td-id">{order.id}</td>
                  <td className="my-order-td my-order-td-date">{order.date}</td>
                  <td className="my-order-td my-order-td-total">${order.total.toFixed(2)}</td>
                  <td className="my-order-td">
                    <StatusBadge status={order.status} />
                  </td>
                  <td className="my-order-td my-order-td-action">
                    <a href={`/orders/${order.id.replace('#', '')}`} className="my-order-view-link">
                      View
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="my-order-pagination">
          <button type="button" onClick={() => setPage(p => Math.max(1, p - 1))} className="my-order-page-nav-button">
            Prev
          </button>

          {Array.from({ length: TOTAL_PAGES }, (_, i) => i + 1).map(n => (
            <button
              key={n}
              type="button"
              onClick={() => setPage(n)}
              className={`my-order-page-number-button${page === n ? ' my-order-page-number-button-active' : ''}`}>
              {n}
            </button>
          ))}

          <button
            type="button"
            onClick={() => setPage(p => Math.min(TOTAL_PAGES, p + 1))}
            className="my-order-page-nav-button">
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
