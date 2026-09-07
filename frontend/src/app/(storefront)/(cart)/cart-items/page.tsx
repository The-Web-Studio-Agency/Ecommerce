import CommanLayout from '@/components/CommanLayout';
import CommonBanner2 from '@/components/CommonBanner2';
import { checkoutApi } from '@/lib/api/orders';
import { getAccessToken } from '@/lib/auth/session';
import Cart from './_components/Cart';

/**
 * The cart is open to guests, so the checkout preview is best-effort: it
 * needs a session, and an empty cart has nothing to price.
 */
export default async function CartPage() {
  const token = await getAccessToken();
  const preview = token ? await checkoutApi.preview(token).catch(() => null) : null;

  return (
    <CommanLayout>
      <CommonBanner2 parentText="Home" currentText="Cart" mainText="Shop Standard" />
      <Cart preview={preview} />
    </CommanLayout>
  );
}
