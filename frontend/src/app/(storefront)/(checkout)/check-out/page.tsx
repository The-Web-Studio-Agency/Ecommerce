import CommanLayout from '@/components/CommanLayout';
import { checkoutApi } from '@/lib/api/orders';
import { getAccessToken } from '@/lib/auth/session';
import Checkout from './_components/Checkout';

/**
 * Price the cart before the form renders.
 *
 * Middleware has already turned guests away, so a missing preview here means
 * an empty cart or a backend that is down -- the form handles both.
 */
export default async function CheckoutPageRoute() {
  const token = await getAccessToken();
  const preview = token ? await checkoutApi.preview(token).catch(() => null) : null;

  return (
    <CommanLayout>
      <Checkout initialPreview={preview} />
    </CommanLayout>
  );
}
