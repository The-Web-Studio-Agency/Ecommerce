'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';

import { addressApi } from '@/lib/api/addresses';
import { ApiError, ApiUnreachableError } from '@/lib/api/errors';
import { checkoutApi, couponApi, orderApi } from '@/lib/api/orders';
import { getAccessToken } from '@/lib/auth/session';
import type { CheckoutState } from '@/lib/orders/state';

function toState(error: unknown): CheckoutState {
  if (error instanceof ApiError) {
    return {
      status: 'error',
      message: error.message,
      fieldErrors: error.fieldErrors(),
      requestId: error.requestId,
    };
  }

  if (error instanceof ApiUnreachableError) {
    return { status: 'error', message: 'Could not reach Zeen. Try again in a moment.' };
  }

  throw error;
}

export async function saveAddress(_previous: CheckoutState, formData: FormData): Promise<CheckoutState> {
  const token = await getAccessToken();
  if (!token) return { status: 'error', message: 'Sign in to continue.' };

  const payload = {
    full_name: String(formData.get('full_name') ?? '').trim(),
    phone: String(formData.get('phone') ?? '').trim(),
    address_line_1: String(formData.get('address_line_1') ?? '').trim(),
    address_line_2: String(formData.get('address_line_2') ?? '').trim() || null,
    city: String(formData.get('city') ?? '').trim(),
    state: String(formData.get('state') ?? '').trim(),
    postal_code: String(formData.get('postal_code') ?? '').trim(),
    country: String(formData.get('country') ?? 'India').trim(),
    is_default: formData.get('is_default') === 'on',
  };

  try {
    await addressApi.create(token, payload);
  } catch (error) {
    return toState(error);
  }

  revalidatePath('/checkout');
  revalidatePath('/account/addresses');
  return { status: 'success', message: 'Address saved' };
}

export async function deleteAddress(_previous: CheckoutState, formData: FormData): Promise<CheckoutState> {
  const token = await getAccessToken();
  if (!token) return { status: 'error', message: 'Sign in to continue.' };

  try {
    await addressApi.remove(token, String(formData.get('address_id') ?? ''));
  } catch (error) {
    return toState(error);
  }

  revalidatePath('/account/addresses');
  return { status: 'success', message: 'Address removed' };
}

/** Validates a code against the live cart and reports what it takes off. */
export async function applyCoupon(_previous: CheckoutState, formData: FormData): Promise<CheckoutState> {
  const token = await getAccessToken();
  if (!token) return { status: 'error', message: 'Sign in to continue.' };

  const code = String(formData.get('code') ?? '').trim();
  if (!code) return { status: 'error', message: 'Enter a code.' };

  try {
    const result = await couponApi.apply(token, code);
    revalidatePath('/checkout');
    return { status: 'success', message: `${result.code} applied`, couponCode: result.code };
  } catch (error) {
    return toState(error);
  }
}

/**
 * Place the order.
 *
 * Only the address and an optional coupon are sent. Every price is computed
 * by the backend from the cart, so nothing about money crosses from here.
 * The idempotency key makes a double submit safe: the original order comes
 * back rather than a second one being created.
 */
export async function placeOrder(_previous: CheckoutState, formData: FormData): Promise<CheckoutState> {
  const token = await getAccessToken();
  if (!token) return { status: 'error', message: 'Sign in to continue.' };

  const addressId = String(formData.get('address_id') ?? '');
  if (!addressId) return { status: 'error', message: 'Choose a delivery address.' };

  const couponCode = String(formData.get('coupon_code') ?? '').trim() || null;
  const idempotencyKey = String(formData.get('idempotency_key') ?? '') || crypto.randomUUID();

  let orderId: string;

  try {
    const order = await checkoutApi.placeOrder(token, { addressId, couponCode, idempotencyKey });
    orderId = order.id;
  } catch (error) {
    return toState(error);
  }

  revalidatePath('/orders');
  revalidatePath('/cart');
  revalidatePath('/', 'layout');

  // The real order id from the backend, never a fabricated one.
  redirect(`/orders/${orderId}?placed=1`);
}

export async function cancelOrder(_previous: CheckoutState, formData: FormData): Promise<CheckoutState> {
  const token = await getAccessToken();
  if (!token) return { status: 'error', message: 'Sign in to continue.' };

  const orderId = String(formData.get('order_id') ?? '');

  try {
    await orderApi.cancel(token, orderId);
  } catch (error) {
    return toState(error);
  }

  revalidatePath(`/orders/${orderId}`);
  revalidatePath('/orders');
  return { status: 'success', message: 'Order cancelled' };
}
