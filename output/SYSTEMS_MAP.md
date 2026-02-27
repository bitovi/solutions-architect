# Systems Map: Bitovi Training Microservices

**Generated:** 2026-02-28  
**Source:** Compose-first discovery from `bitovi-training/service-infra/docker-compose.yml`  
**Repositories Analyzed:** 8 (4 services + 2 auth middleware + 1 infra + 1 tests)

---

## Executive Summary

This is a microservices-based e-commerce platform with four core services (order, product, user, loyalty) orchestrated via Docker Compose. Services communicate via HTTP REST APIs using environment-variable-based service discovery. Authentication follows a distributed validation pattern with centralized JWT generation.

**Key Characteristics:**
- **Authentication:** Centralized token generation (user-service), distributed validation (auth middleware per service)
- **Service Discovery:** Environment variables (`*_SERVICE_URL`)
- **Authorization:** Role-Based Access Control (admin/user roles)
- **Storage:** In-memory (development/demo only)
- **Tech Stack:** Mixed (Go for order-service, NestJS for others)

---

## Repositories in Scope

All repositories cloned locally to `/Users/nikita/solutions-architect/workdir/repos/`

| Repository | Owner | Purpose | Status |
|------------|-------|---------|--------|
| service-infra | bitovi-training | Docker Compose orchestration | ✅ Analyzed |
| order-service | bitovi-training | Order management (Go) | ✅ Analyzed |
| product-service | bitovi-training | Product catalog (NestJS) | ✅ Analyzed |
| user-service | bitovi-training | Authentication provider (NestJS) | ✅ Analyzed |
| loyalty-service | bitovi-training | Loyalty points management (NestJS) | ✅ Analyzed |
| auth-middleware | bitovi-corp | Node.js auth library | ✅ Analyzed |
| auth-middleware-go | bitovi-corp | Go auth library | ✅ Analyzed |
| api-tests | bitovi-training | Integration test suite | ✅ Analyzed |

**Discovery Method:**
1. Started with docker-compose.yml from service-infra
2. Extracted build contexts to identify service repos
3. Searched package.json and go.mod for auth middleware dependencies
4. Located api-tests via repository pattern matching

---

## Service Inventory

### 1. order-service

**Repository:** `bitovi-training/order-service`  
**Purpose:** E-commerce order management with product validation and loyalty point integration  
**Tech Stack:** Go 1.25.5  
**Runtime Port:** `8100` (docker-compose), `8080` (code default)  

