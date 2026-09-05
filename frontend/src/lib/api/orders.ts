import { apiRequest, apiRequestPage } from '@/lib/api/client';
import type { Page, PageParams } from '@/types/api';
import type { CheckoutPreview, CouponApplyResult, Order, OrderSummary, Payment } from '@/types/orders';

export const checkoutApi = {
  /**
   * Price the cart before ordering.
   *
   * The only place discount, shipping, tax and total can be read before an
   * order exists. Passing an address lets the backend price delivery to it.
   */
  preview(token: string, options: { addressId?: string; couponCode?: string } = {}): Promise<CheckoutPreview> {
    return apiRequest<CheckoutPreview>('/checkout/preview', {
      method: 'POST',
      query: { coupon_code: options.couponCode },
      body: { address_id: options.addressId ?? null },
      token,
      cache: 'no-store',
    });
  },

  /**
   * Place the order.
   *
   * Takes only the address and an optional coupon: every price is computed
   * server-side from the cart, so nothing about money is sent from here.
   * The idempotency key makes a retry safe -- the original order comes back
   * rather than a duplicate being created.
   */
  placeOrder(
    token: string,
    input: { addressId: string; couponCode?: string | null; idempotencyKey: string },
  ): Promise<Order> {
    return apiRequest<Order>('/checkout', {
      method: 'POST',
      body: { address_id: input.addressId, coupon_code: input.couponCode ?? null },
      headers: { 'Idempotency-Key': input.idempotencyKey },
      token,
      cache: 'no-store',
    });
  },
};

export const orderApi = {
  list(token: string, params: PageParams = {}): Promise<Page<OrderSummary>> {
    return apiRequestPage<OrderSummary>('/orders', {
      query: { ...params },
      token,
      cache: 'no-store',
    });
  },

  get(token: string, orderId: string): Promise<Order> {
    return apiRequest<Order>(`/orders/${orderId}`, { token, cache: 'no-store' });
  },

  /** Allowed only while the order is pending, confirmed or processing. */
  cancel(token: string, orderId: string): Promise<Order> {
    return apiRequest<Order>(`/orders/${orderId}/cancel`, {
      method: 'POST',
      token,
      cache: 'no-store',
    });
  },
};

export const couponApi = {
  /** Validate a code against the live cart and return what it takes off. */
  apply(token: string, code: string): Promise<CouponApplyResult> {
    return apiRequest<CouponApplyResult>('/coupons/apply', {
      method: 'POST',
      body: { code },
      token,
      cache: 'no-store',
    });
  },
};

export const paymentApi = {
  /**
   * Look up one payment.
   *
   * There is no customer payment listing; payment history is built from the
   * order list, since each order carries its own payment.
   */
  get(token: string, paymentId: string): Promise<Payment> {
    return apiRequest<Payment>(`/payments/${paymentId}`, { token, cache: 'no-store' });
  },
};
