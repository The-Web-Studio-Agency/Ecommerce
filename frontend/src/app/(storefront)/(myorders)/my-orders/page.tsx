import CommanLayout from '@/components/CommanLayout';
import CommonBanner2 from '@/components/CommonBanner2';
import MyOrders from './_components/MyOrders';

export default function MyOrdersPage() {
  return (
    <CommanLayout>
      {/* <ProtectedRoute> */}
      <CommonBanner2 parentText="Home" currentText="My Orders" mainText="Shop Standard" />
      <MyOrders />
      {/* </ProtectedRoute> */}
    </CommanLayout>
  );
}
