import CommonBanner2 from '@/components/CommonBanner2';
import CommanLayout from '@/components/CommanLayout';
import OrderSuccess from '../_components/OrderSuccess';

export default async function OrderSuccessPage({ params }: { params: Promise<{ orderId: string }> }) {
    const {orderId} = await params;
  return (
    <CommanLayout>
      {/* <ProtectedRoute> */}
      <CommonBanner2 parentText="CheckOut" currentText="Order Success" mainText="Shop Standard" />
      <OrderSuccess orderId={orderId} />
      {/* </ProtectedRoute> */}
    </CommanLayout>
  );
}
