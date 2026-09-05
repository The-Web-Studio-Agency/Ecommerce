import Badge, { type BadgeTone } from '@/components/ui/Badge';
import type { OrderStatus, PaymentStatus } from '@/types/orders';

const ORDER_TONES: Record<OrderStatus, BadgeTone> = {
  PENDING: 'neutral',
  CONFIRMED: 'accent',
  PROCESSING: 'accent',
  SHIPPED: 'accent',
  DELIVERED: 'positive',
  CANCELLED: 'critical',
};

const PAYMENT_TONES: Record<PaymentStatus, BadgeTone> = {
  PENDING: 'caution',
  PAID: 'positive',
  FAILED: 'critical',
  REFUNDED: 'neutral',
};

const ORDER_LABELS: Record<OrderStatus, string> = {
  PENDING: 'Placed',
  CONFIRMED: 'Confirmed',
  PROCESSING: 'Being packed',
  SHIPPED: 'On its way',
  DELIVERED: 'Delivered',
  CANCELLED: 'Cancelled',
};

const PAYMENT_LABELS: Record<PaymentStatus, string> = {
  PENDING: 'Pay on delivery',
  PAID: 'Paid',
  FAILED: 'Payment failed',
  REFUNDED: 'Refunded',
};

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  return <Badge tone={ORDER_TONES[status]}>{ORDER_LABELS[status]}</Badge>;
}

export function PaymentStatusBadge({ status }: { status: PaymentStatus }) {
  return <Badge tone={PAYMENT_TONES[status]}>{PAYMENT_LABELS[status]}</Badge>;
}

export { ORDER_LABELS };
