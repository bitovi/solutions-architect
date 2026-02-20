# Bitovi Microservices System Map (AI Agent Context)

This document provides a cross-repo system map for the following repositories.

All listed repositories are part of the **`bitovi-training` GitHub organization**:

- `api-tests`
- `auth-middleware`
- `auth-middleware-go`
- `loyalty-service`
- `order-service`
- `product-service`
- `user-service`

It is intended as a fast, practical context layer for AI agents navigating and modifying this ecosystem.

---

## 1) System at a glance

### Runtime topology (local default)

- **order-service** (Go): `http://localhost:8100`
- **product-service** (NestJS): `http://localhost:8200`
- **loyalty-service** (NestJS): `http://localhost:8300`
- **user-service** (NestJS): `http://localhost:8400`

`service-infra/docker-compose.yml` wires service-to-service URLs:

- order-service → product-service (`PRODUCT_SERVICE_URL`)
- order-service → loyalty-service (`LOYALTY_SERVICE_URL`)
- loyalty-service → order-service (`ORDER_SERVICE_URL`)
- loyalty-service → user-service (`USER_SERVICE_URL`)

### High-level request/data flow

1. A user signs up/signs in via **user-service** and gets a mock JWT.
2. JWT is used to call protected endpoints in **order-service**, **product-service**, **loyalty-service**.
3. **order-service** reads product data from **product-service** for pricing/validation.
4. On submit, **order-service** posts order accrual data to **loyalty-service** (`POST /loyalty/orders`).
5. **loyalty-service** calculates balances from order data and redemptions, and validates users through **user-service**.
6. **api-tests** executes end-to-end and domain test suites against all services.

---

## 2) Auth model (shared assumptions)

### Core behavior

- Auth is **mock JWT-based** (intended for development/testing).
- Tokens are parsed for claims (`sub`, `email`, `roles`, `exp`, etc.).
- Signature verification is intentionally not enforced in current middleware implementations.

### Libraries

- **NestJS services** use: `@bitovi-corp/auth-middleware` (`auth-middleware` repo)
  - `AuthGuard`
  - `RequireRolesGuard` (any-of semantics)
  - `RequireAllRolesGuard` (all-of semantics)
  - decorators such as `@Roles()`
- **Go services** use: `github.com/bitovi-corp/auth-middleware-go/middleware` (`auth-middleware-go` repo)
  - `AuthMiddleware`
  - `RequireRoles(...)` (any-of semantics)
  - `RequireAllRoles(...)` (all-of semantics)

### Important caveat for agents

Do not assume production-grade JWT verification or token revocation durability in this environment. Several components explicitly describe this as mock/dev behavior.

---

## 3) Repository map

## `user-service` (NestJS auth service)

### Responsibility

- Registration, authentication, and logout.
- Issues mock JWT tokens consumed by other services.
- Exposes user-validation endpoint used by loyalty-service.

### Key endpoints

- `POST /auth/signup`
- `POST /auth/signin`
- `POST /auth/logout`
- `GET /health`
- `GET /users/:userId/validate`

### Notable implementation notes

- Global validation pipe enabled.
- In-memory storage patterns (users + blacklist behavior discussed in docs).
- Compatible token payload includes at least `sub`, `email`, `roles`, `iat`, `exp`.

---

## `product-service` (NestJS catalog)

### Responsibility

- In-memory product catalog APIs.

### Key endpoints and auth

- `GET /products` → public
- `GET /products/:id` → `AuthGuard`
- `POST /products` → `AuthGuard` + `RequireRolesGuard` + `@Roles('admin')`

### Notable implementation notes

- Minimal bounded context: product listing, lookup, and create.
- Consumed by order-service via HTTP client for order creation/update validation.

---

## `order-service` (Go order workflow)

### Responsibility

- Order lifecycle management and status transitions.
- Integrates with product-service (product lookup/pricing context).
- Integrates with loyalty-service for loyalty accrual on submit.

### Key endpoints and auth

- `GET /health` → public
- `GET /orders` → admin role required
- `POST /orders` → admin role required
- `GET /orders/{orderId}` → admin role required
- `PATCH /orders/{orderId}` → admin role required
- `POST /orders/{orderId}/submit` → admin role required

Auth and logging are composed centrally in `cmd/server/main.go`.

### Notable implementation notes

- Contract-first orientation around `api/openapi.yaml`.
- Uses `auth-middleware-go` for role-based enforcement.
- On submit flow, uses loyalty client to call `POST /loyalty/orders`.

---

## `loyalty-service` (NestJS loyalty domain)

### Responsibility

- Loyalty balance calculation, redemption processing, and redemption history.
- Loyalty point accrual intake from order-service submissions.
- User validation through user-service API.

### Key endpoints and auth

- `GET /loyalty/:userId/balance` → `AuthGuard`
- `POST /loyalty/:userId/redeem` → `AuthGuard`
- `GET /loyalty/:userId/redemptions` → `AuthGuard`
- `POST /loyalty/orders` → `AuthGuard` (called by order-service)

