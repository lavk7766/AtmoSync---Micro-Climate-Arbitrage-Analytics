# AtmoSync – Supporting Data Schema Plan

**Status:** Proposed for team review — not yet approved
**Purpose:** Define the supporting data structures that connect sensor telemetry with container, commodity-price, and route information.

These schemas follow the project's data dictionary. Field types, units, required fields, and example values below are proposals for team confirmation.

---

## 1. Container Metadata Schema

Describes each shipment/container and the product being transported.

| Field | Proposed data type | Unit / format | Description |
|---|---|---|---|
| `container_id` | STRING | — | Unique container identifier; primary reference for telemetry |
| `product_name` | STRING | — | Commodity or product carried |
| `quantity` | FLOAT | Numeric | Quantity of product in the shipment |
| `quantity_unit` | STRING | e.g. `tonne`, `kg` | Unit used for `quantity` |
| `origin` | STRING | — | Shipment origin |
| `destination` | STRING | — | Shipment destination |
| `batch_id` | STRING | — | Shipment or product batch identifier |
| `source_type` | STRING | — | Origin of the record, e.g. `synthetic_simulated` |

### Example record

```json
{
  "container_id": "CONT001",
  "product_name": "Tomatoes",
  "quantity": 18.5,
  "quantity_unit": "tonne",
  "origin": "Pune",
  "destination": "Delhi",
  "batch_id": "BATCH001",
  "source_type": "synthetic_simulated"
}
```

### Proposed validation
- `container_id` must be present and unique in the container metadata dataset.
- `product_name`, `origin`, and `destination` must not be empty.
- `quantity` must be numeric and greater than zero.
- `quantity_unit` must be explicit; do not infer units from the numeric value.
- `batch_id` and `source_type` must be present if required by the agreed project workflow.

**Unit recommendation:** Use `tonne` as the default shipment quantity unit if the team agrees, while retaining `quantity_unit` so records with other units remain unambiguous. Convert quantities to a common unit before comparing or aggregating them.

---

## 2. Commodity Price Schema

Stores a commodity's observed price for a particular market and time.

| Field | Proposed data type | Unit / format | Description |
|---|---|---|---|
| `product_name` | STRING | — | Commodity being priced |
| `market_name` | STRING | — | Market or location associated with the price |
| `price` | FLOAT | Numeric | Observed commodity price |
| `currency` | STRING | ISO 4217 code, e.g. `INR` | Currency of the price |
| `price_timestamp` | TIMESTAMP | UTC | Date and time when the price applies or was recorded |
| `source_type` | STRING | — | Origin of the record, e.g. `synthetic_simulated` |

### Example record

```json
{
  "product_name": "Tomatoes",
  "market_name": "Azadpur Mandi",
  "price": 2400.0,
  "currency": "INR",
  "price_timestamp": "2026-11-06T08:30:00Z",
  "source_type": "synthetic_simulated"
}
```

### Proposed validation
- `product_name` and `market_name` must not be empty.
- `price` must be numeric and non-negative.
- `currency` must be an agreed currency code; do not mix currencies without conversion.
- `price_timestamp` must be a valid UTC timestamp.
- `source_type` should identify whether the record is simulated or sourced externally.

**Important:** The team must define what the price represents (for example, per kg, per quintal, or per tonne). The current data dictionary does not specify a price unit. Add a `price_unit` field before implementation if prices may use different quantity units.

---

## 3. Route Schema

Describes the route and estimated transport details for a shipment.

| Field | Proposed data type | Unit / format | Description |
|---|---|---|---|
| `origin` | STRING | — | Starting location |
| `destination` | STRING | — | Destination location |
| `distance_km` | FLOAT | Kilometres (km) | Route distance |
| `estimated_travel_hours` | FLOAT | Hours (h) | Estimated travel duration |
| `transport_cost` | FLOAT | Numeric | Estimated transport cost |
| `currency` | STRING | ISO 4217 code, e.g. `INR` | Currency of transport cost |
| `source_type` | STRING | — | Origin of the record, e.g. `synthetic_simulated` |

### Example record

```json
{
  "origin": "Pune",
  "destination": "Delhi",
  "distance_km": 1420.0,
  "estimated_travel_hours": 24.0,
  "transport_cost": 28000.0,
  "currency": "INR",
  "source_type": "synthetic_simulated"
}
```

### Proposed validation
- `origin` and `destination` must not be empty.
- `distance_km` and `estimated_travel_hours` must be numeric and greater than zero.
- `transport_cost` must be numeric and non-negative.
- `currency` must be explicit and consistent when costs are compared.
- `source_type` should identify the record's origin.

---

## 4. Relationships Between the Datasets

| Dataset | Join / matching fields | Purpose |
|---|---|---|
| Sensor telemetry | `container_id` | Attach sensor readings to a container |
| Container metadata | `container_id` | Identify product, quantity, batch and shipment locations |
| Commodity prices | `product_name` + `market_name` + relevant timestamp | Match a product to a market price at the appropriate time |
| Route data | `origin` + `destination` | Match a shipment to its route and estimated transport details |

The team should confirm how market selection and timestamp matching will work for commodity prices. Matching only on `product_name` may be insufficient when prices differ by market or time.

---

## 5. Decisions to Confirm Before Implementation

1. **Quantity unit:** Should shipment quantity use `tonne` as the default, with `quantity_unit` retained?
2. **Price unit:** Is commodity price quoted per kg, quintal, tonne, crate, or another unit? Should `price_unit` be added?
3. **Price identity:** Is a unique price-record ID required, and can multiple records exist for the same product, market, and timestamp?
4. **Route identity:** Can multiple routes exist for the same origin and destination? If so, should the record include a `route_id` or another distinguishing field?
5. **Source values:** Which `source_type` values will the project use?
6. **Storage and ingestion:** Will these be static/reference datasets, database records, or separate Kafka messages? This is an architecture decision and is not assumed by this document.
7. **Ownership:** Confirm who will provide, generate, maintain, and validate each dataset.

---

## Scope note

This document proposes the **data schemas**, not the Kafka topic design. It does not assume that container metadata, commodity prices, or route records must each become separate Kafka topics. The team should decide their source, update frequency, storage location, and ingestion method before those implementation details are finalized.

All sample names, quantities, prices, distances, and costs are illustrative only. Confirm the schema and business units with the team before treating them as final.
