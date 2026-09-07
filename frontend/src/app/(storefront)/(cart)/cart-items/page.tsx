import CommanLayout from '@/components/CommanLayout';
import CommonBanner2 from '@/components/CommonBanner2';
import Cart from './_components/Cart';
import ProtectedRoute from '@/components/ProtectedRoute';

export default function CartPage() {
  return (
    <CommanLayout>
      {/* <ProtectedRoute> */}
        <CommonBanner2 parentText="Home" currentText="Cart" mainText="Shop Standard" />
        <Cart />
      {/* </ProtectedRoute> */}
    </CommanLayout>
  );
}
