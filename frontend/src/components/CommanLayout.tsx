import Header from './Header';
import Footer from './Footer';
import MainFooter from './MainFoooter';

interface Props {
  children: React.ReactNode;
}

const CommanLayout = ({ children }: Props) => {
  return (
    <div className="page-wraper">
      <Header design="" />
      {children}
      <MainFooter />
    </div>
  );
};
export default CommanLayout;
