from __future__ import annotations

from datetime import datetime

from rinsehq.domain.entities.account import BusinessInfo, PersonalInfo, SubAdmin
from rinsehq.domain.entities.customer import Customer
from rinsehq.domain.entities.invoice import Invoice
from rinsehq.domain.entities.order import Order
from rinsehq.domain.entities.service import Service, ServicesConfiguration
from rinsehq.domain.entities.store import Store, StoreAssignment
from rinsehq.domain.entities.transaction import Transaction
from rinsehq.domain.entities.user import AuthUser, StoreAccess, User


def _format_ngn(amount_kobo: int) -> str:
    return f"N{amount_kobo / 100:,.0f}"


def user_to_response(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "emailVerified": user.email_verified,
        "createdAt": user.created_at.isoformat(),
    }


def auth_user_to_response(auth_user: AuthUser) -> dict:
    return {
        "id": auth_user.id,
        "email": auth_user.email,
        "name": auth_user.name,
        "storeId": auth_user.store_id,
        "storeName": auth_user.store_name,
        "storeRole": auth_user.store_role,
        "permissionLevel": auth_user.permission_level,
    }


def store_access_to_response(access: StoreAccess) -> dict:
    return {
        "storeId": access.store_id,
        "storeName": access.store_name,
        "address": access.address,
        "city": access.city,
        "isMainStore": access.is_main_store,
        "role": access.role,
        "permissionLevel": access.permission_level,
    }


def store_to_response(store: Store) -> dict:
    return {
        "id": store.id,
        "name": store.name,
        "address": store.address,
        "city": store.city,
        "phone": store.phone,
        "isMainStore": store.is_main_store,
        "status": store.status,
        "ownerUserId": store.owner_user_id,
    }


def assignment_to_response(assignment: StoreAssignment) -> dict:
    return {
        "id": assignment.id,
        "storeId": assignment.store_id,
        "email": assignment.email,
        "name": assignment.name,
        "role": assignment.role,
        "permissionLevel": assignment.permission_level,
        "status": assignment.status,
    }


def order_row_to_response(order: Order) -> dict:
    order_type = "Mobile app" if order.type == "mobile_app" else "Offline"
    return {
        "id": order.id,
        "type": order_type,
        "orderDate": order.order_date.isoformat(),
        "customer": order.customer,
        "amount": _format_ngn(order.amount_cents),
        "status": order.status,
        "deliveryDate": order.delivery_date.isoformat(),
        "deliveryMode": order.delivery_mode,
    }


def order_detail_to_response(order: Order) -> dict:
    base = order_row_to_response(order)
    base.update(
        {
            "customerEmail": order.customer_email,
            "customerPhone": order.customer_phone,
            "customerAddress": order.customer_address,
            "invoiceId": order.invoice_id or "",
            "invoiceNo": order.invoice_no or "",
            "paymentStatus": order.payment_status,
            "paymentMethod": order.payment_method,
            "laundryMode": order.laundry_mode,
            "serviceType": order.service_type,
            "lineItems": [
                {
                    "name": li.name,
                    "quantity": li.quantity,
                    "unitPrice": li.unit_price,
                    "amount": li.amount,
                    "laundryMode": li.laundry_mode,
                }
                for li in (order.line_items or [])
            ],
            "subtotal": order.subtotal,
            "vat": order.vat,
            "discount": order.discount,
            "total": order.total,
            "pickupDate": order.pickup_date,
            "pickupTime": order.pickup_time,
            "deliveryTime": order.delivery_time,
            "description": order.description,
        }
    )
    return base


def service_to_response(service: Service) -> dict:
    return {
        "id": service.id,
        "name": service.name,
        "category": service.category,
        "laundryMode": service.laundry_mode,
        "unitPrice": service.unit_price,
        "pricingUnit": service.pricing_unit,
        "turnaroundHours": service.turnaround_hours,
        "status": service.status,
        "description": service.description,
        "ordersCount": service.orders_count,
        "updatedAt": service.updated_at.isoformat(),
    }


def config_to_response(config: ServicesConfiguration) -> dict:
    def items(lst):
        return [{"id": i.id, "label": i.label, "enabled": i.enabled} for i in lst]

    return {
        "laundryModes": items(config.laundry_modes),
        "serviceTypes": items(config.service_types),
        "orderTypes": items(config.order_types),
    }


def customer_to_response(customer: Customer) -> dict:
    return {
        "id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
    }


def transaction_row_to_response(txn: Transaction) -> dict:
    return {
        "id": txn.id,
        "reference": txn.reference,
        "orderId": txn.order_id,
        "customer": txn.customer,
        "amount": _format_ngn(txn.amount_cents),
        "type": txn.type,
        "paymentMethod": txn.payment_method,
        "status": txn.status,
        "date": txn.date.isoformat(),
    }


def transaction_detail_to_response(txn: Transaction) -> dict:
    base = transaction_row_to_response(txn)
    base.update(
        {
            "customerEmail": txn.customer_email,
            "customerPhone": txn.customer_phone,
            "description": txn.description,
            "fee": _format_ngn(txn.fee_cents),
            "netAmount": _format_ngn(txn.net_amount_cents),
            "channel": txn.channel,
            "paidAt": txn.paid_at.isoformat() if txn.paid_at else None,
        }
    )
    return base


def invoice_to_response(invoice: Invoice) -> dict:
    return {
        "id": invoice.id,
        "businessName": invoice.business_name,
        "status": invoice.status,
        "customer": {
            "name": invoice.customer_name,
            "email": invoice.customer_email,
            "phone": invoice.customer_phone,
            "address": invoice.customer_address,
        },
        "invoiceNo": invoice.invoice_no,
        "invoiceDate": invoice.invoice_date.isoformat(),
        "paymentMethod": invoice.payment_method,
        "lineItems": [
            {
                "index": li.index,
                "laundryMode": li.laundry_mode,
                "itemsLabel": li.items_label,
                "unitPrice": li.unit_price,
                "amount": li.amount,
            }
            for li in invoice.line_items
        ],
        "subtotal": invoice.subtotal,
        "vat": invoice.vat,
        "discount": invoice.discount,
        "total": invoice.total,
        "businessContact": {
            "address": invoice.business_address,
            "phone": invoice.business_phone,
            "whatsapp": invoice.business_whatsapp,
        },
    }


def personal_to_response(info: PersonalInfo) -> dict:
    return {"fullName": info.full_name, "email": info.email, "phone": info.phone}


def business_to_response(info: BusinessInfo) -> dict:
    return {
        "businessName": info.business_name,
        "bio": info.bio,
        "registrationNo": info.registration_no,
        "address": info.address,
        "city": info.city,
        "postalCode": info.postal_code,
        "country": info.country,
        "phone": info.phone,
        "whatsapp": info.whatsapp,
    }


def sub_admin_to_response(admin: SubAdmin) -> dict:
    return {
        "id": admin.id,
        "name": admin.name,
        "email": admin.email,
        "permissionLevel": admin.permission_level,
        "permissions": {
            "orders": admin.permissions.orders,
            "services": admin.permissions.services,
            "transactions": admin.permissions.transactions,
            "reports": admin.permissions.reports,
            "settings": admin.permissions.settings,
            "adminManagement": admin.permissions.admin_management,
        },
        "status": admin.status,
        "storeIds": admin.store_ids,
        "lastActive": admin.last_active,
    }
