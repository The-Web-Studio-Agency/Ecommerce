import Breadcrumb from "@/components/admin-components/Breadcrumb";
import DashBoardLayerThree from "@/components/admin-components/DashBoardLayerThree";
import MasterLayout from "@/admin-masterLayout/MasterLayout";

export const metadata = {
  title: "WowDash NEXT JS - Admin Dashboard Multipurpose Bootstrap 5 Template",
  description:
    "Wowdash NEXT JS is a developer-friendly, ready-to-use admin template designed for building attractive, scalable, and high-performing web applications.",
};

const Page = () => {
  return (
    <>
      {/* MasterLayout */}
      <MasterLayout>
        {/* Breadcrumb */}
        <Breadcrumb title='eCommerce' />

        {/* DashBoardLayerThree */}
        <DashBoardLayerThree />
      </MasterLayout>
    </>
  );
};

export default Page;
