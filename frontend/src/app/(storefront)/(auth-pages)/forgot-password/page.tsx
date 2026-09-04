import CommanLayout from '@/components/CommanLayout';
import CommonBanner2 from '@/components/CommonBanner2';
import ForgotPassword from '@/components/ForgotPassword';

export default function ForgotPasswordPage() {
  return (
    <CommanLayout>
      <CommonBanner2 parentText="SignIn" currentText="Forgot Password" mainText="Shop Standard"></CommonBanner2>
      <ForgotPassword />
    </CommanLayout>
  );
}
