import SignUp from '@/components/SignUp';
import CommanLayout from '@/components/CommanLayout';
import CommonBanner2 from '@/components/CommonBanner2';

export default function SignUpPage() {
  return (
    <CommanLayout>
      <CommonBanner2 parentText="Home" currentText="Sign Up" mainText="Shop Standard"></CommonBanner2>
      <SignUp />
    </CommanLayout>
  );
}
