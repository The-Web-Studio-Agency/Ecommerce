import Breadcrumb from "@/components/admin-components/Breadcrumb";
import ErrorLayer from "@/components/admin-components/ErrorLayer";
import MasterLayout from "@/admin-masterLayout/MasterLayout";

export default function NotFound() {
  return (
    <>
      {/* MasterLayout */}
      <MasterLayout>
        {/* Breadcrumb */}
        <Breadcrumb title='404' />

        {/* ErrorLayer */}
        <ErrorLayer />
      </MasterLayout>
    </>
  );
}
