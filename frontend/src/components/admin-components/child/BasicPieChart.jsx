"use client";
import useReactApexChart from "../../../hook/useReactApexChart";
import dynamic from "next/dynamic";
const ReactApexChart = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

const BasicPieChart = () => {
  let { pieChartSeriesOne, pieChartOptionsTwo } = useReactApexChart();
  return (
    <div className='col-md-6'>
      <div className='card h-100 p-0'>
        <div className='card-header border-bottom bg-base py-16 px-24'>
          <h6 className='text-lg fw-semibold mb-0'>Basic Pie Chart</h6>
        </div>
        <div className='card-body p-24 text-center'>
          <ReactApexChart
            id='pieChart'
            className='d-flex justify-content-center'
            options={pieChartOptionsTwo}
            series={pieChartSeriesOne}
            type='pie'
            height={264}
            width={380}
          />
        </div>
      </div>
    </div>
  );
};

export default BasicPieChart;
