import { redirect } from 'next/navigation';

import homeStyles from '@/app/(storefront)/(home)/home/_components/luxe/Home.module.css';
import LuxeFooter from '@/components/luxe/LuxeFooter';
import LuxeHeader from '@/components/luxe/LuxeHeader';
import MobileBottomNav from '@/components/luxe/MobileBottomNav';
import { addressApi } from '@/lib/api/addresses';
import { getCurrentUser } from '@/lib/auth/current-user';
import { getAccessToken } from '@/lib/auth/session';
import { EMPTY_WISHLIST, getWishlist } from '@/lib/wishlist/read';

import MyProfile from './_components/MyProfile';

export const metadata = {
  title: 'My Profile | Zeen',
  description: 'Manage your Zeen profile, saved addresses, and wishlist.',
};

export default async function MyAccountPage() {
  const [token, user] = await Promise.all([getAccessToken(), getCurrentUser()]);
  if (!token || !user) redirect('/signin?next=/my-account');

  const [addresses, wishlist] = await Promise.all([
    addressApi.list(token).catch(() => []),
    getWishlist().catch(() => EMPTY_WISHLIST),
  ]);

  return (
    <div className={homeStyles.page}>
      <LuxeHeader />
      <MyProfile user={user} initialAddresses={addresses} initialWishlist={wishlist} />
      <LuxeFooter />
      <MobileBottomNav />
    </div>
  );
}
