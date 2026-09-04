'use client';

import { useEffect, useState } from 'react';

interface InvoiceMeta {
  number: string;
  orderId: string;
  issuedOn: string;
  dueOn: string;
  status: string;
  paymentMethod: string;
}

interface Party {
  name: string;
  address: string;
  email: string;
  phone: string;
}

interface Seller extends Party {
  gstin: string;
}

interface LineItem {
  id: number;
  title: string;
  size: string;
  qty: number;
  price: number;
}

interface OrderData {
  invoice: InvoiceMeta;
  seller: Seller;
  customer: Party;
  items: LineItem[];
}

interface InvoiceProps {
  orderId: string;
}

export default function Invoice({ orderId }: InvoiceProps) {
  const [order, setOrder] = useState<OrderData | null>(null);
  const [isLoading, setIsLoading] = useState(false); //true 
  const [isPrinting, setIsPrinting] = useState(false);

  /*
  ============================================================
  GET ORDER FROM SERVER
  ============================================================

  useEffect(() => {
    const getOrder = async () => {
      try {
        const response = await fetch(
          `http://localhost:5000/orders/${params.orderId}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch order');
        }

        const data = await response.json();

        setOrder(data);

      } catch (error) {
        console.error('Error fetching order:', error);
      } finally {
        setIsLoading(false);
      }
    };

    getOrder();
  }, [params.orderId]);
  ============================================================
  */

  /*
  TEMPORARY DATA
  Remove this after connecting your backend.
  */

  const invoice: InvoiceMeta = {
    number: 'INV-2026-00842',
    // IMPORTANT:
    // This now comes from the URL
    orderId: orderId,
    issuedOn: '3 September 2026',
    dueOn: '10 September 2026',
    status: 'Paid',
    paymentMethod: 'Visa •••• 4821',
  };

  const seller: Seller = {
    name: 'Zeeen',
    address: '4th Floor, Cinnamon House, Kozhikode, Kerala 673001',
    gstin: '32AACCA1234B1Z8',
    email: 'billingzeen@gmail.com',
    phone: '+91 495 123 4567',
  };

  const customer: Party = {
    name: 'Ananya Menon',
    address: '14, MG Road, Kozhikode, Kerala 673001',
    email: 'ananya.menon@email.com',
    phone: '+91 98765 43210',
  };

  const items: LineItem[] = [
    {
      id: 1,
      title: 'Ribbed Knit Cardigan',
      size: 'XS',
      qty: 1,
      price: 4999,
    },
    {
      id: 2,
      title: 'Sophisticated Swan Blouse',
      size: 'SM',
      qty: 1,
      price: 2499,
    },
  ];

  const subtotal = items.reduce((sum, item) => sum + item.price * item.qty, 0);

  const shipping: number = 0;

  const tax = Math.round(subtotal * 0.18);

  const total = subtotal + shipping + tax;

  const handleDownloadPdf = () => {
    setIsPrinting(true);

    setTimeout(() => {
      window.print();

      setTimeout(() => {
        setIsPrinting(false);
      }, 500);
    }, 100);
  };

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center">Loading invoice...</div>;
  }

  return (
    <div className="invoice-page">
      {/* Actions */}
      <div className="invoice-actions print:hidden">
        <button type="button" onClick={handleDownloadPdf} disabled={isPrinting} className="invoice-download-button">
          {isPrinting ? 'Preparing...' : 'Download PDF'}
        </button>

        <button type="button" onClick={() => window.print()} className="invoice-print-button">
          Print
        </button>
      </div>

      {/* Invoice */}
      <div className="invoice-sheet">
        {/* Header */}
        <div className="invoice-header">
          <div className="invoice-brand">
            <div className="invoice-brand-mark">
              <span>Z</span>
            </div>

            <div>
              <p className="invoice-seller-name">{seller.name}</p>

              <p className="invoice-seller-email">{seller.email}</p>
            </div>
          </div>

          <div className="invoice-title-block">
            <h1 className="invoice-title">INVOICE</h1>

            <p className="invoice-number invoice-mono">{invoice.number}</p>
          </div>
        </div>

        {/* Details */}
        <div className="invoice-details-grid">
          {/* Billed From */}
          <div className="invoice-bill-container">
            <div>
              <p className="invoice-label">Billed from</p>

              <p className="invoice-party-name">{seller.name}</p>

              <p className="invoice-party-line">{seller.address}</p>

              <p className="invoice-party-line">{seller.phone}</p>

              <p className="invoice-gstin">GSTIN: {seller.gstin}</p>
            </div>

            {/* Billed To */}
            <div>
              <p className="invoice-label">Billed to</p>

              <p className="invoice-party-name">{customer.name}</p>

              <p className="invoice-party-line">{customer.address}</p>

              <p className="invoice-party-line">{customer.email}</p>

              <p className="invoice-party-line">{customer.phone}</p>
            </div>
          </div>

          {/* Invoice Details */}
          <div>
            <p className="invoice-label">Invoice details</p>

            <div className="invoice-meta-grid">
              <span className="invoice-meta-key">Order ID</span>

              <span className="invoice-meta-value invoice-mono">{invoice.orderId}</span>

              <span className="invoice-meta-key">Issued</span>

              <span className="invoice-meta-value">{invoice.issuedOn}</span>

              <span className="invoice-meta-key">Due</span>

              <span className="invoice-meta-value">{invoice.dueOn}</span>
            </div>
          </div>

          {/* Payment */}
          <div>
            <p className="invoice-label">Payment</p>

            <span className="invoice-status-badge">
              <span className="invoice-status-dot" />

              {invoice.status}
            </span>

            <p className="invoice-payment-method">{invoice.paymentMethod}</p>
          </div>
        </div>

        {/* Items */}
        <div className="invoice-items-section">
          <div className="invoice-table-scroll">
            <table className="invoice-table">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Size</th>
                  <th className="invoice-th-center">Qty</th>
                  <th className="invoice-th-right">Price</th>
                  <th className="invoice-th-right">Amount</th>
                </tr>
              </thead>

              <tbody>
                {items.map(item => (
                  <tr key={item.id}>
                    <td className="invoice-item-title">{item.title}</td>

                    <td className="invoice-item-muted">{item.size}</td>

                    <td className="invoice-item-muted invoice-td-center">{item.qty}</td>

                    <td className="invoice-item-muted invoice-td-right invoice-mono">
                      ₹{item.price.toLocaleString('en-IN')}
                    </td>

                    <td className="invoice-item-amount invoice-td-right invoice-mono">
                      ₹{(item.price * item.qty).toLocaleString('en-IN')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Totals */}
          <div className="invoice-totals-row">
            <div className="invoice-totals-box">
              <div className="invoice-totals-line">
                <span>Subtotal</span>

                <span className="invoice-totals-value invoice-mono">₹{subtotal.toLocaleString('en-IN')}</span>
              </div>

              <div className="invoice-totals-line">
                <span>Shipping</span>

                <span className="invoice-totals-value invoice-mono">
                  {shipping === 0 ? 'Free' : `₹${shipping.toLocaleString('en-IN')}`}
                </span>
              </div>

              <div className="invoice-totals-line">
                <span>GST (18%)</span>

                <span className="invoice-totals-value invoice-mono">₹{tax.toLocaleString('en-IN')}</span>
              </div>

              <div className="invoice-grand-total">
                <span className="invoice-grand-total-label">Total</span>

                <span className="invoice-grand-total-value invoice-mono">₹{total.toLocaleString('en-IN')}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="invoice-footer">
          <div>
            <p className="invoice-thanks">Thank you for your business.</p>

            <p className="invoice-contact">Questions about this invoice? Contact {seller.email}</p>
          </div>

          <p className="invoice-footer-number invoice-mono">{invoice.number}</p>
        </div>
      </div>
    </div>
  );
}
