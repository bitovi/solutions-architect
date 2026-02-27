# Systems Map: Bitovi Training Microservices Architecture

**Generated:** 2026-02-27  
**Source:** Compose-first discovery from `bitovi-training/service-infra/docker-compose.yml`  
**Repositories Analyzed:** 8 (4 services + 2 auth middleware + 1 infra + 1 tests)

---

## Executive Summary

This is a microservices-based e-commerce platform consisting of four core services (order, product, user, loyalty) orchestrated via Docker Compose. All services except user-service require JWT Bearer authentication. Services communicate via HTTP REST APIs with environment-variable-based service discovery.

**Key Architectural Characteristics:**
- **Authentication Model:** Centralized JWT generation (user-service), distributed validation (auth middleware in each service)
- **Service Discovery:** Environment variables (`*_SERVICE_URL`)
- **Authorization:** Role-Based Access Control (RBAC) with "admin" and "user" roles
- **Storage:** In-memory (development/demo only)
- **Tech Stack:** Mixed (Go for order-service, NestJS/Node.js for others)

---

## Service Inventory

### 1. order-service

**Repository:** `bitovi-training/order-service`  
**Purpose:** E-commerce order management API providing order CRUD operations with product validation and loyalty point integration  
**Tech Stack:** Go 1.25.5  
**Runtime Port:** `8100` (from docker-compose.yml)  
**Dockerfile:**
- Line 2: `FROM golang:1.25.5-alpine AS builder` ([workdir/repos/order-service/Dockerfile:2](workdir/repos/order-service/Dockerfile#L2))
- Line 18: `FROM alpine:latest` ([workdir/repos/order-service/Dockerfile:18](workdir/repos/order-service/Dockerfile#L18))

**Environment Variables:**
- `PORT=8100` (docker-compose.yml)
- `PRODUCT_SERVICE_URL=http://product-service:8200` (docker-compose.yml)
- `LOYALTY_SERVICE_URL=http://loyalty-service:8300` (docker-compose.yml)

**Dependencies:**
- product-service (outbound: product validation)
- loyalty-service (outbound: point accrual)
- auth-middleware-go v0.2.0 ([workdir/repos/order-service/go.mod:6](workdir/repos/order-service/go.mod#L6))

---

### 2. product-service

**Repository:** `bitovi-training/product-service`  
**Purpose:** NestJS service that exposes a minimal catalog API for products with in-memory storage  
**Tech Stack:** NestJS 11.0.1, Node.js 20-alpine, TypeScript 5.7.3  
**Runtime Port:** `8200` (from docker-compose.yml)  
**Dockerfile:**
- Line 2: `FROM node:20-alpine AS builder` ([workdir/repos/product-service/Dockerfile:2](workdir/repos/product-service/Dockerfile#L2))
- Line 18: `FROM node:20-alpine` ([workdir/repos/product-service/Dockerfile:18](workdir/repos/product-service/Dockerfile#L18))

**Environment Variables:**
- `PORT=8200` (docker-compose.yml)

**Dependencies:**
- auth-middleware v0.1.0 ([workdir/repos/product-service/package.json:23](workdir/repos/product-service/package.json#L23))
- No outbound service calls

---

### 3. user-service

**Repository:** `bitovi-training/user-service`  
**Purpose:** NestJS-based authentication service providing user registration (sign up), authentication (sign in), and logout functionality with JWT token generation  
**Tech Stack:** NestJS, Node.js 20-alpine, TypeScript, bcrypt  
**Runtime Port:** `8400` (from docker-compose.yml)  
**Dockerfile:**
- Line 2: `FROM node:20-alpine AS builder` ([workdir/repos/user-service/Dockerfile:2](workdir/repos/user-service/Dockerfile#L2))
- Line 19: `FROM node:20-alpine` ([workdir/repos/user-service/Dockerfile:19](workdir/repos/user-service/Dockerfile#L19))

**Environment Variables:**
- `PORT=8400` (docker-compose.yml)

**Dependencies:**
- No external service dependencies
- **Does NOT use auth-middleware** (generates tokens, doesn't validate)

---

### 4. loyalty-service

**Repository:** `bitovi-training/loyalty-service`  
**Purpose:** Manages customer loyalty points including balance calculation, point redemption, and order service integration  
**Tech Stack:** NestJS, Node.js 20-alpine, TypeScript  
**Runtime Port:** `8300` (from docker-compose.yml)  
**Dockerfile:**
- Line 2: `FROM node:20-alpine AS builder` ([workdir/repos/loyalty-service/Dockerfile:2](workdir/repos/loyalty-service/Dockerfile#L2))
- Line 18: `FROM node:20-alpine` ([workdir/repos/loyalty-service/Dockerfile:18](workdir/repos/loyalty-service/Dockerfile#L18))

**Environment Variables:**
- `PORT=8300` (docker-compose.yml)
- `ORDER_SERVICE_URL=http://order-service:8100` (docker-compose.yml)
- `USER_SERVICE_URL=http://user-service:8400` (docker-compose.yml)

**Dependencies:**
- order-service (outbound: fetch orders)
- user-service (outbound: user validation)
- auth-middleware v0.1.0 ([workdir/repos/loyalty-service/package.json:23](workdir/repos/loyalty-service/package.json#L23))

---

## Service Endpoints

### order-service (Port 8100)

**No route prefix** (verified: no global prefix in codebase)

| Method | Endpoint | Auth | Role | Purpose | Evidence |
|--------|----------|------|------|---------|----------|
| GET | `/health` | ❌ No | - | Health check | [cmd/server/main.go:35](workdir/repos/order-service/cmd/server/main.go#L35) |
| GET | `/orders` | ✅ Yes | admin | List all orders | [cmd/server/main.go:38](workdir/repos/order-service/cmd/server/main.go#L38) |
| POST | `/orders` | ✅ Yes | admin | Create new order | [cmd/server/main.go:38](workdir/repos/order-service/cmd/server/main.go#L38) |
| GET | `/orders/{orderId}` | ✅ Yes | admin | Get order by ID | [cmd/server/main.go:37](workdir/repos/order-service/cmd/server/main.go#L37) |
| PATCH | `/orders/{orderId}` | ✅ Yes | admin | Update order products | [cmd/server/main.go:37](workdir/repos/order-service/cmd/server/main.go#L37) |
| POST | `/orders/{orderId}/submit` | ✅ Yes | admin | Submit or cancel order | [cmd/server/main.go:37](workdir/repos/order-service/cmd/server/main.go#L37) |

**Middleware Stack:**
1. LoggingMiddleware (all endpoints) - [internal/middleware/logging.go:11-26](workdir/repos/order-service/internal/middleware/logging.go#L11-L26)
2. AuthMiddleware from `github.com/bitovi-corp/auth-middleware-go` (all except /health) - [cmd/server/main.go:37-38](workdir/repos/order-service/cmd/server/main.go#L37-L38)

---

### product-service (Port 8200)

**No route prefix** (verified: no `setGlobalPrefix` in [src/main.ts](workdir/repos/product-service/src/main.ts))  
**Controller prefix:** `/products` ([src/products/products.controller.ts:10](workdir/repos/product-service/src/products/products.controller.ts#L10))

| Method | Endpoint | Auth | Role | Purpose | Evidence |
|--------|----------|------|------|---------|----------|
| GET | `/products` | ❌ No | - | List all products | [src/products/products.controller.ts:28](workdir/repos/product-service/src/products/products.controller.ts#L28) |
| GET | `/products/:id` | ✅ Yes | - | Get product by ID | [src/products/products.controller.ts:39](workdir/repos/product-service/src/products/products.controller.ts#L39) |
| POST | `/products` | ✅ Yes | admin | Create product | [src/products/products.controller.ts:63](workdir/repos/product-service/src/products/products.controller.ts#L63) |

**Auth Middleware:**
- AuthGuard applied to GET/:id and POST ([src/products/products.controller.ts:38,62](workdir/repos/product-service/src/products/products.controller.ts#L38))
- RequireRolesGuard(['admin']) applied to POST ([src/products/products.controller.ts:62](workdir/repos/product-service/src/products/products.controller.ts#L62))

---

### user-service (Port 8400)

**No route prefix** (verified: no `setGlobalPrefix` in [src/main.ts](workdir/repos/user-service/src/main.ts))

| Method | Endpoint | Auth | Purpose | Evidence |
|--------|----------|------|---------|----------|
| POST | `/auth/signup` | ❌ No | Register new user | [src/auth/auth.controller.ts:17](workdir/repos/user-service/src/auth/auth.controller.ts#L17) |
| POST | `/auth/signin` | ❌ No | Authenticate user | [src/auth/auth.controller.ts:31](workdir/repos/user-service/src/auth/auth.controller.ts#L31) |
| POST | `/auth/logout` | ❌ No | Logout user | [src/auth/auth.controller.ts:45](workdir/repos/user-service/src/auth/auth.controller.ts#L45) |
| GET | `/users/:userId/validate` | ❌ No | Check if user exists | [src/user/user.controller.ts:13](workdir/repos/user-service/src/user/user.controller.ts#L13) |
| GET | `/health` | ❌ No | Health check | [src/health/health.controller.ts:8](workdir/repos/user-service/src/health/health.controller.ts#L8) |

**⚠️ Security Note:** All endpoints are publicly accessible. This service generates tokens but does not validate them (intentional - acts as authentication provider).

---

### loyalty-service (Port 8300)

**No route prefix** (verified: no `setGlobalPrefix` in [src/main.ts](workdir/repos/loyalty-service/src/main.ts))  
**Controller prefix:** `/loyalty` ([src/loyalty/loyalty.controller.ts:13](workdir/repos/loyalty-service/src/loyalty/loyalty.controller.ts#L13))

| Method | Endpoint | Auth | Purpose | Evidence |
|--------|----------|------|---------|----------|
| GET | `/loyalty/:userId/balance` | ✅ Yes | Get loyalty balance | [src/loyalty/loyalty.controller.ts:22](workdir/repos/loyalty-service/src/loyalty/loyalty.controller.ts#L22) |
| POST | `/loyalty/:userId/redeem` | ✅ Yes | Redeem loyalty points | [src/loyalty/loyalty.controller.ts:38](workdir/repos/loyalty-service/src/loyalty/loyalty.controller.ts#L38) |
| GET | `/loyalty/:userId/redemptions` | ✅ Yes | Get redemption history | [src/loyalty/loyalty.controller.ts:62](workdir/repos/loyalty-service/src/loyalty/loyalty.controller.ts#L62) |
| POST | `/loyalty/orders` | ✅ Yes | Accrue points for order | [src/loyalty/loyalty.controller.ts:73](workdir/repos/loyalty-service/src/loyalty/loyalty.controller.ts#L73) |

**Auth Middleware:**
- AuthGuard from `@bitovi-corp/auth-middleware` applied to all endpoints ([src/loyalty/loyalty.controller.ts:23,39,63,75](workdir/repos/loyalty-service/src/loyalty/loyalty.controller.ts#L23))

---

## Service Integration Map

### Call Graph

```
┌─────────────────┐
│  user-service   │
│   (port 8400)   │◄──────────────────────────┐
└─────────────────┘                           │
         │                                    │
         │ (JWT generation)                   │ validate user
         │                                    │
         ▼                                    │
┌─────────────────┐      validate      ┌─────────────────┐
│  order-service  │◄──────products─────│ product-service │
│   (port 8100)   │                    │   (port 8200)   │
└─────────────────┘                    └─────────────────┘
         │
         │ accrue points
         ▼
┌─────────────────┐
│ loyalty-service │
│   (port 8300)   │
└─────────────────┘
         │
         └────────fetch orders───────┐
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

**Purpose:** Validate product exists and get pricing information

**Source:** [workdir/repos/order-service/internal/services/product_client.go:45-73](workdir/repos/order-service/internal/services/product_client.go#L45-L73)

**Configuration:**
- Base URL Env Var: `PRODUCT_SERVICE_URL`
- Docker Compose Value: `http://product-service:8200`

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
- CreateOrder flow ([internal/handlers/orders.go](workdir/repos/order-service/internal/handlers/orders.go))
- UpdateOrderProducts flow ([internal/handlers/orders.go](workdir/repos/order-service/internal/handlers/orders.go))

---

### Integration 2: order-service → loyalty-service

**Purpose:** Calculate and store loyalty points for submitted orders

**Source:** [workdir/repos/order-service/internal/services/loyalty_client.go:46-69](workdir/repos/order-service/internal/services/loyalty_client.go#L46-L69)

**Configuration:**
- Base URL Env Var: `LOYALTY_SERVICE_URL`
- Docker Compose Value: `http://loyalty-service:8300`

**Request:**
- Method: `POST`
- Path: `/loyalty/orders`
- Full URL: `${LOYALTY_SERVICE_URL}/loyalty/orders`
- Headers:
  - `Content-Type: application/json` ([loyalty_client.go:66](workdir/repos/order-service/internal/services/loyalty_client.go#L66))
  - `Authorization: {forwarded token}` ([loyalty_client.go:68-70](workdir/repos/order-service/internal/services/loyalty_client.go#L68-L70))

**Request Payload:** ([loyalty_client.go:23-27](workdir/repos/order-service/internal/services/loyalty_client.go#L23-L27))
```json
{
  "orderId": "string (UUID)",
  "userId": "string (UUID)",
  "totalPrice": 0.0
}
```

**Payload Validation (receiver side):** [workdir/repos/loyalty-service/src/loyalty/dto/accrue-points-request.dto.ts:3-14](workdir/repos/loyalty-service/src/loyalty/dto/accrue-points-request.dto.ts#L3-L14)
- `orderId`: UUID, required
- `userId`: UUID, required
- `totalPrice`: number, min 0, required

**Response:** Status 201
```json
{
  "orderId": "string",
  "userId": "string",
  "points": 0
}
```
Evidence: [loyalty_client.go:29-33](workdir/repos/order-service/internal/services/loyalty_client.go#L29-L33)

**Called From:**
- SubmitOrder flow when order status changes to PROCESSING ([internal/handlers/orders.go](workdir/repos/order-service/internal/handlers/orders.go))

---

### Integration 3: loyalty-service → order-service

**Purpose:** Fetch order data to calculate loyalty balances

**Source:** [workdir/repos/loyalty-service/src/clients/order-client.ts:46-77](workdir/repos/loyalty-service/src/clients/order-client.ts#L46-L77)

**Configuration:**
- Base URL Env Var: `ORDER_SERVICE_URL`
- Docker Compose Value: `http://order-service:8100`
- Fallback: `http://localhost:8100` ([order-client.ts:37](workdir/repos/loyalty-service/src/clients/order-client.ts#L37))

**Request 1: Get All Orders**
- Method: `GET`
- Path: `/orders`
- Full URL: `${ORDER_SERVICE_URL}/orders`
- Headers:
  - `Content-Type: application/json` ([order-client.ts:49-51](workdir/repos/loyalty-service/src/clients/order-client.ts#L49-L51))
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
Evidence: [order-client.ts:11-28](workdir/repos/loyalty-service/src/clients/order-client.ts#L11-L28)

**Request 2: Get Order by ID**
- Method: `GET`
- Path: `/orders/{orderId}`
- Full URL: `${ORDER_SERVICE_URL}/orders/{orderId}`
- Headers: Same as Request 1
- Evidence: [order-client.ts:82-101](workdir/repos/loyalty-service/src/clients/order-client.ts#L82-L101)

---

### Integration 4: loyalty-service → user-service

**Purpose:** Validate that a user exists before accruing/redeeming points

**Source:** [workdir/repos/loyalty-service/src/clients/user-client.ts:13-46](workdir/repos/loyalty-service/src/clients/user-client.ts#L13-L46)

**Configuration:**
- Base URL Env Var: `USER_SERVICE_URL`
- Docker Compose Value: `http://user-service:8400`
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
Evidence: [user-client.ts:24](workdir/repos/loyalty-service/src/clients/user-client.ts#L24)

**Called From:**
- accruePoints ([src/loyalty/loyalty.service.ts](workdir/repos/loyalty-service/src/loyalty/loyalty.service.ts))
- redeemPoints ([src/loyalty/loyalty.service.ts](workdir/repos/loyalty-service/src/loyalty/loyalty.service.ts))
- getBalance ([src/loyalty/loyalty.service.ts](workdir/repos/loyalty-service/src/loyalty/loyalty.service.ts))
- getRedemptionHistory ([src/loyalty/loyalty.service.ts](workdir/repos/loyalty-service/src/loyalty/loyalty.service.ts))

---

## Authentication & Authorization Model

### Architecture Overview

**Model:** Centralized token generation + distributed validation

1. **Token Provider:** user-service generates JWT tokens
2. **Token Consumers:** order-service, product-service, loyalty-service validate tokens using shared auth middleware
3. **Validation:** Each service independently validates JWT structure and claims (no central auth service)

### JWT Token Structure

**Generated By:** user-service ([src/auth/jwt.service.ts](workdir/repos/user-service/src/auth/jwt.service.ts))

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

**Token Characteristics:**
- Algorithm: `none` (⚠️ **MOCK IMPLEMENTATION** - no cryptographic signing)
- Expiration: 24 hours (production) or 30 days (development)
- Structure: `<base64url_header>.<base64url_payload>.` (no signature)
- Evidence: [workdir/repos/user-service/src/auth/jwt.service.ts:26-69](workdir/repos/user-service/src/auth/jwt.service.ts#L26-L69)

⚠️ **CRITICAL SECURITY WARNING:** Tokens lack cryptographic signatures and are NOT production-ready.

---

### Auth Middleware Implementations

#### Node/NestJS: @bitovi-corp/auth-middleware v0.1.0

**Repository:** `bitovi-corp/auth-middleware`  
**Used By:** product-service, loyalty-service

**Exports:**
- `AuthGuard` - JWT validation guard
- `RequireRolesGuard` - Role-based access control (RBAC)
- `@User()` decorator - Extract user claims
- `@Roles()` decorator - Declare required roles
- `AuthModule` - NestJS module

**JWT Validation Logic:** [workdir/repos/auth-middleware/src/guards/auth.guard.ts:23-82](workdir/repos/auth-middleware/src/guards/auth.guard.ts#L23-L82)
- Validates 3-part JWT structure (header.payload.signature)
- Base64url decodes payload
- Checks required claims: `sub`, `email`
- Extracts optional claims: `roles` (defaults to []), `exp`, `iat`
- **Does NOT verify signature** (mock mode)
- Accepts expired tokens with warning log

**Role Checking:** [workdir/repos/auth-middleware/src/guards/require-roles.guard.ts](workdir/repos/auth-middleware/src/guards/require-roles.guard.ts)
- Supports "any-of" and "all-of" role matching
- Case-sensitive role comparison
- Returns 403 Forbidden if roles insufficient

---

#### Go: github.com/bitovi-corp/auth-middleware-go v0.2.0

**Repository:** `bitovi-corp/auth-middleware-go`  
**Used By:** order-service

**Exports:**
- `AuthMiddleware` - Basic JWT authentication
- `RequireRoles(roles ...string)` - Any-of role checking
- `RequireAllRoles(roles ...string)` - All-of role checking
- `GetUserClaims(r *http.Request)` - Context retrieval helper
- `UserClaims` struct - Token claims model

**JWT Validation Logic:** [workdir/repos/auth-middleware-go/middleware/auth.go:40-91](workdir/repos/auth-middleware-go/middleware/auth.go#L40-L91)
- Validates 3-part JWT structure
- Base64-decodes payload
- Checks required claims: `sub`, `email`, `roles`, `exp`
- **Does NOT verify signature** (mock mode)
- Accepts expired tokens with warning log

**Role Checking:** [middleware/auth.go:93-195](workdir/repos/auth-middleware-go/middleware/auth.go#L93-L195)
- `RequireRoles`: Any-of (user needs at least one specified role)
- `RequireAllRoles`: All-of (user needs all specified roles)
- Returns 403 Forbidden with JSON error

---

### Role Definitions

Based on seeded users ([workdir/repos/user-service/src/user/user.repository.ts:13-48](workdir/repos/user-service/src/user/user.repository.ts#L13-L48)):

| Role | Permissions | Evidence |
|------|-------------|----------|
| `admin` | Full access to all order, product, loyalty operations | order-service, product-service |
| `user` | Basic authenticated access | Default role for new signups |
| `manager` | Not currently used in RBAC rules | Seeded but no guards check for it |

**RBAC Usage:**
- **order-service:** Requires `admin` role for all order operations ([cmd/server/main.go:37-38](workdir/repos/order-service/cmd/server/main.go#L37-L38))
- **product-service:** Requires `admin` role for POST /products ([src/products/products.controller.ts:62](workdir/repos/product-service/src/products/products.controller.ts#L62))
- **loyalty-service:** Requires authentication but no role restrictions (any authenticated user)

---

### Auth Header Forwarding

**Pattern:** Services forward `Authorization: Bearer {token}` to downstream services

**Evidence:**
1. **order-service → product-service:** [internal/services/product_client.go:59-65](workdir/repos/order-service/internal/services/product_client.go#L59-L65)
2. **order-service → loyalty-service:** [internal/services/loyalty_client.go:68-70](workdir/repos/order-service/internal/services/loyalty_client.go#L68-L70)
3. **loyalty-service → order-service:** [src/clients/order-client.ts:53-55](workdir/repos/loyalty-service/src/clients/order-client.ts#L53-L55)
4. **loyalty-service → user-service:** ❌ **NO AUTH FORWARDED** (validation endpoint is service-to-service)

---

## Test Coverage (api-tests repo)

**Repository:** `bitovi-training/api-tests`  
**Framework:** Jest + TypeScript  
**Test Suites:** 5 suites covering 100+ scenarios

**Services Tested:**
1. **user-service** - 5 endpoints, 20+ test cases
2. **order-service** - 6 endpoints, 40+ test cases
3. **product-service** - 3 endpoints, 15+ test cases
4. **loyalty-service** - 4 endpoints, 25+ test cases

**Key Test Scenarios:**
- Complete purchase flow: signup → browse → create order → submit → loyalty accrual → redemption
- RBAC enforcement (401/403 errors for missing/insufficient roles)
- Validation rules (400 errors for invalid payloads)
- Service-to-service integration (order→product, order→loyalty)

**Evidence:** [workdir/repos/api-tests/src](workdir/repos/api-tests/src)

---

## Known Issues & Spec Drift

### Issue 1: Insecure JWT Implementation

**Problem:** Both auth middleware implementations lack cryptographic signature verification

**Impact:** Tokens can be forged by base64-encoding arbitrary claims

**Evidence:**
- Node: [workdir/repos/auth-middleware/src/guards/auth.guard.ts:23-82](workdir/repos/auth-middleware/src/guards/auth.guard.ts#L23-L82)
- Go: [workdir/repos/auth-middleware-go/middleware/auth.go:40-91](workdir/repos/auth-middleware-go/middleware/auth.go#L40-91)

**Status:** ⚠️ **INTENTIONAL FOR DEMO** - Not production-ready

---

### Issue 2: Port Mismatch (service-internal vs docker-compose)

**Problem:** Services default to different ports in code vs docker-compose

**Details:**
- **product-service:** Code defaults to 3000, docker-compose overrides to 8200
- **loyalty-service:** Code defaults to 3000, docker-compose overrides to 8300
- **user-service:** Code defaults to 3002, docker-compose overrides to 8400

**Evidence:**
- [workdir/repos/product-service/src/main.ts:11](workdir/repos/product-service/src/main.ts#L11)
- [workdir/repos/loyalty-service/src/main.ts:11](workdir/repos/loyalty-service/src/main.ts#L11)
- [workdir/repos/user-service/src/main.ts:9](workdir/repos/user-service/src/main.ts#L9)
- docker-compose.yml environment overrides

**Impact:** Services won't communicate correctly if run outside docker-compose without env vars

**Resolution:** Environment variables correctly configured in docker-compose.yml

---

### Issue 3: In-Memory Storage (All Services)

**Problem:** All services use ephemeral in-memory storage

**Impact:** Data lost on restart, not suitable for production

**Evidence:**
- order-service: [internal/handlers/orders.go](workdir/repos/order-service/internal/handlers/orders.go) (mock data)
- product-service: [src/products/products.service.ts](workdir/repos/product-service/src/products/products.service.ts) (Map storage)
- user-service: [src/user/user.repository.ts](workdir/repos/user-service/src/user/user.repository.ts) (Map storage)
- loyalty-service: [src/loyalty/loyalty.service.ts](workdir/repos/loyalty-service/src/loyalty/loyalty.service.ts) (Map storage)

**Status:** ✅ **INTENTIONAL FOR DEMO**

---

### Issue 4: Inefficient Order Fetching in loyalty-service

**Problem:** loyalty-service fetches ALL orders then filters client-side by userId

**Evidence:** [workdir/repos/loyalty-service/src/clients/order-client.ts:119-127](workdir/repos/loyalty-service/src/clients/order-client.ts#L119-L127)

**Impact:** Performance degrades as order count grows

**Recommendation:** order-service should expose `GET /orders?userId={id}` query param

**Status:** ⚠️ **SPEC GAP**

---

### Issue 5: No API Versioning

**Finding:** No services use `/api/v1` or similar route prefixes

**Verification:**
- Searched for `setGlobalPrefix`, `app.use`, route prefixes in all services
- Result: No versioning found

**Impact:** Breaking changes cannot be phased in gracefully

**Status:** ✅ **CONFIRMED - NO VERSIONING**

---

## Architecture Decisions & Rationale

### ADR-001: Mock JWT (No Signature Verification)

**Decision:** JWT tokens lack cryptographic signatures

**Rationale:** Demo/training environment optimized for simplicity over security

**Consequences:**
- ✅ Easy local testing without key management
- ✅ Tokens human-readable (base64 decode)
- ❌ Not production-ready
- ❌ Tokens can be forged

---

### ADR-002: In-Memory Storage

**Decision:** All services use ephemeral in-memory storage

**Rationale:** Simplifies local development, no database setup required

**Consequences:**
- ✅ Fast startup, no migrations
- ✅ Easy to reset state (restart service)
- ❌ Data lost on restart
- ❌ No persistence layer to test against

---

### ADR-003: Distributed Auth Validation

**Decision:** Each service independently validates tokens (no central auth gateway)

**Rationale:** True microservices pattern, services are self-contained

**Consequences:**
- ✅ No single point of failure
- ✅ Services can run independently
- ✅ Shared auth logic via npm/go packages
- ❌ Token revocation not possible (stateless JWT)
- ❌ Auth logic updates require redeploying all services

---

### ADR-004: Mixed Tech Stack (Go + Node.js)

**Decision:** order-service in Go, others in NestJS/Node.js

**Rationale:** Demonstrate polyglot microservices architecture

**Consequences:**
- ✅ Use best tool per service (Go for performance-critical order processing)
- ✅ Realistic training environment (mimics real-world heterogeneity)
- ❌ Requires maintaining two auth middleware implementations
- ❌ More complex tooling/deployment

---

## Repository Evidence Summary

### Repositories Analyzed

| Repository | Owner | Status | Purpose |
|------------|-------|--------|---------|
| service-infra | bitovi-training | ✅ Cloned | Docker Compose orchestration |
| order-service | bitovi-training | ✅ Cloned | Order management (Go) |
| product-service | bitovi-training | ✅ Cloned | Product catalog (NestJS) |
| user-service | bitovi-training | ✅ Cloned | Authentication provider (NestJS) |
| loyalty-service | bitovi-training | ✅ Cloned | Loyalty points management (NestJS) |
| auth-middleware | bitovi-corp | ✅ Cloned | Node.js auth library |
| auth-middleware-go | bitovi-corp | ✅ Cloned | Go auth library |
| api-tests | bitovi-training | ✅ Cloned | Integration test suite |

**All repos cloned to:** `/Users/nikita/solutions-architect/workdir/repos/`

---

## Appendix: Environment Variable Reference

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
NODE_ENV=development  # Optional, affects token expiry
```

### loyalty-service
```bash
PORT=8300
ORDER_SERVICE_URL=http://order-service:8100
USER_SERVICE_URL=http://user-service:8400
```

---

## Appendix: Seeded Test Users

**Source:** [workdir/repos/user-service/src/user/user.repository.ts:13-48](workdir/repos/user-service/src/user/user.repository.ts#L13-L48)

**All users have password:** `password123`

| Email | Roles | Use Case |
|-------|-------|----------|
| admin@example.com | admin, user | Full access to order/product management |
| user@example.com | user | Basic authenticated access |
| manager@example.com | manager, user | Currently unused role |
| test@example.com | user | Test account |

---

**End of Systems Map**

---

## Generation Metadata

- **Generated:** 2026-02-27
- **Tool:** Copilot with compose-first discovery
- **Source Repositories:** 8 repos (local clones)
- **Subagents Used:** 7 parallel analysis agents
- **Validation Checks:**
  - ✅ Route prefix verification (none found)
  - ✅ Dockerfile FROM lines extracted
  - ✅ Endpoint verification via controller/handler registration
  - ✅ Integration payload verification via client code + DTOs
  - ✅ Auth header forwarding patterns confirmed
