import { apiRequest, apiRequestPage } from '@/lib/api/client';
import type { Page, PageParams } from '@/types/api';
import type {
  Coupon,
  DashboardOverview,
  SalesTrendItem,
  ShippingSettings,
  TaxSettings,
  TopSellingProductItem,
} from '@/types/admin';
import type { Order, OrderStatus, OrderSummary, Payment, PaymentStatus } from '@/types/orders';
import type { Review } from '@/types/reviews';

/**
 * Admin endpoints. Reads generally need STAFF, writes need ADMIN.
 *
 * The backend is the authority on that -- these calls will 403 for the
 * wrong role regardless of what the UI chooses to show.
 */
export const adminApi = {
  dashboard(token: string): Promise<DashboardOverview> {
    return apiRequest<DashboardOverview>('/admin/dashboard', { token, cache: 'no-store' });
  },

  salesTrend(token: string, days = 30): Promise<SalesTrendItem[]> {
    return apiRequest<SalesTrendItem[]>('/admin/dashboard/sales-trend', {
      query: { days },
      token,
      cache: 'no-store',
    });
  },

  topProducts(token: string, options: { days?: number; limit?: number } = {}): Promise<TopSellingProductItem[]> {
    return apiRequest<TopSellingProductItem[]>('/admin/dashboard/top-products', {
      query: { days: options.days, limit: options.limit },
      token,
      cache: 'no-store',
    });
  },

  listOrders(
    token: string,
    query: PageParams & {
      order_number?: string;
      status?: OrderStatus;
      payment_status?: PaymentStatus;
    } = {},
  ): Promise<Page<OrderSummary>> {
    return apiRequestPage<OrderSummary>('/admin/orders', { query: { ...query }, token, cache: 'no-store' });
  },

  getOrder(token: string, orderId: string): Promise<Order> {
    return apiRequest<Order>(`/admin/orders/${orderId}`, { token, cache: 'no-store' });
  },

  /** Transitions are validated server-side; only legal next states succeed. */
  updateOrderStatus(token: string, orderId: string, status: OrderStatus): Promise<Order> {
    return apiRequest<Order>(`/admin/orders/${orderId}/status`, {
      method: 'PATCH',
      body: { status },
      token,
      cache: 'no-store',
    });
  },

  listPayments(
    token: string,
    query: PageParams & { order_id?: string; status?: PaymentStatus } = {},
  ): Promise<Page<Payment>> {
    return apiRequestPage<Payment>('/admin/payments', { query: { ...query }, token, cache: 'no-store' });
  },

  getPayment(token: string, paymentId: string): Promise<Payment> {
    return apiRequest<Payment>(`/admin/payments/${paymentId}`, { token, cache: 'no-store' });
  },

  listCoupons(token: string, query: PageParams & { active_only?: boolean } = {}): Promise<Page<Coupon>> {
    return apiRequestPage<Coupon>('/admin/coupons', { query: { ...query }, token, cache: 'no-store' });
  },

  getCoupon(token: string, couponId: string): Promise<Coupon> {
    return apiRequest<Coupon>(`/admin/coupons/${couponId}`, { token, cache: 'no-store' });
  },

  listReviews(token: string, query: PageParams & { is_approved?: boolean } = {}): Promise<Page<Review>> {
    return apiRequestPage<Review>('/admin/reviews', { query: { ...query }, token, cache: 'no-store' });
  },

  moderateReview(token: string, reviewId: string, isApproved: boolean): Promise<Review> {
    return apiRequest<Review>(`/admin/reviews/${reviewId}`, {
      method: 'PATCH',
      body: { is_approved: isApproved },
      token,
      cache: 'no-store',
    });
  },

  getShippingSettings(token: string): Promise<ShippingSettings> {
    return apiRequest<ShippingSettings>('/admin/shipping', { token, cache: 'no-store' });
  },

  getTaxSettings(token: string): Promise<TaxSettings> {
    return apiRequest<TaxSettings>('/admin/tax', { token, cache: 'no-store' });
  },
};
