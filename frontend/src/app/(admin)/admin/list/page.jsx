import Breadcrumb from "@/components/admin-components/Breadcrumb";
import ListLayer from "@/components/admin-components/ListLayer";
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
        <Breadcrumb title='Components / List' />

        {/* ListLayer */}
        <ListLayer />
      </MasterLayout>
    </>
  );
};

export default Page;
