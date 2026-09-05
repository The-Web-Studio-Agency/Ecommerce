import Footer from '@/components/layout/Footer';
import Header from '@/components/layout/Header';

/**
 * The shopping surfaces share chrome. Sign-in and admin sit outside this
 * group so they can present without a storefront header around them.
 */
export default function ShellLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Header />
      {children}
      <Footer />
    </>
  );
}
