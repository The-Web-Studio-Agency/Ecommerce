export interface CheckoutState {
  status: 'idle' | 'success' | 'error';
  message: string | null;
  fieldErrors?: Record<string, string>;
  requestId?: string | null;
  couponCode?: string;
}

export const initialCheckoutState: CheckoutState = { status: 'idle', message: null };
