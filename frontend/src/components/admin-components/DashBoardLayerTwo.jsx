import CampaignStaticOne from "./child/CampaignStaticOne";
import ClientPaymentOne from "./child/ClientPaymentOne";
import CountryStatusOne from "./child/CountryStatusOne";
import EarningStaticOne from "./child/EarningStaticOne";
import LastTransactionOne from "./child/LastTransactionOne";
import LatestPerformanceOne from "./child/LatestPerformanceOne";
import RevenueGrowthOne from "./child/RevenueGrowthOne";
import TopPerformanceOne from "./child/TopperformanceOne";
import UnitCountTwo from "./child/UnitCountTwo";

const DashBoardLayerTwo = () => {
  return (
    <section className='row gy-4'>
      {/* UnitCountTwo */}
      <UnitCountTwo />

      {/* RevenueGrowthOne */}
      <RevenueGrowthOne />

      {/* EarningStaticOne */}
      <EarningStaticOne />

      {/* CampaignStaticOne */}
      <CampaignStaticOne />

      {/* ClientPaymentOne  */}
      <ClientPaymentOne />

      {/* CountryStatusOne */}
      <CountryStatusOne />

      {/* TopPerformanceOne */}
      <TopPerformanceOne />

      {/* LatestPerformanceOne */}
      <LatestPerformanceOne />

      {/* LastTransactionOne */}
      <LastTransactionOne />
    </section>
  );
};

export default DashBoardLayerTwo;
