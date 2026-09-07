'use client';

import Link from 'next/link';
import { useState } from 'react';

import { formatDate, formatMoney } from '@/lib/format';
import type { OrderStatus, OrderSummary } from '@/types/orders';

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

interface StatusMeta {
  label: string;
  dotClassName: string;
  textClassName: string;
}

/** The backend's six statuses, mapped onto the template's four badge colours. */
const STATUS_META: Record<OrderStatus, StatusMeta> = {
  PENDING: {
    label: 'Pending',
    dotClassName: 'myorderDotAmber',
    textClassName: 'myorderTextAmber',
  },
  CONFIRMED: {
    label: 'Confirmed',
    dotClassName: 'myorderDotBlue',
    textClassName: 'myorderTextBlue',
  },
  PROCESSING: {
    label: 'Processing',
    dotClassName: 'myorderDotBlue',
    textClassName: 'myorderTextBlue',
  },
  SHIPPED: {
    label: 'Shipped',
    dotClassName: 'myorderDotBlue',
    textClassName: 'myorderTextBlue',
  },
  DELIVERED: {
    label: 'Delivered',
    dotClassName: 'myorderDotEmerald',
    textClassName: 'myorderTextEmerald',
  },
  CANCELLED: {
    label: 'Cancelled',
    dotClassName: 'myorderDotRose',
    textClassName: 'myorderTextRose',
  },
};

type FilterValue = 'all' | OrderStatus;

const FILTERS: FilterValue[] = ['all', 'PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED'];

export default function MyOrders({ orders: allOrders }: { orders: OrderSummary[] }) {
  const [filter, setFilter] = useState<FilterValue>('all');

  const orders = filter === 'all' ? allOrders : allOrders.filter(order => order.status === filter);

  return (
    <div className="myorderPage">
      <div className="myorderContainer">
        <div className="myorderHeader">
          <div>
            <h1 className="myorderTitle">My orders</h1>
          </div>
        </div>
        {orders.length!==0 &&
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
        }

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
                      <td className="myorderTd myorderTdOrderId">#{order.order_number}</td>
                      <td className="myorderTd myorderTdDate">{formatDate(order.created_at)}</td>
                      <td className="myorderTd myorderTdAmount">
                        {formatMoney(order.total_amount, order.currency)}
                      </td>
                      <td className="myorderTd">
                        <span className={`myorderStatusBadge ${meta.textClassName}`}>
                          <span className={`myorderStatusDot ${meta.dotClassName}`} />
                          {meta.label}
                        </span>
                      </td>
                      <td className="myorderTd myorderTdAction">
                        <Link href={`/order-success/${order.id}`} className="myorderViewButton">
                          View
                          <ArrowUpRightIcon className="myorderViewIcon" />
                        </Link>
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
              <p className="myorderEmptyText">You haven't placed any orders yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
