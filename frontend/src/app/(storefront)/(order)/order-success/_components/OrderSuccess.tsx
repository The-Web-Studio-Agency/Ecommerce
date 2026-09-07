import Link from 'next/link';

import { formatDate, formatMoney } from '@/lib/format';
import type { Order } from '@/types/orders';

/** Confirmation for one placed order, rendered from the order itself. */
export default function OrderSuccess({ order }: { order: Order }) {
  const money = (amount: string) => formatMoney(amount, order.currency);

  return (
    <div className="order-success">
      <div className="order-success-container">
        {/* Success Icon */}
        <div className="order-success-icon">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="11" stroke="currentColor" strokeWidth="1.5" />

            <path
              d="M7.5 12.5L10.3 15.3L16.5 9"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        {/* Heading */}
        <h1 className="order-success-title">Order placed successfully</h1>

        <p className="order-success-subtext">
          {"Thank you for your purchase. Your order is "}{order.status.toLowerCase()}.
        </p>

        {/* Order Information */}
        <div className="order-success-meta">
          <div className="order-success-meta-item">
            <span className="order-success-meta-label">Order ID</span>

            <span className="order-success-meta-value">{order.order_number}</span>
          </div>

          <div className="order-success-meta-item">
            <span className="order-success-meta-label">Placed on</span>

            <span className="order-success-meta-value">{formatDate(order.created_at)}</span>
          </div>
        </div>

        {/* Order Summary */}
        <div className="order-success-summary">
          <h2 className="order-success-summary-title">Order Summary</h2>

          <ul className="order-success-items">
            {order.items.map(item => (
              <li key={item.variant_id} className="order-success-item">
                <div className="order-success-item-info">
                  <p className="order-success-item-title">{item.product_name}</p>

                  <p className="order-success-item-meta">{item.variant_name}</p>

                  <p className="order-success-item-meta">Qty: {item.quantity}</p>
                </div>

                <div className="order-success-item-price">{money(item.subtotal)}</div>
              </li>
            ))}
          </ul>

          {/* Totals */}
          <div className="order-success-totals">
            <div className="order-success-totals-row">
              <span>Subtotal</span>

              <span>{money(order.subtotal)}</span>
            </div>

            {Number(order.discount_amount) > 0 && (
              <div className="order-success-totals-row">
                <span>Discount{order.coupon_code ? ` (${order.coupon_code})` : ''}</span>

                <span>−{money(order.discount_amount)}</span>
              </div>
            )}

            <div className="order-success-totals-row">
              <span>Shipping</span>

              <span>{Number(order.shipping_amount) === 0 ? 'Free' : money(order.shipping_amount)}</span>
            </div>

            <div className="order-success-totals-row">
              <span>Tax</span>

              <span>{money(order.tax_amount)}</span>
            </div>
          </div>

          {/* Final Total */}
          <div className="order-success-total-row">
            <span>Total Paid</span>

            <span>{money(order.total_amount)}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="order-success-actions">
          <Link href={`/invoice/${order.id}`} className="order-success-button order-success-button-primary">
            View Invoice
          </Link>

          <Link href="/" className="order-success-button order-success-button-secondary">
            Continue Shopping
          </Link>
        </div>
      </div>
    </div>
  );
}