### Upstream/downstream integrations

- Calls order-service via `OrderClient` (`ORDER_SERVICE_URL`)
- Calls user-service via `UserClient` (`USER_SERVICE_URL`)

### Notable implementation notes

- Balance is derived from order data + redemptions.
- Integration docs indicate migration from hardcoded users to user-service validation.

---

## `auth-middleware` (NestJS shared auth package)

### Responsibility

- Reusable NestJS auth/authorization building blocks for services.

### Main exports/concepts

- `AuthGuard` (parse/validate token shape + claims)
- `RequireRolesGuard` (`@Roles(...)`, any-of)
- `RequireAllRolesGuard` (`@RequireAllRoles(...)`, all-of)
- `@User()` parameter decorator for claims extraction

### Agent guidance

- Prefer using this package in NestJS services instead of duplicating auth logic.
- Role comparisons are case-sensitive.

---

## `auth-middleware-go` (Go shared auth package)

### Responsibility

- Reusable Go HTTP middleware for token checks + RBAC.

### Main exports/concepts

- `AuthMiddleware(next)`
- `RequireRoles(roles...)` (any-of)
- `RequireAllRoles(roles...)` (all-of)
- `GetUserClaims(r)`

### Agent guidance

- Prefer composition with this middleware in Go handlers.
- Keep auth behavior consistent with Nest counterpart when changing cross-service access behavior.

---

## `api-tests` (cross-service E2E and API validation)

### Responsibility

- End-to-end and service-level API tests (Jest + TypeScript).
- Validates auth behavior, role constraints, and full commerce flows across services.

### Environment expectations

- Uses `.env` (auto-generated from `.env.example` if missing).
- Defaults:
  - `USER_SERVICE_URL=http://localhost:8400`
  - `ORDER_SERVICE_URL=http://localhost:8100`
  - `PRODUCT_SERVICE_URL=http://localhost:8200`
  - `LOYALTY_SERVICE_URL=http://localhost:8300`

### Coverage shape

- user auth flows (`/auth/signup`, `/auth/signin`, `/auth/logout`)
- product endpoints and admin enforcement
- order lifecycle and submission behavior
- loyalty balance/redeem/history and accrual input
- full E2E flows across multiple services

---

## 4) Service dependency graph

```text
                     +-------------------+
                     |   user-service    |
                     |  auth + users API |
                     +---------+---------+
                               ^
                               | validate user
                               |
+-------------------+   calls  |    +-------------------+
|   loyalty-service +----------+    |   api-tests       |
| balance/redeem    |<--------------+ e2e + domain APIs |
| accrual endpoint  | tests all      +-------------------+
+---------+---------+
          ^
          | POST /loyalty/orders (submit accrual)
          |
+---------+---------+      fetch products      +-------------------+
|    order-service  +------------------------->|  product-service  |
| order workflow    |                          | catalog endpoints |
+-------------------+                          +-------------------+

Shared auth libs:
- NestJS services use auth-middleware
- Go services use auth-middleware-go
```

---

## 5) Common ports and env vars

### Ports (compose/local convention)

- `8100` → order-service
- `8200` → product-service
- `8300` → loyalty-service
- `8400` → user-service

### Frequently referenced env vars

- `PORT`
- `PRODUCT_SERVICE_URL` (order-service)
- `LOYALTY_SERVICE_URL` (order-service)
- `ORDER_SERVICE_URL` (loyalty-service)
- `USER_SERVICE_URL` (loyalty-service)

---

## 6) Agent playbook (recommended workflow)

When changing behavior across this system:

1. **Trace impacted contracts first**
   - order-service OpenAPI + controller routes
   - NestJS controller DTO/guard combinations
2. **Check auth + role impacts**
   - verify both middleware packages if semantics should stay aligned
3. **Update integration points**
   - especially order ↔ loyalty and loyalty ↔ user interactions
4. **Update/extend `api-tests`**
   - treat tests as cross-repo safety net for regressions
5. **Reconcile local infra assumptions**
   - ensure env vars and compose wiring remain consistent

---

## 7) Known constraints / non-goals in current system

- Mock JWT behavior is intentional in multiple repos (not production hardened).
- Services are demo-friendly and often in-memory by design.
- Auth expectations are strict in role checks (case sensitivity can matter in tests).

---

## 8) Canonical references per repo

- `api-tests/README.md`
- `auth-middleware/README.md`
- `auth-middleware-go/README.md`
- `loyalty-service/README.md`
- `loyalty-service/ORDER_CLIENT.md`
- `loyalty-service/USER_SERVICE_INTEGRATION.md`
- `order-service/README.md`
- `order-service/cmd/server/main.go`
- `product-service/README.md`
- `product-service/src/products/products.controller.ts`
- `user-service/README.md`
- `user-service/src/controllers/user.controller.ts`
- `service-infra/README.md`
- `service-infra/docker-compose.yml`
