'use client';

import type { ApexOptions } from 'apexcharts';
import dynamic from 'next/dynamic';

import { formatMoney } from '@/lib/format';
import type { SalesTrendItem } from '@/types/admin';

const ReactApexChart = dynamic(() => import('react-apexcharts'), { ssr: false });

/**
 * Daily revenue for the trailing window.
 *
 * The endpoint only returns days that actually had sales, so the series is
 * plotted against its own dates rather than a padded calendar -- a gap in
 * the axis is a day with no fulfilled orders, not missing data.
 */
export default function SalesTrendChart({
  data,
  currency,
  days,
}: {
  data: SalesTrendItem[];
  currency: string;
  days: number;
}) {
  const total = data.reduce((sum, point) => sum + Number(point.revenue), 0);
  const orderCount = data.reduce((sum, point) => sum + point.order_count, 0);

  const options: ApexOptions = {
    chart: { type: 'area', toolbar: { show: false }, zoom: { enabled: false }, fontFamily: 'inherit' },
    colors: ['#487FFF'],
    dataLabels: { enabled: false },
    stroke: { curve: 'smooth', width: 3 },
    fill: {
      type: 'gradient',
      gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.05, stops: [0, 100] },
    },
    grid: { borderColor: '#D1D5DB', strokeDashArray: 4 },
    xaxis: {
      type: 'category',
      categories: data.map(point => point.date),
      labels: {
        formatter: value =>
          new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' }).format(new Date(value)),
      },
    },
    yaxis: {
      labels: { formatter: value => formatMoney(String(value), currency) },
    },
    tooltip: {
      y: {
        formatter: (value, { dataPointIndex }) => {
          const point = data[dataPointIndex];
          const orders = point ? point.order_count : 0;
          return `${formatMoney(String(value), currency)} · ${orders} order${orders === 1 ? '' : 's'}`;
        },
      },
    },
  };

  return (
    <div className="col-xxl-8 col-xl-12">
      <div className="card h-100">
        <div className="card-body">
          <div className="d-flex flex-wrap align-items-center justify-content-between gap-2">
            <h6 className="text-lg mb-0">Sales trend</h6>
            <span className="text-sm fw-medium text-neutral-500">Last {days} days</span>
          </div>

          <div className="d-flex flex-wrap align-items-center gap-2 mt-8">
            <h6 className="mb-0">{formatMoney(String(total), currency)}</h6>
            <span className="text-xs fw-medium text-neutral-500">
              from {orderCount} fulfilled order{orderCount === 1 ? '' : 's'}
            </span>
          </div>

          {data.length === 0 ? (
            <div className="d-flex flex-column align-items-center justify-content-center text-center py-40">
              <p className="text-neutral-500 mb-0">No fulfilled orders in this period.</p>
              <p className="text-sm text-neutral-400 mb-0">
                Revenue appears here once orders move past pending.
              </p>
            </div>
          ) : (
            <ReactApexChart options={options} series={[{ name: 'Revenue', data: data.map(p => Number(p.revenue)) }]} type="area" height={264} />
          )}
        </div>
      </div>
    </div>
  );
}
