from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.orders.constants import OrderStatus
from app.payments.constants import PaymentStatus


class PeriodMetric(BaseModel):
    order_count: int
    revenue: Decimal
    previous_order_count: int
    previous_revenue: Decimal
    order_count_change_pct: float | None = None
    revenue_change_pct: float | None = None


class SalesOverview(BaseModel):
    today: PeriodMetric
    week: PeriodMetric
    month: PeriodMetric
    total_order_count: int
    total_revenue: Decimal


class OrderStatusSummary(BaseModel):
    total: int = 0
    today: int = 0
    pending: int = 0
    processing: int = 0
    shipped: int = 0
    delivered: int = 0
    cancelled: int = 0
    returned: int = 0
    other: int = 0


class InventoryVariantItem(BaseModel):
    product_id: UUID
    product_name: str
    variant_id: UUID | None = None
    sku: str
    available_quantity: int
    low_stock_threshold: int


class InventoryOverview(BaseModel):
    low_stock_count: int
    out_of_stock_count: int
    low_stock_variants: list[InventoryVariantItem]
    out_of_stock_variants: list[InventoryVariantItem]


class CustomerOverview(BaseModel):
    total: int
    new_today: int
    new_this_month: int


class ProductsOverview(BaseModel):
    total: int


class PaymentOverview(BaseModel):
    paid_count: int
    pending_count: int
    failed_count: int
    refunded_count: int = 0
    today_paid_amount: Decimal


class RecentOrderSummary(BaseModel):
    order_id: UUID
    order_number: str
    customer_email: str | None = None
    total_amount: Decimal
    currency: str
    order_status: OrderStatus
    payment_status: PaymentStatus
    created_at: datetime


class SalesTrendItem(BaseModel):
    date: date
    order_count: int
    revenue: Decimal


class TopSellingProductItem(BaseModel):
    product_id: UUID
    product_name: str
    quantity_sold: int
    revenue_generated: Decimal


class DashboardOverviewResponse(BaseModel):
    sales: SalesOverview
    orders: OrderStatusSummary
    products: ProductsOverview
    inventory: InventoryOverview
    customers: CustomerOverview
    payments: PaymentOverview
    recent_orders: list[RecentOrderSummary]