import CommanLayout from '@/components/CommanLayout';
import CommonBanner2 from '@/components/CommonBanner2';
import SignIn from '@/components/SignIn';

export default function SignInPage() {
  return (
    <CommanLayout>
      <CommonBanner2 parentText="Home" currentText="Sign In" mainText="Shop Standard"></CommonBanner2>
      <SignIn />
    </CommanLayout>
  );
}
