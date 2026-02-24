# Implementation Plan: product-service — Add `doubleLoyaltyPoints` Product Field

**Date**: 2026-02-24
**Repo**: `bitovi-training/product-service`
**Step**: 1 (must be completed before order-service and loyalty-service changes)

---

## 1. Problem Summary

A new boolean product field `doubleLoyaltyPoints` needs to be added to the product-service. When a product has `doubleLoyaltyPoints: true`, any order containing that product should yield **double loyalty points** for the price contribution of that product. The product-service is the **source of truth** for product data and must expose this field so downstream services (order-service, loyalty-service) can use it in loyalty points calculations.

---

## 2. Assumptions & Constraints

- **No database**: product-service uses in-memory storage (a `Product[]` array with seed data). No migrations needed.
- **Backward-compatible**: The new field defaults to `false`, so existing products and API consumers are unaffected.
- **Field semantics**: `doubleLoyaltyPoints` is a simple boolean. The product-service does NOT calculate loyalty points — it only stores and exposes the flag. Points calculation is the responsibility of the loyalty-service.
- **Optional on creation**: When creating a product via `POST /products`, the field is optional and defaults to `false`.
- **Technology**: NestJS 11.x, TypeScript 5.7, class-validator, class-transformer. Uses `@bitovi-corp/auth-middleware` for auth guards.
- **Validation**: Uses `ValidationPipe` with `whitelist: true` and `forbidNonWhitelisted: true` globally — meaning the DTO must explicitly declare the field or it will be stripped/rejected.

---

## 3. Related Systems/Repos That Are Affected

| Repo | Impact | Dependency Direction |
|---|---|---|
| **order-service** (Go) | Must read `doubleLoyaltyPoints` from product-service responses when validating products. Must pass double-loyalty subtotal info to loyalty-service during order submission. | Downstream consumer of product-service API |
| **loyalty-service** (NestJS/TS) | Must accept an optional `doubleLoyaltyPointsTotal` in the accrual request and apply a 2x multiplier to that portion when calculating points. | Downstream consumer (called by order-service) |

**This plan must be implemented first** because order-service reads product data from the product-service API. The field must be available in the API response before order-service can consume it.

---

## 4. Contract & Schema Changes

### Product Entity — Add `doubleLoyaltyPoints` field

**File**: `src/products/entities/product.entity.ts`

**Current**:
```typescript
export interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  availability: boolean;
}
```

**Proposed**:
```typescript
export interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  availability: boolean;
  doubleLoyaltyPoints: boolean;
}
```

### CreateProductDto — Add optional `doubleLoyaltyPoints` field

**File**: `src/products/dto/create-product.dto.ts`

Add to the existing DTO class:
```typescript
@IsOptional()
@IsBoolean()
doubleLoyaltyPoints?: boolean;
```

### API Response Contract Change

All endpoints that return `Product` objects will now include the `doubleLoyaltyPoints` field:

- `GET /products` → `{ data: Product[], count: number }` — each Product now includes `doubleLoyaltyPoints: boolean`
- `GET /products/:id` → `Product` — now includes `doubleLoyaltyPoints: boolean`
- `POST /products` → `Product` — now includes `doubleLoyaltyPoints: boolean`

This is a **backward-compatible additive change** — existing consumers that don't use this field can safely ignore it.

---

## 5. Data Flow Updates

### Before
```
Product Service API → { id, name, description, price, availability }
```

### After
```
Product Service API → { id, name, description, price, availability, doubleLoyaltyPoints }
```

No new endpoints. No changes to authentication or authorization. The field flows through existing `GET /products` and `GET /products/:id` responses.

---

## 6. Proposed Changes for the Repo

### 6.1 `src/products/entities/product.entity.ts`

Add `doubleLoyaltyPoints: boolean` to the `Product` interface.

```typescript
export interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  availability: boolean;
  doubleLoyaltyPoints: boolean;
}
```

### 6.2 `src/products/dto/create-product.dto.ts`

Add the optional field with validation decorators (consistent with existing patterns like `availability`):

```typescript
@IsOptional()
@IsBoolean()
doubleLoyaltyPoints?: boolean;
```

### 6.3 `src/products/products.service.ts`

**Seed data**: Add `doubleLoyaltyPoints` to each hardcoded product. Set most products to `false` and at least 1-2 to `true` for testing:

```typescript
private products: Product[] = [
  {
    id: 1,
    name: 'Laptop Pro',
    description: 'High-performance laptop with 16GB RAM and 512GB SSD',
    price: 1299.99,
    availability: true,
    doubleLoyaltyPoints: true,    // ← flagship product gets double points
  },
  {
    id: 2,
    name: 'Wireless Mouse',
    description: 'Ergonomic wireless mouse with precision tracking',
    price: 29.99,
    availability: true,
    doubleLoyaltyPoints: false,
  },
  {
    id: 3,
    name: 'Mechanical Keyboard',
    description: 'RGB mechanical keyboard with cherry MX switches',
    price: 149.99,
    availability: true,
    doubleLoyaltyPoints: true,    // ← premium peripheral gets double points
  },
  {
    id: 4,
    name: 'USB-C Hub',
    description: '7-in-1 USB-C hub with HDMI, USB 3.0, and SD card reader',
    price: 49.99,
    availability: false,
    doubleLoyaltyPoints: false,
  },
  {
    id: 5,
    name: 'Laptop Stand',
    description: 'Adjustable aluminum laptop stand for better ergonomics',
    price: 39.99,
    availability: true,
    doubleLoyaltyPoints: false,
  },
];
```

