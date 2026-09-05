'use server';

import { revalidatePath } from 'next/cache';

import { adminApi } from '@/lib/api/admin';
import { ApiError, ApiUnreachableError } from '@/lib/api/errors';
import { getAccessToken } from '@/lib/auth/session';
import type { CheckoutState } from '@/lib/orders/state';
import type { OrderStatus } from '@/types/orders';

function toState(error: unknown): CheckoutState {
  if (error instanceof ApiError) return { status: 'error', message: error.message };
  if (error instanceof ApiUnreachableError) {
    return { status: 'error', message: 'Could not reach the API. Try again.' };
  }
  throw error;
}

/** Transitions are validated by the backend; an illegal one comes back 400. */
export async function updateOrderStatus(
  _previous: CheckoutState,
  formData: FormData,
): Promise<CheckoutState> {
  const token = await getAccessToken();
  if (!token) return { status: 'error', message: 'Sign in again.' };

  const orderId = String(formData.get('order_id') ?? '');
  const status = String(formData.get('status') ?? '') as OrderStatus;

  try {
    await adminApi.updateOrderStatus(token, orderId, status);
  } catch (error) {
    return toState(error);
  }

  revalidatePath(`/admin/orders/${orderId}`);
  revalidatePath('/admin/orders');
  revalidatePath('/admin');
  return { status: 'success', message: 'Status updated' };
}

export async function moderateReview(
  _previous: CheckoutState,
  formData: FormData,
): Promise<CheckoutState> {
  const token = await getAccessToken();
  if (!token) return { status: 'error', message: 'Sign in again.' };

  const reviewId = String(formData.get('review_id') ?? '');
  const approve = formData.get('is_approved') === 'true';

  try {
    await adminApi.moderateReview(token, reviewId, approve);
  } catch (error) {
    return toState(error);
  }

  revalidatePath('/admin/reviews');
  return { status: 'success', message: approve ? 'Review approved' : 'Review hidden' };
}
