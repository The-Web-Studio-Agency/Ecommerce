import AddUserLayer from "@/components/admin-components/AddUserLayer";
import Breadcrumb from "@/components/admin-components/Breadcrumb";
import ColorsLayer from "@/components/admin-components/ColorsLayer";
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
        <Breadcrumb title='Components / Colors' />

        {/* ColorsLayer */}
        <ColorsLayer />
      </MasterLayout>
    </>
  );
};

export default Page;
