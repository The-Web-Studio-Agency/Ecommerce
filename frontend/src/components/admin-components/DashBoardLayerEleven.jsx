import BalanceStatistic from "./child/BalanceStatistic";
import EarningCategories from "./child/EarningCategories";
import ExpenseStatistics from "./child/ExpenseStatistics";
import Investment from "./child/Investment";
import MonthlyExpenseBreakdown from "./child/MonthlyExpenseBreakdown";
import PaymentHistory from "./child/PaymentHistory";
import PaymentHistoryOne from "./child/PaymentHistoryOne";
import QuickTransfer from "./child/QuickTransfer";
import UnitCountEight from "./child/UnitCountEight";

const DashBoardLayerEleven = () => {
  return (
    <>
      {/* UnitCountEight */}
      <UnitCountEight />

      <div className='mt-24'>
        <div className='row gy-4'>
          <div className='col-xl-8'>
            <div className='row gy-4'>
              {/* BalanceStatistic */}
              <BalanceStatistic />

              {/* EarningCategories */}
              <EarningCategories />

              {/* ExpenseStatistics */}
              <ExpenseStatistics />

              {/* PaymentHistory */}
              <PaymentHistory />

              {/* MonthlyExpenseBreakdown */}
              <MonthlyExpenseBreakdown />
            </div>
          </div>
          {/* Sidebar start */}
          <div className='col-xl-4'>
            {/* QuickTransfer */}
            <QuickTransfer />

            {/* Investment */}
            <Investment />
          </div>
          {/* Sidebar end */}
        </div>
      </div>

      {/* PaymentHistoryOne */}
      <PaymentHistoryOne />
    </>
  );
};

export default DashBoardLayerEleven;
