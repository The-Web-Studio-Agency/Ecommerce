import CommanLayout from '@/components/CommanLayout';
import CommonBanner2 from '@/components/CommonBanner2';
import Checkout from './_components/Checkout';

export default function CheckOutPage() {
  return (
    <CommanLayout>
      <CommonBanner2 parentText="Cart" currentText="Checkout" mainText="Shop Standard"></CommonBanner2>
       <Checkout/>
    </CommanLayout>
  );
}
