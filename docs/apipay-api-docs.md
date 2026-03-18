# ApiPay.kz API Documentation

## Complete Integration Guide for Kaspi Pay (Phone Payments)

## Base Configuration

- **Base URL:** `https://bpapi.bazarbay.site/api/v1`
- **Authentication:** Header `X-API-Key: your_api_key`
- **Content-Type:** `application/json`
- **Rate Limits:** 60 req/min per API key

---

## Pricing

| Plan | Transaction Limit (per day) | Price/month |
|------|----------------------------|-------------|
| Старт (Start) | up to 30/day | 10,000 KZT |
| Бизнес (Business) | from 30/day | 25,000 KZT |
| Про (Pro) | from 100/day | 60,000 KZT |

- No transaction fees (0% from payments)
- All plans include all features
- No blocking on exceeding limits — manager will contact you proactively

---

## Prerequisites

1. Get API key in [ApiPay.kz](https://apipay.kz) dashboard
2. [Connect your Kaspi Business as "Cashier"](https://apipay.kz/connect-cashier) — contact support via WhatsApp (+7 708 516 74 89)
3. Wait for organization verification (usually 5-30 minutes)

---

## Endpoints Overview (23)

| # | Method | Path | Description |
|---|--------|------|-------------|
| | **Health** | | |
| 1 | GET | /status | Health check (no auth) |
| | **Invoices** | | |
| 2 | POST | /invoices | Create invoice (with or without cart) |
| 3 | GET | /invoices | List invoices |
| 4 | GET | /invoices/{id} | Get invoice |
| 5 | POST | /invoices/{id}/cancel | Cancel invoice |
| 6 | POST | /invoices/{id}/refund | Refund invoice |
| 7 | GET | /invoices/{id}/refunds | List refunds for invoice |
| 8 | POST | /invoices/status/check | Bulk status check |
| | **Refunds** | | |
| 9 | GET | /refunds | List all refunds |
| | **Catalog** | | |
| 10 | GET | /catalog/units | List measurement units |
| 11 | GET | /catalog | List catalog items |
| 12 | POST | /catalog/upload-image | Upload catalog image |
| 13 | POST | /catalog | Create catalog items |
| 14 | PATCH | /catalog/{id} | Update catalog item |
| 15 | DELETE | /catalog/{id} | Delete catalog item |
| | **Subscriptions** | | |
| 16 | POST | /subscriptions | Create subscription |
| 17 | GET | /subscriptions | List subscriptions |
| 18 | GET | /subscriptions/{id} | Get subscription |
| 19 | PUT | /subscriptions/{id} | Update subscription |
| 20 | POST | /subscriptions/{id}/pause | Pause subscription |
| 21 | POST | /subscriptions/{id}/resume | Resume subscription |
| 22 | POST | /subscriptions/{id}/cancel | Cancel subscription |
| 23 | GET | /subscriptions/{id}/invoices | Subscription invoices |

---

## Health Check

### GET /status

No authentication required.

**Response 200:**
```json
{
  "status": "ok",
  "timestamp": "2026-02-12T12:00:00+05:00"
}
```

---

## Invoices

### POST /invoices

Create a new invoice. Supports two modes:
- **Without cart** — pass `amount` directly
- **With cart** — pass `cart_items`, amount is calculated automatically

**Request (without cart):**
```json
{
  "amount": 5000.00,
  "phone_number": "87001234567",
  "description": "Payment for order #123",
  "external_order_id": "order-123"
}
```

**Request (with cart — for organizations with catalog):**
```json
{
  "phone_number": "87001234567",
  "description": "Payment for order #123",
  "cart_items": [
    { "catalog_item_id": 1, "count": 2, "price": 4500.00 },
    { "catalog_item_id": 5, "count": 1, "discount": 500 }
  ],
  "discount_percentage": 10
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| amount | number | Yes (without cart) | Amount 0.01 - 99999999.99. Ignored when `cart_items` is present. |
| phone_number | string | Yes | Customer phone, format: `8XXXXXXXXXX` (11 digits starting with 8) |
| description | string | No | Max 500 characters |
| external_order_id | string | No | Your order ID, max 255 characters |
| cart_items | array | No | Cart items (only for organizations with catalog). |
| discount_percentage | number | No | Global discount percentage (0-100). Applied to cart items without explicit `discount`. Per-item `discount` takes priority. |

**Cart item fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| catalog_item_id | integer | Yes | Item ID from catalog (field `id` from `GET /catalog`) |
| count | integer | Yes | Quantity, min 1 |
| price | number | No | Custom price override (0.01 - 99999999.99). Replaces catalog price for this item. |
| discount | number | No | Discount amount for this line (min 0). Applied to full line subtotal (price × count). |

> **Recommendation:** Before creating an invoice with cart, fetch the current catalog via `GET /catalog` to use correct `catalog_item_id` values.

**Response 201:**
```json
{
  "id": 124,
  "amount": "4550.00",
  "status": "pending",
  "subtotal": "5000.00",
  "discount_sum": "450.00",
  "discount_percentage": "10",
  "created_at": "2026-02-12T10:35:00+05:00"
}
```

> **Note:** Fields `subtotal`, `discount_sum`, and `discount_percentage` appear only when a discount is applied (backward compatible).

**Errors:**
- `400` — Organization not found or not verified
- `422` — Validation error
- `422` — `"This organization requires cart items. Include cart_items in request."` (catalog org without cart)
- `422` — `"This organization does not support catalog. Remove cart_items from request."` (non-catalog org with cart)
- `422` — `"Total discount cannot exceed subtotal."` (field: `discount`)
- `422` — `"Amount after discounts must be greater than 0."` (field: `amount`)
- `422` — `"Discount cannot exceed line subtotal (9000.00)."` (field: `cart_items.0.discount`)

> **Discount priority:** Per-item `discount` takes priority over global `discount_percentage`. If a cart item has an explicit `discount`, the global percentage is not applied to that item.

---

### GET /invoices

List invoices with filtering, sorting, and pagination.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | integer | 1 | Page number |
| per_page | integer | 10 | Items per page (1-100) |
| search | string | — | Search by ID or description (max 100 chars) |
| status[] | array | — | Filter by statuses: `pending`, `paid`, `cancelled`, `expired` |
| date_from | string | — | Start date (YYYY-MM-DD) |
| date_to | string | — | End date (YYYY-MM-DD, must be >= date_from) |
| sort_by | string | created_at | Sort field: `id`, `amount`, `client_name`, `status`, `created_at` |
| sort_order | string | desc | `asc` or `desc` |

**Response 200:**
```json
{
  "current_page": 1,
  "data": [
    {
      "id": 124,
      "user_id": 5,
      "organization_id": 3,
      "api_key_id": 2,
      "amount": "5000.00",
      "phone_number": "87001234567",
      "description": "Payment for order #123",
      "external_order_id": "order-123",
      "status": "paid",
      "paid_at": "2026-02-12T10:36:00+05:00",
      "created_at": "2026-02-12T10:35:00+05:00"
    }
  ],
  "total": 100
}
```

> **Note:** The list response uses flat pagination (`current_page`, `total` at the top level — no `meta` wrapper). Full invoice details (including `client_name`, `items`, refund fields) are available via `GET /invoices/{id}`.

---

### GET /invoices/{id}

Get a single invoice by ID.

**Response 200:**
```json
{
  "id": 124,
  "amount": "5000.00",
  "phone_number": "87001234567",
  "description": "Payment for order #123",
  "external_order_id": "order-123",
  "status": "paid",
  "client_name": "Ivan I.",
  "client_comment": null,
  "is_sandbox": false,
  "total_refunded": "0.00",
  "is_fully_refunded": false,
  "kaspi_invoice_id": "13234689513",
  "items": [
    {
      "id": 1,
      "invoice_id": 124,
      "catalog_item_id": 42,
      "name": "Americano",
      "price": "800.00",
      "count": 2,
      "unit_id": 1,
      "original_price": "900.00",
      "discount": null
    },
    {
      "id": 2,
      "invoice_id": 124,
      "catalog_item_id": 43,
      "name": "Latte",
      "price": "1200.50",
      "count": 1,
      "unit_id": 1,
      "original_price": null,
      "discount": "500.00"
    }
  ],
  "paid_at": "2026-02-12T10:36:00+05:00",
  "created_at": "2026-02-12T10:35:00+05:00"
}
```

**Items fields:**

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Item position ID |
| invoice_id | integer | Invoice ID |
| catalog_item_id | integer\|null | Catalog item ID. `null` if item was deleted |
| name | string | Product name (snapshot) |
| price | string | Unit price (snapshot) |
| count | integer | Quantity |
| unit_id | integer | Unit of measurement ID |
| original_price | string\|null | Original catalog price if overridden by custom `price`. `null` if catalog price was used. |
| discount | string\|null | Discount amount applied to this line. `null` if no discount. |

> **Note:** The `items` field contains a snapshot of products at the time the invoice was created. An empty array `[]` means the organization has no catalog or it's an older invoice. If `catalog_item_id: null`, the item was deleted from the catalog, but its data (name, price, count, unit_id) is preserved.

**Errors:**
- `404` — Invoice not found

---

### POST /invoices/{id}/cancel

Cancel a pending invoice. May return **202 Accepted** — in that case the invoice transitions to `cancelling` status, use GET /invoices/{id} to poll.

**Request:** empty body

**Response 200/202:**
```json
{
  "message": "Invoice cancelled successfully",
  "invoice": {
    "id": 124,
    "status": "cancelled"
  }
}
```

> **Async cancellation:** If the server returns `202 Accepted`, the invoice transitions to `cancelling` status. Use `GET /invoices/{id}` to poll until final status `cancelled`.

**Errors:**
- `400` — Only pending invoices can be cancelled
- `404` — Invoice not found
- `500` — Failed to cancel in Kaspi
- `503` — Kaspi session expired

---

### POST /invoices/{id}/refund

Create a refund for a paid invoice. Omit `amount` for full refund. For invoices with cart items, use `return_items` to refund specific positions.

**Request:**
```json
{
  "amount": 2000.00,
  "reason": "Customer request",
  "return_items": [
    { "catalog_item_id": 1, "count": 1 }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| amount | number | No | Refund amount (0.01 - 99999999.99). Omit for full refund. |
| reason | string | No | Reason, max 500 chars |
| return_items | array | No | Specific items to refund (for invoices with cart). Format: `{ catalog_item_id, count }` |

**Response 201:**
```json
{
  "message": "Refund created and queued for processing",
  "refund": {
    "id": 456,
    "invoice_id": 124,
    "amount": "2000.00",
    "reason": "Customer request",
    "status": "pending",
    "created_at": "2026-02-12T11:00:00+05:00"
  },
  "invoice": {
    "id": 124,
    "amount": "5000.00",
    "total_refunded": "0.00",
    "available_for_refund": 5000,
    "pending_refund_amount": 2000
  }
}
```

**Errors:**
- `400` — Invoice is not refundable (not paid or fully refunded)
- `400` — Refund amount exceeds available amount
- `404` — Invoice not found

---

### GET /invoices/{id}/refunds

List refunds for a specific invoice.

**Response 200:**
```json
{
  "invoice": {
    "id": 124,
    "amount": "5000.00",
    "total_refunded": "2000.00",
    "available_for_refund": 3000,
    "is_fully_refunded": false
  },
  "refunds": [
    {
      "id": 456,
      "invoice_id": 124,
      "amount": "2000.00",
      "status": "completed",
      "reason": "Customer request",
      "items": null,
      "created_at": "2026-02-12T11:00:00+05:00"
    }
  ],
  "total": 1
}
```

**Errors:**
- `404` — Invoice not found

---

### POST /invoices/status/check

Bulk status check for multiple invoices in one request. Useful for syncing state in your system.

**Request:**
```json
{
  "invoice_ids": [124, 125, 126]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| invoice_ids | array of integers | Yes | Invoice IDs to check (max 100) |

**Response 200:**
```json
{
  "message": "Status check jobs dispatched",
  "count": 3
}
```

> **Note:** This endpoint dispatches background jobs to refresh invoice statuses. It does not return current statuses directly — use `GET /invoices/{id}` to check individual invoice status after triggering a refresh.

---

### Invoice Statuses

| Status | Description | Can Cancel | Can Refund |
|--------|-------------|------------|------------|
| `pending` | Awaiting payment | Yes | No |
| `cancelling` | Being cancelled (async) | No | No |
| `paid` | Paid by customer | No | Yes |
| `cancelled` | Manually cancelled | No | No |
| `expired` | Payment deadline passed | No | No |
| `partially_refunded` | Partially refunded | No | Yes (remaining) |
| `refunded` | Fully refunded | No | No |

---

## Refunds

### GET /refunds

List all refunds for your organization.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | integer | 1 | Page number |
| per_page | integer | 10 | Items per page (1-100) |
| status[] | array | — | Filter: `pending`, `processing`, `completed`, `failed` |
| invoice_id | integer | — | Filter by invoice ID |
| date_from | string | — | Start date (YYYY-MM-DD) |
| date_to | string | — | End date (YYYY-MM-DD) |

**Response 200:**
```json
{
  "current_page": 1,
  "data": [
    {
      "id": 456,
      "invoice_id": 124,
      "amount": "2000.00",
      "reason": "Customer request",
      "status": "completed",
      "created_at": "2026-02-12T11:00:00+05:00"
    }
  ],
  "total": 3
}
```

### Refund Statuses

| Status | Description |
|--------|-------------|
| `pending` | Refund created, queued for processing |
| `processing` | Being processed by Kaspi |
| `completed` | Successfully refunded |
| `failed` | Refund failed |

---

## Catalog

Catalog endpoints are available only for organizations with catalog enabled (`has_catalog = true`).

### GET /catalog/units

List available measurement units for catalog items.

> **Recommendation:** Fetch units before creating items to use correct `unit_id` values.

**Response 200:**
```json
{
  "data": [
    { "id": 1, "name": "шт.", "name_kaz": "дн." },
    { "id": 2, "name": "кг", "name_kaz": "кг" },
    { "id": 3, "name": "литр", "name_kaz": "литр" },
    { "id": 4, "name": "метр", "name_kaz": "метр" },
    { "id": 5, "name": "грамм", "name_kaz": "грамм" },
    { "id": 37, "name": "м2", "name_kaz": "м2" },
    { "id": 38, "name": "сутки", "name_kaz": "тәулік" },
    { "id": 43, "name": "упак.", "name_kaz": "жиынтық" },
    { "id": 44, "name": "час", "name_kaz": "сағат" }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Unit ID (used in `unit_id` when creating items) |
| name | string | Russian name |
| name_kaz | string | Kazakh name |

---

### GET /catalog

List catalog items with search and filtering.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | integer | 1 | Page number |
| per_page | integer | 50 | Items per page (1-200) |
| search | string | — | Search by name |
| barcode | string | — | Filter by barcode |
| first_char | string | — | Filter by first character |

**Response 200:**
```json
{
  "data": [
    {
      "id": 1,
      "kaspi_item_id": 12345,
      "name": "Coffee Latte",
      "unit_id": 1,
      "selling_price": 1800,
      "image_url": "https://cdn.kaspi.kz/image.jpg",
      "barcode": "4870000123456",
      "status": "active",
      "synced_at": "2026-02-12T10:00:00+05:00"
    }
  ],
  "meta": {
    "current_page": 1,
    "total": 50,
    "per_page": 50
  }
}
```

**Catalog item fields:**

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Internal item ID in ApiPay |
| kaspi_item_id | integer | Item ID in Kaspi (assigned after sync) |
| name | string | Product name |
| unit_id | integer | Unit of measurement ID (see `GET /catalog/units`) |
| selling_price | number | Selling price |
| image_url | string\|null | Product image URL |
| barcode | string\|null | Barcode (EAN-13) |
| status | string | Status: `active`, `pending`, `failed`, `deleting`, `deleted` |
| synced_at | string\|null | Last sync date with Kaspi |

**Errors:**
- `400` — Organization does not have catalog enabled
- `400` — Organization has no tradepoint RFO code configured
- `400` — Kaspi session not configured for this organization
- `404` — Verified organization not found

---

### POST /catalog/upload-image

Upload an image for a catalog item. Images are optimized (max 512x512, PNG) and deduplicated by MD5 hash.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| image | file | Yes | Image file (jpg, png, gif, webp), max 10 MB |

**Response 200:**
```json
{
  "image_id": "abc12345-def6-7890-ghij-klmnopqrstuv"
}
```

Use the returned `image_id` when creating or updating catalog items.

---

### POST /catalog

Create one or more catalog items (batch, 1-50 items).

**Request:**
```json
{
  "items": [
    {
      "name": "Coffee Latte",
      "selling_price": 1800,
      "unit_id": 1,
      "image_id": "abc12345-def6-7890-ghij-klmnopqrstuv"
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| items | array | Yes | 1-50 items |
| items.*.name | string | Yes | Product name, max 255 |
| items.*.selling_price | number | Yes | Price, min 0.01 |
| items.*.unit_id | integer | Yes | Unit of measurement ID (from `GET /catalog/units`) |
| items.*.image_id | string (uuid) | No | Image ID from upload-image |

**Response 202:**
```json
{
  "data": [
    {
      "id": 101,
      "name": "Coffee Latte",
      "selling_price": 1800,
      "unit_id": 1,
      "barcode": null,
      "status": "pending"
    }
  ]
}
```

> **Async operation:** Items are created with `status: "pending"` and synced with Kaspi in the background. Use `GET /catalog` to check final status of new items (`active` after successful sync).

**Errors:**
- `422` — Validation error
- `502` — Failed to create catalog item (Kaspi API error)
- `503` — Kaspi session expired

---

### PATCH /catalog/{id}

Update a catalog item. All fields are optional — only provided fields are updated.

**Request:**
```json
{
  "name": "Updated Name",
  "selling_price": 2000,
  "unit_id": 1,
  "image_id": "abc12345-def6-7890-ghij-klmnopqrstuv",
  "is_image_deleted": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | No | Product name, max 255 |
| selling_price | number | No | Price, min 0.01 |
| unit_id | integer | No | Unit of measurement ID (from `GET /catalog/units`) |
| image_id | string (uuid) | No | New image ID from upload-image |
| is_image_deleted | boolean | No | Set `true` to remove image |

**Response 200:**
```json
{
  "message": "Catalog item update queued",
  "catalog_item_id": 1
}
```

**Errors:**
- `404` — Catalog item not found
- `422` — Validation error
- `502` — Failed to update (Kaspi API error)
- `503` — Kaspi session expired

---

### DELETE /catalog/{id}

Delete a catalog item.

**Response 200:**
```json
{
  "message": "Catalog item deletion queued",
  "catalog_item_id": 1
}
```

**Errors:**
- `404` — Catalog item not found
- `502` — Failed to delete (Kaspi API error)
- `503` — Kaspi session expired

---

## Subscriptions

Automatic recurring invoices on a schedule. Supports grace period and retry on failed payments.

### POST /subscriptions

Create a subscription. Two modes: without cart (pass `amount`) or with cart (pass `cart_items`, amount is calculated automatically). For organizations with catalog, `cart_items` is required.

**Request (without cart):**
```json
{
  "phone_number": "87001234567",
  "amount": 5000,
  "billing_period": "monthly",
  "billing_day": 15,
  "description": "Monthly subscription",
  "subscriber_name": "Ivan Ivanov",
  "external_subscriber_id": "cust-123",
  "started_at": "2026-03-01",
  "max_retry_attempts": 3,
  "retry_interval_hours": 24,
  "grace_period_days": 7,
  "metadata": { "plan": "premium" }
}
```

**Request (with cart — for organizations with catalog):**
```json
{
  "phone_number": "87001234567",
  "billing_period": "monthly",
  "billing_day": 15,
  "description": "Monthly subscription",
  "subscriber_name": "Ivan Ivanov",
  "cart_items": [
    { "catalog_item_id": 1, "count": 2 },
    { "catalog_item_id": 5, "count": 1 }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| phone_number | string | Yes | Format: `8XXXXXXXXXX` |
| amount | number | Yes (without cart) | 100 - 1000000. Ignored when `cart_items` is present. |
| billing_period | string | Yes | `daily`, `weekly`, `biweekly`, `monthly`, `quarterly`, `yearly` |
| billing_day | integer | No | Day of period (1-28) |
| description | string | No | Max 255 |
| subscriber_name | string | No | Max 255 |
| external_subscriber_id | string | No | Your subscriber ID, max 255 |
| started_at | date | No | Start date (default: today) |
| max_retry_attempts | integer | No | 1-10 |
| retry_interval_hours | integer | No | 1-168 |
| grace_period_days | integer | No | 1-30 |
| metadata | object | No | Custom JSON data |
| cart_items | array | No | Cart items (for catalog orgs). Format: `{ catalog_item_id, count }` |

**Cart item fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| catalog_item_id | integer | Yes | Item ID from catalog (`id` from `GET /catalog`) |
| count | integer | Yes | Quantity, min 1 |

> **Recommendation:** Before creating a subscription with cart, fetch the current catalog via `GET /catalog`. Prices are recalculated from the current catalog at each billing cycle.

**Response 201:**
```json
{
  "message": "Subscription created",
  "subscription": {
    "id": 1,
    "subscriber_name": "Ivan Ivanov",
    "phone_number": "87001234567",
    "amount": "5000.00",
    "cart_items": null,
    "billing_period": "monthly",
    "billing_period_label": "Ежемесячно",
    "billing_day": 15,
    "billing_day_label": "15-го числа",
    "description": "Monthly subscription",
    "external_subscriber_id": "cust-123",
    "status": "active",
    "status_label": "Активна",
    "status_color": "green",
    "started_at": "2026-02-12T00:00:00+05:00",
    "next_billing_at": "2026-03-15T00:00:00+05:00",
    "next_billing_in_days": 31,
    "next_billing_label": "через 31 день",
    "paused_at": null,
    "cancelled_at": null,
    "failed_attempts": 0,
    "max_retry_attempts": 3,
    "retry_interval_hours": 24,
    "grace_period_days": 7,
    "in_grace_period": false,
    "is_sandbox": false,
    "metadata": { "plan": "premium" },
    "created_at": "2026-02-12T12:00:00+05:00",
    "updated_at": "2026-02-12T12:00:00+05:00"
  }
}
```

**Errors:**
- `403` — Organization not verified
- `422` — Validation error

---

### GET /subscriptions

List subscriptions.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | integer | 1 | Page number |
| per_page | integer | 10 | Items per page (1-100) |
| status | string | — | Filter: `active`, `paused`, `cancelled`, `expired` |
| phone_number | string | — | Filter by phone |
| external_subscriber_id | string | — | Filter by your subscriber ID |

**Response 200:**
```json
{
  "current_page": 1,
  "data": [
    {
      "id": 1,
      "subscriber_name": "Ivan Ivanov",
      "phone_number": "87001234567",
      "amount": "5000.00",
      "cart_items": null,
      "billing_period": "monthly",
      "billing_period_label": "Ежемесячно",
      "billing_day": 15,
      "billing_day_label": "15-го числа",
      "description": "Monthly subscription",
      "external_subscriber_id": "cust-123",
      "status": "active",
      "status_label": "Активна",
      "status_color": "green",
      "started_at": "2026-02-01T00:00:00+05:00",
      "next_billing_at": "2026-03-15T00:00:00+05:00",
      "next_billing_in_days": 17,
      "next_billing_label": "через 17 дней",
      "paused_at": null,
      "cancelled_at": null,
      "failed_attempts": 0,
      "max_retry_attempts": 3,
      "retry_interval_hours": 24,
      "grace_period_days": 7,
      "in_grace_period": false,
      "is_sandbox": false,
      "metadata": null,
      "created_at": "2026-02-12T12:00:00+05:00",
      "updated_at": "2026-02-12T12:00:00+05:00"
    }
  ],
  "total": 10
}
```

---

### GET /subscriptions/{id}

Get subscription with stats and last payment info.

**Response 200:**
```json
{
  "subscription": {
    "id": 1,
    "subscriber_name": "Ivan Ivanov",
    "phone_number": "87001234567",
    "amount": "5000.00",
    "cart_items": null,
    "billing_period": "monthly",
    "billing_period_label": "Ежемесячно",
    "billing_day": 15,
    "billing_day_label": "15-го числа",
    "description": "Monthly subscription",
    "status": "active",
    "status_label": "Активна",
    "status_color": "green",
    "external_subscriber_id": "cust-123",
    "started_at": "2026-02-01T00:00:00+05:00",
    "next_billing_at": "2026-03-15T00:00:00+05:00",
    "next_billing_in_days": 17,
    "next_billing_label": "через 17 дней",
    "paused_at": null,
    "cancelled_at": null,
    "max_retry_attempts": 3,
    "retry_interval_hours": 24,
    "grace_period_days": 7,
    "failed_attempts": 0,
    "in_grace_period": false,
    "is_sandbox": false,
    "metadata": { "plan": "premium" },
    "stats": {
      "total_payments": 5,
      "successful_payments": 4,
      "failed_payments": 1,
      "total_amount": "20000.00"
    },
    "last_payment": {
      "id": 200,
      "status": "paid",
      "amount": "5000.00",
      "paid_at": "2026-02-15T12:00:00+05:00"
    },
    "created_at": "2026-02-01T12:00:00+05:00",
    "updated_at": "2026-02-15T12:00:00+05:00"
  }
}
```

**Errors:**
- `404` — Subscription not found

---

### PUT /subscriptions/{id}

Update subscription. All fields are optional — only provided fields are updated. When `cart_items` is passed, the amount is recalculated automatically.

**Request:**
```json
{
  "amount": 7000,
  "billing_day": 20,
  "description": "Updated plan",
  "subscriber_name": "Ivan Petrov",
  "max_retry_attempts": 5,
  "retry_interval_hours": 12,
  "grace_period_days": 14,
  "metadata": { "plan": "enterprise" }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| amount | number | No | New amount (100 - 1000000) |
| billing_day | integer | No | Day of period (1-28) |
| description | string | No | Max 255 |
| subscriber_name | string | No | Max 255 |
| max_retry_attempts | integer | No | 1-10 |
| retry_interval_hours | integer | No | 1-168 |
| grace_period_days | integer | No | 1-30 |
| metadata | object | No | Custom JSON data |
| cart_items | array | No | New cart items (same format as create). Amount recalculated automatically. |

**Response 200:**
```json
{
  "message": "Subscription updated",
  "subscription": {
    "id": 1,
    "subscriber_name": "Ivan Petrov",
    "phone_number": "87001234567",
    "amount": "7000.00",
    "cart_items": null,
    "billing_period": "monthly",
    "billing_period_label": "Ежемесячно",
    "billing_day": 20,
    "billing_day_label": "20-го числа",
    "description": "Updated plan",
    "external_subscriber_id": "cust-123",
    "status": "active",
    "status_label": "Активна",
    "status_color": "green",
    "started_at": "2026-02-12T00:00:00+05:00",
    "next_billing_at": "2026-03-20T00:00:00+05:00",
    "next_billing_in_days": 36,
    "next_billing_label": "через 36 дней",
    "paused_at": null,
    "cancelled_at": null,
    "failed_attempts": 0,
    "max_retry_attempts": 5,
    "retry_interval_hours": 12,
    "grace_period_days": 14,
    "in_grace_period": false,
    "is_sandbox": false,
    "metadata": { "plan": "enterprise" },
    "created_at": "2026-02-12T12:00:00+05:00",
    "updated_at": "2026-02-26T10:00:00+05:00"
  }
}
```

**Errors:**
- `404` — Subscription not found
- `422` — Validation error

---

### POST /subscriptions/{id}/pause

Pause an active subscription.

**Request:** empty body

**Response 200:**
```json
{
  "message": "Subscription paused",
  "subscription": {
    "id": 1,
    "subscriber_name": "Ivan Ivanov",
    "phone_number": "87001234567",
    "amount": "5000.00",
    "billing_period": "monthly",
    "billing_day": 15,
    "status": "paused",
    "status_label": "На паузе",
    "status_color": "orange",
    "next_billing_at": null,
    "paused_at": "2026-02-26T10:00:00+05:00",
    "cancelled_at": null,
    "updated_at": "2026-02-26T10:00:00+05:00"
  }
}
```

**Errors:**
- `400` — Cannot pause (wrong status)
- `404` — Subscription not found

---

### POST /subscriptions/{id}/resume

Resume a paused subscription.

**Request:** empty body

**Response 200:**
```json
{
  "message": "Subscription resumed",
  "subscription": {
    "id": 1,
    "subscriber_name": "Ivan Ivanov",
    "phone_number": "87001234567",
    "amount": "5000.00",
    "billing_period": "monthly",
    "billing_day": 15,
    "status": "active",
    "status_label": "Активна",
    "status_color": "green",
    "next_billing_at": "2026-03-15T00:00:00+05:00",
    "paused_at": null,
    "cancelled_at": null,
    "updated_at": "2026-02-26T10:00:00+05:00"
  }
}
```

**Errors:**
- `400` — Cannot resume (wrong status)
- `404` — Subscription not found

---

### POST /subscriptions/{id}/cancel

Cancel a subscription permanently. **Cannot be restored.**

**Request:** empty body

**Response 200:**
```json
{
  "message": "Subscription cancelled",
  "subscription": {
    "id": 1,
    "subscriber_name": "Ivan Ivanov",
    "phone_number": "87001234567",
    "amount": "5000.00",
    "billing_period": "monthly",
    "billing_day": 15,
    "status": "cancelled",
    "status_label": "Отменена",
    "status_color": "red",
    "next_billing_at": null,
    "paused_at": null,
    "cancelled_at": "2026-02-26T10:00:00+05:00",
    "updated_at": "2026-02-26T10:00:00+05:00"
  }
}
```

**Errors:**
- `400` — Cannot cancel (wrong status)
- `404` — Subscription not found

---

### GET /subscriptions/{id}/invoices

List invoices generated by a subscription.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | integer | 1 | Page number |
| per_page | integer | 10 | Items per page (1-100) |

**Response 200:**
```json
{
  "data": [
    {
      "id": 1,
      "invoice_id": 200,
      "billing_period_start": "2026-02-01",
      "billing_period_end": "2026-02-28",
      "billing_period_label": "01.02.2026 — 28.02.2026",
      "amount": "5000.00",
      "attempt_number": 1,
      "status": "paid",
      "status_label": "Оплачен",
      "status_color": "green",
      "paid_at": "2026-02-15T12:00:00+05:00",
      "failure_reason": null,
      "invoice": {
        "id": 200,
        "kaspi_invoice_id": "13234689513",
        "status": "paid"
      },
      "created_at": "2026-02-15T00:00:00+05:00"
    }
  ],
  "meta": {
    "current_page": 1,
    "total": 5,
    "per_page": 20
  }
}
```

> **Note:** Each item is a `subscription_invoice` record (billing attempt), not a plain invoice. Contains billing period, attempt number, and a nested `invoice` object with the actual Kaspi invoice details.

**Errors:**
- `404` — Subscription not found

---

### Subscription Statuses

| Status | Description |
|--------|-------------|
| `active` | Billing on schedule |
| `paused` | Temporarily paused |
| `cancelled` | Permanently cancelled |
| `expired` | Grace period exceeded |

### Billing Periods

| Period | Description |
|--------|-------------|
| `daily` | Every day |
| `weekly` | Every week |
| `biweekly` | Every 2 weeks |
| `monthly` | Every month |
| `quarterly` | Every 3 months |
| `yearly` | Every year |

### Grace Period

If the customer does not pay and all retry attempts are exhausted:
1. Subscription enters grace period (`in_grace_period: true`)
2. If payment arrives within `grace_period_days` — subscription continues
3. If not — subscription transitions to `expired` status

---

## Webhooks

Webhooks are configured in ApiPay.kz dashboard (Settings > Connection).

When creating a webhook you will receive a secret (shown only once). Use it to verify the signature of incoming notifications.

### Webhook Events

| Event | Description |
|-------|-------------|
| `invoice.status_changed` | Invoice status changed (paid, cancelled, expired) |
| `invoice.refunded` | Refund created for a paid invoice |
| `subscription.payment_succeeded` | Successful subscription payment |
| `subscription.payment_failed` | Failed subscription payment |
| `subscription.grace_period_started` | Subscription grace period started |
| `subscription.expired` | Subscription expired (after grace period) |
| `webhook.test` | Test webhook |

### invoice.status_changed

```json
{
  "event": "invoice.status_changed",
  "invoice": {
    "id": 42,
    "external_order_id": "order_123",
    "amount": "15000.00",
    "subtotal": "16500.00",
    "discount_sum": "1500.00",
    "discount_percentage": "10",
    "status": "paid",
    "description": "Payment description",
    "kaspi_invoice_id": "13234689513",
    "client_name": "Ivan Ivanov",
    "client_phone": "87071234567",
    "paid_at": "2026-02-12T14:35:00+05:00"
  },
  "source": "My API Key",
  "timestamp": "2026-02-12T14:35:01+05:00"
}
```

### invoice.refunded

```json
{
  "event": "invoice.refunded",
  "refund": {
    "id": 5,
    "amount": "2000.00",
    "status": "completed",
    "reason": "Return",
    "created_at": "2026-02-12T10:00:00+05:00"
  },
  "invoice": {
    "id": 42,
    "external_order_id": "order_123",
    "amount": "5000.00",
    "subtotal": "5500.00",
    "discount_sum": "500.00",
    "total_refunded": "2000.00",
    "available_for_refund": "3000.00",
    "is_fully_refunded": false,
    "status": "paid",
    "kaspi_invoice_id": "13234689513"
  },
  "source": "My API Key",
  "timestamp": "2026-02-12T10:00:01+05:00"
}
```

> **Note:** Fields `subtotal`, `discount_sum`, and `discount_percentage` appear in webhook payloads only when the invoice has discounts applied.

### subscription.payment_succeeded

```json
{
  "event": "subscription.payment_succeeded",
  "subscription": {
    "id": 10,
    "external_subscriber_id": "CLIENT-001",
    "phone_number": "87071234567",
    "subscriber_name": "Ivan Ivanov",
    "amount": "5000.00",
    "billing_period": "monthly",
    "status": "active",
    "next_billing_at": "2026-03-01T00:00:00+05:00",
    "failed_attempts": 0,
    "in_grace_period": false
  },
  "invoice_id": 200,
  "amount": "5000.00",
  "paid_at": "2026-02-01T12:00:00+05:00",
  "source": "My API Key",
  "timestamp": "2026-02-01T12:00:01+05:00"
}
```

### subscription.payment_failed

```json
{
  "event": "subscription.payment_failed",
  "subscription": {
    "id": 10,
    "phone_number": "87071234567",
    "amount": "5000.00",
    "billing_period": "monthly",
    "status": "active",
    "failed_attempts": 2,
    "in_grace_period": false
  },
  "invoice_id": 201,
  "amount": "5000.00",
  "reason": "Invoice expired",
  "attempt_number": 2,
  "source": "My API Key",
  "timestamp": "2026-02-02T12:00:01+05:00"
}
```

### subscription.grace_period_started

```json
{
  "event": "subscription.grace_period_started",
  "subscription": {
    "id": 10,
    "phone_number": "87071234567",
    "amount": "5000.00",
    "status": "active",
    "failed_attempts": 3,
    "in_grace_period": true
  },
  "grace_period_days": 3,
  "expires_at": "2026-02-05T12:00:00+05:00",
  "source": "My API Key",
  "timestamp": "2026-02-02T12:00:01+05:00"
}
```

### subscription.expired

```json
{
  "event": "subscription.expired",
  "subscription": {
    "id": 10,
    "phone_number": "87071234567",
    "amount": "5000.00",
    "status": "expired",
    "next_billing_at": null,
    "failed_attempts": 3,
    "in_grace_period": false
  },
  "source": "My API Key",
  "timestamp": "2026-02-05T12:00:01+05:00"
}
```

### `source` field

All webhook payloads contain a `source` field — the name of the API key that created the resource (invoice or subscription). Can be `null`.

### Retry Policy

- **Subscription webhooks** — retried up to 3 times with intervals of 1, 5, 15 minutes
- **Invoice webhooks** — no retries
- Your server must respond within 10 seconds
- HTTP 2xx = success, any other code = failure

### Signature Verification

Header: `X-Webhook-Signature: sha256=<HMAC-SHA256>`

#### JavaScript / Node.js
```javascript
const crypto = require('crypto')

function verifyWebhook(payload, signature, secret) {
  const expected = 'sha256=' + crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex')
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(signature))
}
```

#### PHP
```php
function verifyWebhook($payload, $signature, $secret) {
    $expected = 'sha256=' . hash_hmac('sha256', $payload, $secret);
    return hash_equals($expected, $signature);
}
```

#### Python
```python
import hmac, hashlib

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = 'sha256=' + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## Code Examples

### Create Invoice

#### JavaScript / Node.js
```javascript
const response = await fetch('https://bpapi.bazarbay.site/api/v1/invoices', {
  method: 'POST',
  headers: {
    'X-API-Key': 'YOUR_API_KEY',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    amount: 10000,
    phone_number: '87001234567',
    description: 'Payment for order #123'
  })
})
const data = await response.json()
console.log('Invoice created:', data.id)
```

#### Python
```python
import requests

response = requests.post(
    'https://bpapi.bazarbay.site/api/v1/invoices',
    headers={'X-API-Key': 'YOUR_API_KEY', 'Content-Type': 'application/json'},
    json={'amount': 10000, 'phone_number': '87001234567'}
)
data = response.json()
print(f"Invoice created: {data['id']}")
```

#### PHP
```php
$ch = curl_init('https://bpapi.bazarbay.site/api/v1/invoices');
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => ['X-API-Key: YOUR_API_KEY', 'Content-Type: application/json'],
    CURLOPT_POSTFIELDS => json_encode(['amount' => 10000, 'phone_number' => '87001234567']),
    CURLOPT_RETURNTRANSFER => true
]);
$response = json_decode(curl_exec($ch), true);
echo "Invoice created: " . $response['id'];
```

#### cURL
```bash
curl -X POST https://bpapi.bazarbay.site/api/v1/invoices \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"amount": 10000, "phone_number": "87001234567"}'
```

### Create Invoice with Cart

#### JavaScript / Node.js
```javascript
const response = await fetch('https://bpapi.bazarbay.site/api/v1/invoices', {
  method: 'POST',
  headers: {
    'X-API-Key': 'YOUR_API_KEY',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    phone_number: '87001234567',
    description: 'Cart order',
    cart_items: [
      { catalog_item_id: 1, count: 2, price: 4500.00 },
      { catalog_item_id: 5, count: 3, discount: 500 }
    ],
    discount_percentage: 10
  })
})
```

### Create Subscription

#### cURL
```bash
curl -X POST https://bpapi.bazarbay.site/api/v1/subscriptions \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "87001234567",
    "amount": 5000,
    "billing_period": "monthly",
    "description": "Monthly subscription"
  }'
```

#### JavaScript / Node.js
```javascript
const response = await fetch('https://bpapi.bazarbay.site/api/v1/subscriptions', {
  method: 'POST',
  headers: {
    'X-API-Key': 'YOUR_API_KEY',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    phone_number: '87001234567',
    amount: 5000,
    billing_period: 'monthly',
    description: 'Monthly subscription'
  })
})
const data = await response.json()
console.log('Subscription:', data.subscription.id)
```

### Upload Image + Create Catalog Item

#### cURL
```bash
# Step 1: Upload image
IMAGE_ID=$(curl -s -X POST https://bpapi.bazarbay.site/api/v1/catalog/upload-image \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "image=@product.jpg" | jq -r '.image_id')

# Step 2: Create item with image
curl -X POST https://bpapi.bazarbay.site/api/v1/catalog \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"items\": [{
      \"name\": \"Coffee Latte\",
      \"selling_price\": 1800,
      \"unit_id\": 1,
      \"image_id\": \"$IMAGE_ID\"
    }]
  }"
```

### Refund

#### cURL
```bash
# Full refund
curl -X POST https://bpapi.bazarbay.site/api/v1/invoices/42/refund \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Customer request"}'

# Partial refund
curl -X POST https://bpapi.bazarbay.site/api/v1/invoices/42/refund \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"amount": 5000, "reason": "Partial return"}'
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request — invalid state or missing prerequisites |
| 401 | Unauthorized — invalid, missing or expired API key |
| 403 | Forbidden — organization not verified |
| 404 | Not Found |
| 422 | Validation Error |
| 429 | Too Many Requests — rate limit exceeded (check `retry_after`) |
| 500 | Server Error |
| 502 | Bad Gateway — Kaspi API error |
| 503 | Service Unavailable — Kaspi session expired |

### Error Response Format

```json
{
  "message": "Error description",
  "errors": {
    "field_name": ["error details"]
  }
}
```
