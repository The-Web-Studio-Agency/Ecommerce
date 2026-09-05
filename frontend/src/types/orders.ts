export type OrderStatus =
  | 'PENDING'
  | 'CONFIRMED'
  | 'PROCESSING'
  | 'SHIPPED'
  | 'DELIVERED'
  | 'CANCELLED';

export type PaymentStatus = 'PENDING' | 'PAID' | 'FAILED' | 'REFUNDED';

/** Cash on delivery is the only provider the backend implements. */
export type PaymentProvider = 'COD';

/** Which status an order may move to next. Mirrors ALLOWED_TRANSITIONS. */
export const ALLOWED_TRANSITIONS: Record<OrderStatus, readonly OrderStatus[]> = {
  PENDING: ['CONFIRMED', 'PROCESSING', 'CANCELLED'],
  CONFIRMED: ['PROCESSING', 'CANCELLED'],
  PROCESSING: ['SHIPPED', 'CANCELLED'],
  SHIPPED: ['DELIVERED'],
  DELIVERED: [],
  CANCELLED: [],
};

/** The statuses a customer may cancel from. */
export const CANCELLABLE_STATUSES: readonly OrderStatus[] = ['PENDING', 'CONFIRMED', 'PROCESSING'];

export interface Payment {
  id: string;
  order_id: string;
  amount: string;
  currency: string;
  status: PaymentStatus;
  provider: PaymentProvider;
  created_at: string;
}

export interface DeliveryAddress {
  full_name: string;
  phone: string;
  address_line_1: string;
  address_line_2: string | null;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

export interface OrderItem {
  product_id: string;
  variant_id: string;
  product_name: string;
  variant_name: string;
  sku: string;
  quantity: number;
  unit_price: string;
  subtotal: string;
}

export interface Order {
  id: string;
  order_number: string;
  status: OrderStatus;
  payment_status: PaymentStatus;
  items: OrderItem[];
  subtotal: string;
  coupon_code: string | null;
  discount_amount: string;
  shipping_amount: string;
  tax_amount: string;
  total_amount: string;
  currency: string;
  payment: Payment | null;
  delivery_address: DeliveryAddress;
  created_at: string;
}

/** A row in a list of orders. Carries no items, so listings stay cheap. */
export interface OrderSummary {
  id: string;
  order_number: string;
  status: OrderStatus;
  payment_status: PaymentStatus;
  total_amount: string;
  currency: string;
  created_at: string;
}

export interface CheckoutItem {
  product_id: string;
  variant_id: string;
  product_name: string;
  variant_name: string;
  sku: string;
  quantity: number;
  unit_price: string;
  subtotal: string;
}

/** The only place tax, shipping and the order total can be read before placing. */
export interface CheckoutPreview {
  items: CheckoutItem[];
  subtotal: string;
  coupon_code: string | null;
  discount_amount: string;
  shipping_amount: string;
  tax_amount: string;
  total_amount: string;
}

export interface CouponApplyResult {
  code: string;
  discount_amount: string;
  currency: string;
}
