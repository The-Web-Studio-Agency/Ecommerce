import Link from 'next/link';

interface OrderItem {
  id: number;
  title: string;
  size: string;
  qty: number;
  price: number;
  image: string;
}

interface OrderSuccessProps {
  orderId: string;
}

/* ----- Mock data ----- */

const ORDER_ITEMS: OrderItem[] = [
  {
    id: 1,
    title: 'Ribbed Knit Cardigan',
    size: 'XS',
    qty: 1,
    price: 4999,
    image: '#EDEAE3',
  },
  {
    id: 2,
    title: 'Sophisticated Swan Blouse',
    size: 'SM',
    qty: 1,
    price: 2499,
    image: '#EFEFEF',
  },
   {
    id: 3,
    title: 'Sophisticated Swan Blouse',
    size: 'SM',
    qty: 1,
    price: 2499,
    image: '#EFEFEF',
  },

   {
    id: 4,
    title: 'Sophisticated Swan Blouse',
    size: 'SM',
    qty: 1,
    price: 2499,
    image: '#EFEFEF',
  },
   {
    id: 5,
    title: 'Sophisticated Swan Blouse',
    size: 'SM',
    qty: 1,
    price: 2499,
    image: '#EFEFEF',
  },

   {
    id: 6,
    title: 'Sophisticated Swan Blouse',
    size: 'SM',
    qty: 1,
    price: 2499,
    image: '#EFEFEF',
  },
   {
    id: 7,
    title: 'Sophisticated Swan Blouse',
    size: 'SM',
    qty: 1,
    price: 2499,
    image: '#EFEFEF',
  },
];

export default function OrderSuccess({ orderId }: OrderSuccessProps) {
  const subtotal = ORDER_ITEMS.reduce((s, i) => s + i.price * i.qty, 0);

  const shipping: number = 0;

  const tax = Math.round(subtotal * 0.18);

  const total = subtotal + shipping + tax;

  const placedOn = new Date().toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

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
          Thank you for your purchase. A confirmation has been sent to your email.
        </p>

        {/* Order Information */}
        <div className="order-success-meta">
          <div className="order-success-meta-item">
            <span className="order-success-meta-label">Order ID</span>

            <span className="order-success-meta-value">{orderId}</span>
          </div>

          <div className="order-success-meta-item">
            <span className="order-success-meta-label">Placed on</span>

            <span className="order-success-meta-value">{placedOn}</span>
          </div>
        </div>

        {/* Order Summary */}
        <div className="order-success-summary">
          <h2 className="order-success-summary-title">Order Summary</h2>

          <ul className="order-success-items">
            {ORDER_ITEMS.map(item => (
              <li key={item.id} className="order-success-item">
                <div
                  className="order-success-item-image"
                  style={{
                    backgroundColor: item.image,
                  }}
                />

                <div className="order-success-item-info">
                  <p className="order-success-item-title">{item.title}</p>

                  <p className="order-success-item-meta">Size: {item.size}</p>

                  <p className="order-success-item-meta">Qty: {item.qty}</p>
                </div>

                <div className="order-success-item-price">₹{item.price.toLocaleString('en-IN')}</div>
              </li>
            ))}
          </ul>

          {/* Totals */}
          <div className="order-success-totals">
            <div className="order-success-totals-row">
              <span>Subtotal</span>

              <span>₹{subtotal.toLocaleString('en-IN')}</span>
            </div>

            <div className="order-success-totals-row">
              <span>Shipping</span>

              <span>
                {' '}
                <span>{shipping === 0 ? 'Free' : `₹${shipping.toLocaleString('en-IN')}`}</span>
              </span>
            </div>

            <div className="order-success-totals-row">
              <span>GST (18%)</span>

              <span>₹{tax.toLocaleString('en-IN')}</span>
            </div>
          </div>

          {/* Final Total */}
          <div className="order-success-total-row">
            <span>Total Paid</span>

            <span>₹{total.toLocaleString('en-IN')}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="order-success-actions">
          <Link href={`/invoice/${orderId}`} className="order-success-button order-success-button-primary">
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
