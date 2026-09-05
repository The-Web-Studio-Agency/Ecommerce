import AverageDailySales from "./child/AverageDailySales";
import MonthlyCampaignState from "./child/MonthlyCampaignState";
import RecentActivityOne from "./child/RecentActivityOne";
import RevenueStatisticOne from "./child/RevenueStatisticOne";
import SalesByCountries from "./child/SalesByCountries";
import SourceVisitors from "./child/SourceVisitors";
import SupportTracker from "./child/SupportTracker";
import TransactionsTwo from "./child/TransactionsTwo";
import UpgradeYourPlan from "./child/UpgradeYourPlan";

const DashBoardLayerNine = () => {
  return (
    <div className='row gy-4'>
      {/* UpgradeYourPlan */}
      <UpgradeYourPlan />

      {/* RevenueStatisticOne */}
      <RevenueStatisticOne />

      {/* SupportTracker */}
      <SupportTracker />

      {/* AverageDailySales */}
      <AverageDailySales />

      {/* TransactionsTwo */}
      <TransactionsTwo />

      {/* SalesByCountries */}
      <SalesByCountries />

      {/* SourceVisitors */}
      <SourceVisitors />

      {/* MonthlyCampaignState */}
      <MonthlyCampaignState />

      {/* RecentActivityOne */}
      <RecentActivityOne />
    </div>
  );
};

export default DashBoardLayerNine;
