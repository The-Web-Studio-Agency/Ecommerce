import CommonBanner2 from '@/components/CommonBanner2';
import CommanLayout from '@/components/CommanLayout';
import Invoice from '../_components/Invoice';

export default async function InvoicePage({ params }: { params: Promise<{ orderId: string }> }) {
  const { orderId } = await params;
  return (
    <CommanLayout>
      {/* <ProtectedRoute> */}
      <CommonBanner2 parentText="CheckOut" currentText="Order Success" mainText="Shop Standard" />
      <Invoice orderId={orderId} />
      {/* </ProtectedRoute> */}
    </CommanLayout>
  );
}