**Docker Images:**
- Build: `FROM golang:1.25.5-alpine AS builder` ([Dockerfile:2](workdir/repos/order-service/Dockerfile#L2))
- Runtime: `FROM alpine:latest` ([Dockerfile:19](workdir/repos/order-service/Dockerfile#L19))

**Environment Variables (docker-compose.yml):**
```yaml
PORT: 8100
PRODUCT_SERVICE_URL: http://product-service:8200
LOYALTY_SERVICE_URL: http://loyalty-service:8300
```

**Dependencies:**
- product-service (outbound: validate products, get pricing)
- loyalty-service (outbound: accrue loyalty points)
- auth-middleware-go v0.2.0 ([go.mod:6](workdir/repos/order-service/go.mod#L6))

---

### 2. product-service

**Repository:** `bitovi-training/product-service`  
**Purpose:** Product catalog API with in-memory storage  
**Tech Stack:** NestJS 11.0.1, Node.js 20-alpine, TypeScript 5.7.3  
**Runtime Port:** `8200` (docker-compose), `3000` (code default)

**Docker Images:**
- Build: `FROM node:20-alpine AS builder` ([Dockerfile:2](workdir/repos/product-service/Dockerfile#L2))
- Runtime: `FROM node:20-alpine` ([Dockerfile:17](workdir/repos/product-service/Dockerfile#L17))

**Environment Variables (docker-compose.yml):**
```yaml
PORT: 8200
```

**Dependencies:**
- auth-middleware v0.1.0 ([package.json:23](workdir/repos/product-service/package.json#L23))
- No outbound service calls

---

### 3. user-service

**Repository:** `bitovi-training/user-service`  
**Purpose:** Authentication service with JWT token generation  
**Tech Stack:** NestJS, Node.js 20-alpine, TypeScript, bcrypt  
**Runtime Port:** `8400` (docker-compose), `3002` (code default)

**Docker Images:**
- Build: `FROM node:20-alpine AS builder` ([Dockerfile:2](workdir/repos/user-service/Dockerfile#L2))
- Runtime: `FROM node:20-alpine` ([Dockerfile:19](workdir/repos/user-service/Dockerfile#L19))

**Environment Variables (docker-compose.yml):**
```yaml
PORT: 8400
```

**Dependencies:**
- No external service dependencies
- Does NOT use auth-middleware (generates tokens, doesn't validate)

---

### 4. loyalty-service

**Repository:** `bitovi-training/loyalty-service`  
**Purpose:** Loyalty points management with balance, redemption, and order integration  
**Tech Stack:** NestJS, Node.js 20-alpine, TypeScript  
**Runtime Port:** `8300` (docker-compose), `3000` (code default)

**Docker Images:**
- Build: `FROM node:20-alpine AS builder` ([Dockerfile:2](workdir/repos/loyalty-service/Dockerfile#L2))
- Runtime: `FROM node:20-alpine` ([Dockerfile:18](workdir/repos/loyalty-service/Dockerfile#L18))

**Environment Variables (docker-compose.yml):**
```yaml
PORT: 8300
ORDER_SERVICE_URL: http://order-service:8100
USER_SERVICE_URL: http://user-service:8400
```

**Dependencies:**
- order-service (outbound: fetch orders)
- user-service (outbound: validate users)
- auth-middleware v0.1.0 ([package.json:23](workdir/repos/loyalty-service/package.json#L23))

---

## Service Endpoints

### order-service (Port 8100)

**No route prefix** (verified: no global prefix in codebase)

| Method | Endpoint | Auth | Role | Purpose | Evidence |
|--------|----------|------|------|---------|----------|
| GET | `/health` | ❌ | - | Health check | [main.go:34](workdir/repos/order-service/cmd/server/main.go#L34) |
| GET | `/orders` | ✅ | admin | List all orders | [main.go:38](workdir/repos/order-service/cmd/server/main.go#L38) |
| POST | `/orders` | ✅ | admin | Create order | [main.go:38](workdir/repos/order-service/cmd/server/main.go#L38) |
| GET | `/orders/{orderId}` | ✅ | admin | Get order by ID | [main.go:37](workdir/repos/order-service/cmd/server/main.go#L37) |
| PATCH | `/orders/{orderId}` | ✅ | admin | Update order | [main.go:37](workdir/repos/order-service/cmd/server/main.go#L37) |
| POST | `/orders/{orderId}/submit` | ✅ | admin | Submit/cancel order | [main.go:37](workdir/repos/order-service/cmd/server/main.go#L37) |

**Middleware:**
- LoggingMiddleware (all endpoints) - [logging.go:11-26](workdir/repos/order-service/internal/middleware/logging.go#L11-L26)
- AuthMiddleware + RequireRoles("admin") (all except /health) - [main.go:37-38](workdir/repos/order-service/cmd/server/main.go#L37-L38)

---

### product-service (Port 8200)

**No global prefix** (verified: no `setGlobalPrefix` in codebase)  
**Controller prefix:** `/products` ([products.controller.ts:10](workdir/repos/product-service/src/products/products.controller.ts#L10))

| Method | Endpoint | Auth | Role | Purpose | Evidence |
|--------|----------|------|------|---------|----------|
| GET | `/products` | ❌ | - | List all products | [products.controller.ts:28](workdir/repos/product-service/src/products/products.controller.ts#L28) |
| GET | `/products/:id` | ✅ | - | Get product by ID | [products.controller.ts:39](workdir/repos/product-service/src/products/products.controller.ts#L39) |
| POST | `/products` | ✅ | admin | Create product | [products.controller.ts:63](workdir/repos/product-service/src/products/products.controller.ts#L63) |

**Auth Guards:**
- AuthGuard (GET/:id, POST) - [products.controller.ts:38,62](workdir/repos/product-service/src/products/products.controller.ts#L38)
- RequireRolesGuard(['admin']) (POST only) - [products.controller.ts:62](workdir/repos/product-service/src/products/products.controller.ts#L62)

---

### user-service (Port 8400)

**No global prefix** (verified: no `setGlobalPrefix` in codebase)

| Method | Endpoint | Auth | Purpose | Evidence |
|--------|----------|------|---------|----------|
| POST | `/auth/signup` | ❌ | Register user | [auth.controller.ts:17](workdir/repos/user-service/src/auth/auth.controller.ts#L17) |
| POST | `/auth/signin` | ❌ | Authenticate user | [auth.controller.ts:31](workdir/repos/user-service/src/auth/auth.controller.ts#L31) |
| POST | `/auth/logout` | ✅ | Logout user | [auth.controller.ts:45](workdir/repos/user-service/src/auth/auth.controller.ts#L45) |
| GET | `/users/:userId/validate` | ❌ | Check user exists | [user.controller.ts:13](workdir/repos/user-service/src/user/user.controller.ts#L13) |
| GET | `/health` | ❌ | Health check | [health.controller.ts:8](workdir/repos/user-service/src/health/health.controller.ts#L8) |

**Note:** Only `/auth/logout` requires authentication. All other endpoints are public (intentional - this is the auth provider).

---

### loyalty-service (Port 8300)

**No global prefix** (verified: no `setGlobalPrefix` in codebase)  
**Controller prefix:** `/loyalty` ([loyalty.controller.ts:13](workdir/repos/loyalty-service/src/loyalty/loyalty.controller.ts#L13))

| Method | Endpoint | Auth | Purpose | Evidence |
|--------|----------|------|---------|----------|
| GET | `/loyalty/:userId/balance` | ✅ | Get points balance | [loyalty.controller.ts:22](workdir/repos/loyalty-service/src/loyalty/loyalty.controller.ts#L22) |
| POST | `/loyalty/:userId/redeem` | ✅ | Redeem points | [loyalty.controller.ts:38](workdir/repos/loyalty-service/src/loyalty/loyalty.controller.ts#L38) |
| GET | `/loyalty/:userId/redemptions` | ✅ | Get redemption history | [loyalty.controller.ts:62](workdir/repos/loyalty-service/src/loyalty/loyalty.controller.ts#L62) |
| POST | `/loyalty/orders` | ✅ | Accrue order points | [loyalty.controller.ts:73](workdir/repos/loyalty-service/src/loyalty/loyalty.controller.ts#L73) |

**Auth Guards:**
- AuthGuard from `@bitovi-corp/auth-middleware` applied to all endpoints

---

## Service Integration Map

### Call Graph

```
┌─────────────────┐
│  user-service   │
│   (port 8400)   │◄──────────────────────┐
└─────────────────┘                       │
         │                                │ validate user
         │ (JWT generation)               │
         ▼                                │
┌─────────────────┐     validate    ┌─────────────────┐
│  order-service  │◄────products────│ product-service │
│   (port 8100)   │                 │   (port 8200)   │
└─────────────────┘                 └─────────────────┘
         │
         │ accrue points
         ▼
┌─────────────────┐
│ loyalty-service │
│   (port 8300)   │
└─────────────────┘
         │
         └────fetch orders────┐
                              │
                              ▼
                     ┌─────────────────┐
                     │  order-service  │
                     │   (port 8100)   │
                     └─────────────────┘
```

---

## Detailed Integration Specifications

### Integration 1: order-service → product-service

**Purpose:** Validate product exists and retrieve pricing

**Configuration:**
- Env Var: `PRODUCT_SERVICE_URL`
- Docker Value: `http://product-service:8200`
- Code Reference: [config.go](workdir/repos/order-service/internal/config/config.go)

**Request:**
- Method: `GET`
- Path: `/products/{productId}`
- Full URL: `${PRODUCT_SERVICE_URL}/products/{productId}`
- Headers:
  - `Content-Type: application/json`
  - `Authorization: {forwarded Bearer token}` ([product_client.go:59-65](workdir/repos/order-service/internal/services/product_client.go#L59-L65))

**Response:** Status 200
```json
{
  "id": 1,
  "name": "string",
  "description": "string",
  "price": 0.0,
  "availability": true
}
```

**Called From:**
- CreateOrder handler ([orders.go](workdir/repos/order-service/internal/handlers/orders.go))
- UpdateOrder handler ([orders.go](workdir/repos/order-service/internal/handlers/orders.go))

**Evidence:** [product_client.go:45-73](workdir/repos/order-service/internal/services/product_client.go#L45-L73)

---

### Integration 2: order-service → loyalty-service

**Purpose:** Calculate and store loyalty points for submitted orders

**Configuration:**
- Env Var: `LOYALTY_SERVICE_URL`
- Docker Value: `http://loyalty-service:8300`
- Code Reference: [config.go](workdir/repos/order-service/internal/config/config.go)

**Request:**
- Method: `POST`
- Path: `/loyalty/orders`
- Full URL: `${LOYALTY_SERVICE_URL}/loyalty/orders`
- Headers:
  - `Content-Type: application/json` ([loyalty_client.go:66](workdir/repos/order-service/internal/services/loyalty_client.go#L66))
  - `Authorization: {forwarded token}` ([loyalty_client.go:68-70](workdir/repos/order-service/internal/services/loyalty_client.go#L68-L70))

**Request Payload:**
```json
{
  "orderId": "string (UUID)",
  "userId": "string (UUID)",
  "totalPrice": 0.0
}
```
**Evidence:** [loyalty_client.go:23-27](workdir/repos/order-service/internal/services/loyalty_client.go#L23-L27)

**Payload Validation (receiver):**
- `orderId`: UUID, required ([accrue-points-request.dto.ts:4-6](workdir/repos/loyalty-service/src/loyalty/dto/accrue-points-request.dto.ts#L4-L6))
- `userId`: UUID, required ([accrue-points-request.dto.ts:8-10](workdir/repos/loyalty-service/src/loyalty/dto/accrue-points-request.dto.ts#L8-L10))
- `totalPrice`: number, min 0, required ([accrue-points-request.dto.ts:12-14](workdir/repos/loyalty-service/src/loyalty/dto/accrue-points-request.dto.ts#L12-L14))

**Response:** Status 201
```json
{
  "orderId": "string",
  "userId": "string",
  "points": 0
}
```

**Called From:**
- SubmitOrder handler when status changes to PROCESSING ([orders.go](workdir/repos/order-service/internal/handlers/orders.go))

**Evidence:** [loyalty_client.go:46-69](workdir/repos/order-service/internal/services/loyalty_client.go#L46-L69)

---

### Integration 3: loyalty-service → order-service

**Purpose:** Fetch order data to calculate loyalty balances

**Configuration:**
- Env Var: `ORDER_SERVICE_URL`
- Docker Value: `http://order-service:8100`
- Fallback: `http://localhost:8100` ([order-client.ts:37](workdir/repos/loyalty-service/src/clients/order-client.ts#L37))

**Request 1: Get All Orders**
- Method: `GET`
- Path: `/orders`
- Full URL: `${ORDER_SERVICE_URL}/orders`
- Headers:
  - `Content-Type: application/json`
  - `Authorization: Bearer {token}` (if provided) ([order-client.ts:53-55](workdir/repos/loyalty-service/src/clients/order-client.ts#L53-L55))

**Response:**
```typescript
{
  orders: [
    {
      id: string,
      userId: string,
      products: [{ productId: string, quantity: number }],
      totalPrice: number,
      accruedLoyaltyPoints?: number,
      orderDate: string,
      status: string
    }
  ],
  total: number
}
```
**Evidence:** [order-client.ts:11-28](workdir/repos/loyalty-service/src/clients/order-client.ts#L11-L28)

**Request 2: Get Order by ID**
- Method: `GET`
- Path: `/orders/{orderId}`
- Full URL: `${ORDER_SERVICE_URL}/orders/{orderId}`
- Headers: Same as Request 1
- Evidence: [order-client.ts:82-101](workdir/repos/loyalty-service/src/clients/order-client.ts#L82-L101)

---

### Integration 4: loyalty-service → user-service

**Purpose:** Validate user exists before accruing/redeeming points

**Configuration:**
- Env Var: `USER_SERVICE_URL`
- Docker Value: `http://user-service:8400`
- Fallback: `http://localhost:8400`

**Request:**
- Method: `GET`
- Path: `/users/{userId}/validate`
- Full URL: `${USER_SERVICE_URL}/users/${userId}/validate`
- Headers:
  - `Content-Type: application/json`
  - **No Authorization header** (service-to-service validation)

**Response:**
```json
{
  "exists": true,
  "userId": "string"
}
```

**Called From:**
- accruePoints ([loyalty.service.ts](workdir/repos/loyalty-service/src/loyalty/loyalty.service.ts))
- redeemPoints ([loyalty.service.ts](workdir/repos/loyalty-service/src/loyalty/loyalty.service.ts))
- getBalance ([loyalty.service.ts](workdir/repos/loyalty-service/src/loyalty/loyalty.service.ts))
- getRedemptionHistory ([loyalty.service.ts](workdir/repos/loyalty-service/src/loyalty/loyalty.service.ts))

**Evidence:** [user-client.ts:13-46](workdir/repos/loyalty-service/src/clients/user-client.ts#L13-L46)

---

## Authentication & Authorization Model

### Architecture

**Model:** Centralized token generation + distributed validation

1. **Token Provider:** user-service generates JWT tokens
2. **Token Consumers:** order-service, product-service, loyalty-service validate via auth middleware
3. **Validation:** Each service independently validates JWT structure and claims (no central gateway)

### JWT Token Structure

**Generated By:** user-service ([jwt.service.ts](workdir/repos/user-service/src/auth/jwt.service.ts))

**Token Format:**
```json
{
  "sub": "user-id (UUID)",
  "email": "user@example.com",
  "roles": ["user", "admin"],
  "iat": 1737000000,
  "exp": 1737086400
}
```

**Characteristics:**
- Algorithm: `none` (⚠️ **MOCK** - no cryptographic signing)
- Expiration: 24 hours (production) or 30 days (development)
- Structure: `<base64url_header>.<base64url_payload>.` (no signature)
- Evidence: [jwt.service.ts:26-69](workdir/repos/user-service/src/auth/jwt.service.ts#L26-L69)

⚠️ **CRITICAL WARNING:** Tokens lack signatures and are NOT production-ready.

---

### Auth Middleware Implementations

#### Node/NestJS: @bitovi-corp/auth-middleware v0.1.0

**Used By:** product-service, loyalty-service

**Exports:**
- `AuthGuard` - JWT validation guard
- `RequireRolesGuard` - Role-based access control (any-of)
- `RequireAllRolesGuard` - RBAC (all-of)
- `@User()` decorator - Extract user claims
- `@Roles()` decorator - Declare required roles
- `AuthModule` - NestJS module

**JWT Validation:** [auth.guard.ts:23-82](workdir/repos/auth-middleware/src/guards/auth.guard.ts#L23-L82)
- Validates 3-part structure (header.payload.signature)
- Base64url decodes payload
- Checks required: `sub`, `email`
- Extracts optional: `roles` (defaults []), `exp`, `iat`
- **Does NOT verify signature** (mock mode)
- Accepts expired tokens with warning

**Role Checking:** [require-roles.guard.ts](workdir/repos/auth-middleware/src/guards/require-roles.guard.ts)
- Any-of: User needs ONE of specified roles
- All-of: User needs ALL specified roles
- Case-sensitive comparison
- Returns 403 if insufficient

---

#### Go: github.com/bitovi-corp/auth-middleware-go v0.2.0

**Used By:** order-service

**Exports:**
- `AuthMiddleware` - Basic JWT authentication
- `RequireRoles(roles ...string)` - Any-of role checking
- `RequireAllRoles(roles ...string)` - All-of role checking
- `GetUserClaims(r *http.Request)` - Context retrieval
- `UserClaims` struct - Token claims model

**JWT Validation:** [auth.go:40-91](workdir/repos/auth-middleware-go/middleware/auth.go#L40-L91)
- Validates 3-part structure
- Base64-decodes payload
- Checks required: `sub`, `email`, `roles`, `exp`
- **Does NOT verify signature** (mock mode)
- Accepts expired tokens with warning

**Role Checking:** [auth.go:93-195](workdir/repos/auth-middleware-go/middleware/auth.go#L93-L195)
- `RequireRoles`: Any-of (≥1 specified role)
- `RequireAllRoles`: All-of (all specified roles)
- Returns 403 with JSON error

---

### Role Definitions

**Based on seeded users:** [user.repository.ts:13-48](workdir/repos/user-service/src/user/user.repository.ts#L13-L48)

| Role | Permissions | Usage |
|------|-------------|-------|
| `admin` | Full access to orders, products, loyalty | order-service, product-service |
| `user` | Basic authenticated access | Default for new signups |
| `manager` | Not currently enforced | Seeded but unused |

**RBAC Usage:**
- **order-service:** Requires `admin` for all order operations ([main.go:37-38](workdir/repos/order-service/cmd/server/main.go#L37-L38))
- **product-service:** Requires `admin` for POST /products ([products.controller.ts:62](workdir/repos/product-service/src/products/products.controller.ts#L62))
- **loyalty-service:** Requires authentication but no role restrictions

---

### Auth Header Forwarding

**Pattern:** Services forward `Authorization: Bearer {token}` to downstream services

**Evidence:**
1. order-service → product-service: [product_client.go:59-65](workdir/repos/order-service/internal/services/product_client.go#L59-L65)
2. order-service → loyalty-service: [loyalty_client.go:68-70](workdir/repos/order-service/internal/services/loyalty_client.go#L68-L70)
3. loyalty-service → order-service: [order-client.ts:53-55](workdir/repos/loyalty-service/src/clients/order-client.ts#L53-L55)
4. loyalty-service → user-service: ❌ **NO AUTH** (validation endpoint is service-to-service)

---

## Test Coverage (api-tests)

**Repository:** `bitovi-training/api-tests`  
**Framework:** Jest + TypeScript + Axios

**Services Tested:**
1. **user-service** - 5 endpoints, 12 test cases
2. **order-service** - 6 endpoints, 35+ test cases
3. **product-service** - 3 endpoints, 15+ test cases
4. **loyalty-service** - 4 endpoints, 14 test cases
5. **E2E Integration** - 7 complete flow scenarios

**Key Scenarios:**
- Complete purchase flow: signup → browse → order → submit → accrue points → redeem
- RBAC enforcement (401/403 for missing/invalid roles)
- Validation errors (400 for invalid payloads)
- Service-to-service integration (order→product, order→loyalty)

**Auth Testing:**
- Mock JWT generation with configurable roles
- Bearer token authentication patterns
- Case-sensitive role validation
- Missing/malformed token scenarios

**Evidence:** Test files in [src/](workdir/repos/api-tests/src)

---

## Known Issues & Spec Drift

### Issue 1: Insecure JWT Implementation

**Problem:** Both auth middleware implementations lack signature verification

**Impact:** Tokens can be forged by base64-encoding arbitrary claims

**Evidence:**
- Node: [auth.guard.ts:23-82](workdir/repos/auth-middleware/src/guards/auth.guard.ts#L23-L82)
- Go: [auth.go:40-91](workdir/repos/auth-middleware-go/middleware/auth.go#L40-L91)

**Status:** ⚠️ **INTENTIONAL FOR DEMO** - Not production-ready

---

### Issue 2: Port Mismatch

**Problem:** Services default to different ports in code vs docker-compose

**Details:**
- product-service: Code 3000, docker 8200
- loyalty-service: Code 3000, docker 8300
- user-service: Code 3002, docker 8400
- order-service: Code 8080, docker 8100

**Impact:** Services won't communicate correctly outside docker-compose without env vars

**Mitigation:** docker-compose.yml correctly overrides via PORT environment variable

---

### Issue 3: In-Memory Storage

**Problem:** All services use ephemeral in-memory storage

**Impact:** Data lost on restart, not production-suitable

**Evidence:**
- order-service: Mock data in handlers
- product-service: [products.service.ts](workdir/repos/product-service/src/products/products.service.ts) Map storage
- user-service: [user.repository.ts](workdir/repos/user-service/src/user/user.repository.ts) Map storage
- loyalty-service: [loyalty.service.ts](workdir/repos/loyalty-service/src/loyalty/loyalty.service.ts) Map storage

**Status:** ✅ **INTENTIONAL FOR DEMO**

---

### Issue 4: Inefficient Order Fetching

**Problem:** loyalty-service fetches ALL orders then filters client-side by userId

**Evidence:** [order-client.ts:119-127](workdir/repos/loyalty-service/src/clients/order-client.ts#L119-L127)

**Impact:** Performance degrades as order count grows

**Recommendation:** order-service should expose query param: `GET /orders?userId={id}`

**Status:** ⚠️ **SPEC GAP**

---

### Issue 5: No API Versioning

**Finding:** No services use `/api/v1` or similar prefixes

**Verification:**
- Searched for `setGlobalPrefix` in all TypeScript services (0 results)
- Verified Go service uses root-level routes

**Impact:** Breaking changes require synchronized deployments

**Status:** ✅ **CONFIRMED - NO VERSIONING**

---

## Environment Variables Reference

### order-service
```bash
PORT=8100
PRODUCT_SERVICE_URL=http://product-service:8200
LOYALTY_SERVICE_URL=http://loyalty-service:8300
```

### product-service
```bash
PORT=8200
```

### user-service
```bash
PORT=8400
NODE_ENV=development  # Affects token expiry (24h prod, 30d dev)
```

### loyalty-service
```bash
PORT=8300
ORDER_SERVICE_URL=http://order-service:8100
USER_SERVICE_URL=http://user-service:8400
```

---

## Seeded Test Users

**Source:** [user.repository.ts:13-48](workdir/repos/user-service/src/user/user.repository.ts#L13-L48)

**All users password:** `password123`

| Email | Roles | Use Case |
|-------|-------|----------|
| admin@example.com | admin, user | Full order/product management |
| user@example.com | user | Basic access |
| manager@example.com | manager, user | Reserved (unused) |
| test@example.com | user | Test account |

---

## Generation Metadata

**Generated:** 2026-02-28  
**Method:** Compose-first discovery with parallel subagent analysis  
**Repositories:** 8 cloned to local workdir/repos/  

**Validation Performed:**
- ✅ Route prefix verification (none found)
- ✅ Dockerfile FROM lines extracted
- ✅ Endpoint verification via route registration
- ✅ Integration payload verification via client code + DTOs
- ✅ Auth header forwarding confirmed

---

**End of Systems Map**