**`create()` method**: Apply the default value when creating a new product:

```typescript
create(payload: CreateProductDto): Product {
  const product: Product = {
    id: this.nextId++,
    name: payload.name,
    description: payload.description ?? '',
    price: payload.price ?? 0.01,
    availability: payload.availability ?? true,
    doubleLoyaltyPoints: payload.doubleLoyaltyPoints ?? false,
  };

  this.products.push(product);
  return product;
}
```

### 6.4 `src/products/products.controller.ts`

**No changes needed.** The controller passes the DTO through to the service and returns the `Product` entity directly. The new field will flow through automatically.

### 6.5 `src/products/products.service.spec.ts`

Update all test assertions and mock data to include `doubleLoyaltyPoints`:

- **`findAll` tests**: Add `doubleLoyaltyPoints` to the list of required fields checked with `toHaveProperty` and type assertions.
- **`findOne` tests**: Add `doubleLoyaltyPoints` to returned product property checks.
- **`create` tests**: 
  - Test that explicit `doubleLoyaltyPoints: true` is stored.
  - Test that omitting the field defaults to `false`.

Example additions:
```typescript
// In findAll tests:
expect(product).toHaveProperty('doubleLoyaltyPoints');
expect(typeof product.doubleLoyaltyPoints).toBe('boolean');

// In findOne tests:
expect(typeof product.doubleLoyaltyPoints).toBe('boolean');

// In create tests - explicit true:
it('should store doubleLoyaltyPoints when provided', () => {
  const product = service.create({
    name: 'Premium Widget',
    doubleLoyaltyPoints: true,
  });
  expect(product.doubleLoyaltyPoints).toBe(true);
});

// In create tests - default:
it('should default doubleLoyaltyPoints to false', () => {
  const product = service.create({ name: 'Minimal Product' });
  expect(product.doubleLoyaltyPoints).toBe(false);
});
```

### 6.6 `src/products/products.controller.spec.ts`

Update all mock product objects to include `doubleLoyaltyPoints`:

```typescript
// findAll mock:
const mockResult = {
  data: [
    {
      id: 1,
      name: 'Test Product',
      description: 'Test description',
      price: 99.99,
      availability: true,
      doubleLoyaltyPoints: false,
    },
  ],
  count: 1,
};

// findOne mock:
const mockProduct = {
  id: 1,
  name: 'Test Product',
  description: 'Test description',
  price: 99.99,
  availability: true,
  doubleLoyaltyPoints: false,
};

// create mock and request payloads:
const mockProduct = {
  id: 101,
  name: 'New Product',
  description: 'New description',
  price: 12.34,
  availability: true,
  doubleLoyaltyPoints: false,
};
```

### 6.7 `test/products.contract-spec.ts`

Update contract test payloads and assertions:

```typescript
it('POST /products returns Product schema with 201', () => {
  return request(app.getHttpServer())
    .post('/products')
    .send({
      name: 'Laptop Pro',
      description: 'High-performance laptop with 16GB RAM and 512GB SSD',
      price: 1299.99,
      availability: true,
      doubleLoyaltyPoints: true,
    })
    .expect(201)
    .expect((res) => {
      expect(res.body).toEqual({
        id: expect.any(Number),
        name: 'Laptop Pro',
        description: 'High-performance laptop with 16GB RAM and 512GB SSD',
        price: 1299.99,
        availability: true,
        doubleLoyaltyPoints: true,
      });
    });
});
```

Also add a test confirming the default value works when the field is omitted:

```typescript
it('POST /products defaults doubleLoyaltyPoints to false when omitted', () => {
  return request(app.getHttpServer())
    .post('/products')
    .send({
      name: 'Basic Widget',
      price: 9.99,
    })
    .expect(201)
    .expect((res) => {
      expect(res.body.doubleLoyaltyPoints).toBe(false);
    });
});
```

---

## 7. Security & Compliance Considerations

- **No new auth requirements**: The field is read-only through existing authenticated (`GET /products/:id`) and unauthenticated (`GET /products`) endpoints.
- **Admin-only creation**: Product creation (`POST /products`) already requires `admin` role via `RequireRolesGuard`. Adding the field does not change access control.
- **Input validation**: The `@IsBoolean()` decorator with `@IsOptional()` ensures only valid boolean values are accepted. The global `ValidationPipe` with `forbidNonWhitelisted: true` prevents injection of unexpected fields.
- **No PII or sensitive data**: The `doubleLoyaltyPoints` field is a simple business configuration flag.

---

## 8. Risks, Unknowns, and Open Questions

| Item | Type | Detail |
|---|---|---|
| Seed data choice | Decision | Which products should default to `doubleLoyaltyPoints: true`? Plan suggests Laptop Pro (id=1) and Mechanical Keyboard (id=3) as "premium" items. Adjust as needed. |
| No API spec file | Note | product-service has no `api/openapi.yaml`. The contract is implicitly defined by the entity and DTO. The order-service maintains its own copy of the Product schema in its OpenAPI spec — that will need updating separately (covered in the order-service plan). |
| Downstream readiness | Risk | If product-service is deployed with this field before order-service/loyalty-service are updated, the new field is simply ignored by downstream consumers. **This is safe.** |
| No breaking changes | Confirmed | This is a purely additive change. Existing API consumers will continue to work without modification. |
