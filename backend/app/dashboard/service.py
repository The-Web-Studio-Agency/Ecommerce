from __future__ import annotations

from datetime import datetime, time, timezone, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalogue.models import Product, ProductVariant, InventoryItem
from app.core.money import money
from app.orders.constants import OrderStatus
from app.orders.models import Order, OrderItem
from app.payments.constants import PaymentStatus
from app.payments.models import Payment
from app.users.models import User


class DashboardService:
    """Aggregates multi-tenant business data for the admin dashboard."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    def _calculate_change_pct(self, current: Decimal | int, previous: Decimal | int) -> float | None:
        if previous == 0:
            return None if current == 0 else 100.0
        diff = float(current) - float(previous)
        return round((diff / float(previous)) * 100.0, 2)

    async def get_overview(self, currency: str = "USD") -> dict:
        now_utc = datetime.now(timezone.utc)
        today_start = datetime.combine(now_utc.date(), time.min, tzinfo=timezone.utc)
        week_start = today_start - timedelta(days=7)
        month_start = datetime.combine(now_utc.date().replace(day=1), time.min, tzinfo=timezone.utc)

        yesterday_start = today_start - timedelta(days=1)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

        completed_statuses = [OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]

        async def get_sales_stats(start_dt: datetime, end_dt: datetime) -> tuple[int, Decimal]:
            stmt = select(
                func.count(Order.id),
                func.coalesce(func.sum(Order.total_amount), Decimal("0.00"))
            ).where(
                Order.tenant_id == self.tenant_id,
                Order.created_at >= start_dt,
                Order.created_at < end_dt,
                Order.status.in_(completed_statuses)
            )
            res = (await self.session.execute(stmt)).one()
            return res[0], money(res[1])

        today_orders, today_rev = await get_sales_stats(today_start, now_utc)
        yest_orders, yest_rev = await get_sales_stats(yesterday_start, today_start)

        week_orders, week_rev = await get_sales_stats(week_start, now_utc)

        month_orders, month_rev = await get_sales_stats(month_start, now_utc)
        prev_month_orders, prev_month_rev = await get_sales_stats(prev_month_start, month_start)

        total_stmt = select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), Decimal("0.00"))
        ).where(
            Order.tenant_id == self.tenant_id,
            Order.status.in_(completed_statuses)
        )
        total_res = (await self.session.execute(total_stmt)).one()
        total_order_count, total_revenue = total_res[0], money(total_res[1])

        sales_overview = {
            "today": {
                "order_count": today_orders,
                "revenue": today_rev,
                "previous_order_count": yest_orders,
                "previous_revenue": yest_rev,
                "order_count_change_pct": self._calculate_change_pct(today_orders, yest_orders),
                "revenue_change_pct": self._calculate_change_pct(today_rev, yest_rev),
            },
            "week": {
                "order_count": week_orders,
                "revenue": week_rev,
                "previous_order_count": 0,
                "previous_revenue": Decimal("0.00"),
            },
            "month": {
                "order_count": month_orders,
                "revenue": month_rev,
                "previous_order_count": prev_month_orders,
                "previous_revenue": prev_month_rev,
                "order_count_change_pct": self._calculate_change_pct(month_orders, prev_month_orders),
                "revenue_change_pct": self._calculate_change_pct(month_rev, prev_month_rev),
            },
            "total_order_count": total_order_count,
            "total_revenue": total_revenue,
        }

        # Order Status Breakdown
        status_stmt = select(
            Order.status, func.count(Order.id)
        ).where(
            Order.tenant_id == self.tenant_id
        ).group_by(Order.status)
        status_counts = {row[0]: row[1] for row in (await self.session.execute(status_stmt)).all()}

        # All orders regardless of status -- distinct from sales.total_order_count,
        # which only counts completed (processing/shipped/delivered) orders.
        total_orders_count = (await self.session.scalar(
            select(func.count(Order.id)).where(Order.tenant_id == self.tenant_id)
        )) or 0

        # There is no "RETURNED" order status in this domain -- a return only
        # ever shows up as its payment being refunded, so that is the source
        # of truth for "returned orders" here.
        returned_orders_count = (await self.session.scalar(
            select(func.count(func.distinct(Order.id)))
            .select_from(Order)
            .join(Payment, Payment.order_id == Order.id)
            .where(
                Order.tenant_id == self.tenant_id,
                Payment.status == PaymentStatus.REFUNDED,
            )
        )) or 0

        orders_summary = {
            "total": total_orders_count,
            "pending": status_counts.get(OrderStatus.PENDING, 0),
            "processing": status_counts.get(OrderStatus.PROCESSING, 0),
            "shipped": status_counts.get(OrderStatus.SHIPPED, 0),
            "delivered": status_counts.get(OrderStatus.DELIVERED, 0),
            "cancelled": status_counts.get(OrderStatus.CANCELLED, 0),
            "returned": returned_orders_count,
            "other": sum(v for k, v in status_counts.items() if k not in {s.value for s in OrderStatus}),
        }

        # Total Products
        total_products_count = (await self.session.scalar(
            select(func.count(Product.id)).where(Product.tenant_id == self.tenant_id)
        )) or 0
        products_overview = {"total": total_products_count}

        # Inventory Overview via ProductVariant and Product
        inv_stmt = select(InventoryItem, ProductVariant, Product).join(
            ProductVariant, InventoryItem.variant_id == ProductVariant.id
        ).join(
            Product, ProductVariant.product_id == Product.id
        ).where(
            InventoryItem.tenant_id == self.tenant_id
        )
        inv_rows = (await self.session.execute(inv_stmt)).all()

        low_stock_products = []
        out_of_stock_products = []

        for item, variant, prod in inv_rows:
            sellable = item.available_quantity - item.reserved_quantity
            threshold = item.low_stock_threshold or 5

            prod_item = {
                "product_id": prod.id,
                "product_name": prod.name,
                "variant_id": variant.id,
                "sku": variant.sku,
                "available_quantity": sellable,
                "low_stock_threshold": threshold,
            }

            if sellable <= 0:
                out_of_stock_products.append(prod_item)
            elif sellable <= threshold:
                low_stock_products.append(prod_item)

        inventory_overview = {
            "low_stock_count": len(low_stock_products),
            "out_of_stock_count": len(out_of_stock_products),
            "low_stock_products": low_stock_products[:10],
            "out_of_stock_products": out_of_stock_products[:10],
        }

        # Customer Overview
        cust_base = select(func.count(User.id)).where(
            User.tenant_id == self.tenant_id,
            User.role == "CUSTOMER"
        )
        total_customers = (await self.session.scalar(cust_base)) or 0
        new_today_cust = (await self.session.scalar(cust_base.where(User.created_at >= today_start))) or 0
        new_month_cust = (await self.session.scalar(cust_base.where(User.created_at >= month_start))) or 0

        customer_overview = {
            "total": total_customers,
            "new_today": new_today_cust,
            "new_this_month": new_month_cust,
        }

        # Payment Overview
        pay_stmt = select(Payment.status, func.count(Payment.id)).where(
            Payment.tenant_id == self.tenant_id
        ).group_by(Payment.status)
        pay_counts = {row[0]: row[1] for row in (await self.session.execute(pay_stmt)).all()}

        today_paid_amount = (await self.session.scalar(
            select(func.coalesce(func.sum(Payment.amount), Decimal("0.00"))).where(
                Payment.tenant_id == self.tenant_id,
                Payment.status == PaymentStatus.PAID,
                Payment.created_at >= today_start
            )
        )) or Decimal("0.00")

        payment_overview = {
            "paid_count": pay_counts.get(PaymentStatus.PAID, 0),
            "pending_count": pay_counts.get(PaymentStatus.PENDING, 0),
            "failed_count": pay_counts.get(PaymentStatus.FAILED, 0),
            "refunded_count": pay_counts.get(PaymentStatus.REFUNDED, 0),
            "today_paid_amount": money(today_paid_amount),
        }

        # Recent Orders
        recent_stmt = select(Order, User).outerjoin(
            User, Order.customer_id == User.id
        ).where(
            Order.tenant_id == self.tenant_id
        ).order_by(
            Order.created_at.desc()
        ).limit(5)
        recent_rows = (await self.session.execute(recent_stmt)).all()

        recent_orders = []
        for ord_obj, usr_obj in recent_rows:
            recent_orders.append({
                "order_id": ord_obj.id,
                "order_number": ord_obj.order_number,
                "customer_email": usr_obj.email if usr_obj else None,
                "total_amount": ord_obj.total_amount,
                "currency": currency,
                "order_status": ord_obj.status,
                "payment_status": ord_obj.payment_status,
                "created_at": ord_obj.created_at,
            })

        return {
            "sales": sales_overview,
            "orders": orders_summary,
            "products": products_overview,
            "inventory": inventory_overview,
            "customers": customer_overview,
            "payments": payment_overview,
            "recent_orders": recent_orders,
        }

    async def get_sales_trend(self, days: int = 30) -> list[dict]:
        start_date = datetime.now(timezone.utc).date() - timedelta(days=days)
        completed_statuses = [OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]

        stmt = select(
            func.date(Order.created_at).label("order_date"),
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total_amount), Decimal("0.00")).label("revenue")
        ).where(
            Order.tenant_id == self.tenant_id,
            func.date(Order.created_at) >= start_date,
            Order.status.in_(completed_statuses)
        ).group_by(
            func.date(Order.created_at)
        ).order_by(
            func.date(Order.created_at).asc()
        )

        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "date": row.order_date,
                "order_count": row.order_count,
                "revenue": money(row.revenue),
            }
            for row in rows
        ]

    async def get_top_products(self, days: int = 30, limit: int = 10) -> list[dict]:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        completed_statuses = [OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]

        stmt = select(
            Product.id,
            Product.name,
            func.sum(OrderItem.quantity).label("quantity_sold"),
            func.coalesce(func.sum(OrderItem.subtotal), Decimal("0.00")).label("revenue_generated")
        ).join(
            ProductVariant, OrderItem.variant_id == ProductVariant.id
        ).join(
            Product, ProductVariant.product_id == Product.id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).where(
            Order.tenant_id == self.tenant_id,
            Order.created_at >= start_date,
            Order.status.in_(completed_statuses)
        ).group_by(
            Product.id, Product.name
        ).order_by(
            desc("quantity_sold")
        ).limit(limit)

        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "product_id": row.id,
                "product_name": row.name,
                "quantity_sold": row.quantity_sold,
                "revenue_generated": money(row.revenue_generated),
            }
            for row in rows
        ]