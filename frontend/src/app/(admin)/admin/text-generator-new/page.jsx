import Breadcrumb from "@/components/admin-components/Breadcrumb";
import TermsConditionLayer from "@/components/admin-components/TermsConditionLayer";
import TextGeneratorNewLayer from "@/components/admin-components/TextGeneratorNewLayer";
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
        <Breadcrumb title='Text Generator' />

        {/* TextGeneratorNewLayer */}
        <TextGeneratorNewLayer />
      </MasterLayout>
    </>
  );
};

export default Page;
