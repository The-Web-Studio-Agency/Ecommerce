import CommanLayout from '@/components/CommanLayout';
import CommonBanner2 from '@/components/CommonBanner2';
import PaymentHistory from './_components/PaymentHistory';
export default function PaymentHistoryPage() {
  return (
    <CommanLayout>
      {/* <ProtectedRoute> */}
      <CommonBanner2 parentText="Home" currentText="Payment History" mainText="Shop Standard" />
      <PaymentHistory />
      {/* </ProtectedRoute> */}
    </CommanLayout>
  );
}
