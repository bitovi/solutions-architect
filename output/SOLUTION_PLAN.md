# Solution Plan: Double Loyalty Points for Eligible Products

## 1. Problem Summary

**User Request:** Add a new product field `doubleLoyaltyPointsEligible` that yields double loyalty points when included in an order.

**Current State:**
- Product catalog ([products.service.ts](workdir/repos/product-service/src/products/products.service.ts)) stores basic product attributes (id, name, description, price, availability)
- order-service validates products and triggers loyalty point accrual on order submission
- loyalty-service calculates points based solely on `totalPrice` using payload: `{orderId, userId, totalPrice}` ([loyalty_client.go:23-27](workdir/repos/order-service/internal/services/loyalty_client.go#L23-L27))
- No per-product metadata flows to loyalty calculations

**Problem:** The current integration loses product-level information during loyalty accrual. loyalty-service receives only a total price aggregate, preventing differential point calculation based on product characteristics.

**Business Impact:** Cannot implement promotional mechanics for specific products (e.g., seasonal items, featured products, clearance items earning bonus points).

---

## 2. Impacted Systems

### Primary Changes (3 services)

**product-service (NestJS/TypeScript):**
- Add `doubleLoyaltyPointsEligible` boolean field to product schema
- Update Create Product endpoint validation
- Maintain backward compatibility for existing products (default: false)

**order-service (Go 1.25.5):**
- Enhance loyalty accrual payload to include per-product eligibility flags
- Retrieve `doubleLoyaltyPointsEligible` from product-service responses
- Pass product metadata to loyalty-service during order submission

**loyalty-service (NestJS/TypeScript):**
- Replace aggregate `totalPrice` calculation with per-product point accrual
- Apply 2x multiplier for eligible products
- Update DTO validation to accept new payload structure

### Indirect Impacts

**api-tests (Jest):**
- Add test scenarios for double-points products
- Verify calculation correctness with mixed eligible/non-eligible orders
- Validate backward compatibility for orders without eligibility flags

**No Changes Required:**
- user-service (does not interact with products or loyalty calculations)
- auth-middleware packages (no new auth requirements)
- service-infra (no new services or dependencies)

---

## 3. Proposed Changes by System

### 3.1 product-service

**File:** [src/products/products.service.ts](workdir/repos/product-service/src/products/products.service.ts)

**Schema Update:**
```typescript
interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  availability: boolean;
  doubleLoyaltyPointsEligible: boolean; // NEW FIELD
}
```

**Implementation Changes:**
1. Add field to in-memory storage initialization (seed data)
2. Update `createProduct()` to accept `doubleLoyaltyPointsEligible` (default: `false`)
3. Update `getProductById()` response to include new field

**File:** [src/products/dto/create-product.dto.ts](workdir/repos/product-service/src/products/dto/create-product.dto.ts)

**DTO Validation:**
```typescript
@IsBoolean()
@IsOptional()
doubleLoyaltyPointsEligible?: boolean = false;
```

**Breaking Change Risk:** ⚠️ **LOW** - Adding optional field with default value maintains backward compatibility for existing API consumers.

---

### 3.2 order-service

**File:** [internal/services/loyalty_client.go](workdir/repos/order-service/internal/services/loyalty_client.go)

**Current Payload Structure ([loyalty_client.go:23-27](workdir/repos/order-service/internal/services/loyalty_client.go#L23-L27)):**
```go
type AccrueLoyaltyPointsRequest struct {
    OrderID    string  `json:"orderId"`
    UserID     string  `json:"userId"`
    TotalPrice float64 `json:"totalPrice"`
}
```

**New Payload Structure:**
```go
type AccrueLoyaltyPointsRequest struct {
    OrderID  string                 `json:"orderId"`
    UserID   string                 `json:"userId"`
    Products []ProductEligibilityInfo `json:"products"`
}

type ProductEligibilityInfo struct {
    ProductID                  string  `json:"productId"`
    Quantity                   int     `json:"quantity"`
    Price                      float64 `json:"price"`
    DoubleLoyaltyPointsEligible bool   `json:"doubleLoyaltyPointsEligible"`
}
```

**Implementation Changes:**

1. **Extend ProductClient response model** ([internal/services/product_client.go](workdir/repos/order-service/internal/services/product_client.go)):
   ```go
   type Product struct {
       ID                          int     `json:"id"`
       Name                        string  `json:"name"`
       Description                 string  `json:"description"`
       Price                       float64 `json:"price"`
       Availability                bool    `json:"availability"`
       DoubleLoyaltyPointsEligible bool    `json:"doubleLoyaltyPointsEligible"` // NEW
   }
   ```

2. **Update SubmitOrder handler** ([internal/handlers/orders.go](workdir/repos/order-service/internal/handlers/orders.go)):
   - Build product eligibility array during product validation loop
   - Replace single `totalPrice` calculation with per-product details
   - Pass enriched payload to `loyalty_client.AccrueLoyaltyPoints()`

**Pseudo-code:**
```go
// During order submission (status: PROCESSING)
productInfos := []ProductEligibilityInfo{}
for _, item := range order.Products {
    product, err := productClient.GetProduct(item.ProductID, authToken)
    if err != nil { return err }
    
    productInfos = append(productInfos, ProductEligibilityInfo{
        ProductID:                   item.ProductID,
        Quantity:                    item.Quantity,
        Price:                       product.Price,
        DoubleLoyaltyPointsEligible: product.DoubleLoyaltyPointsEligible,
    })
}

err := loyaltyClient.AccrueLoyaltyPoints(AccrueLoyaltyPointsRequest{
    OrderID:  order.ID,
    UserID:   order.UserID,
    Products: productInfos,
})
```

**Breaking Change Risk:** ⚠️ **HIGH** - Payload structure change is non-backward-compatible. Requires coordinated deployment with loyalty-service.

---

### 3.3 loyalty-service

**File:** [src/loyalty/dto/accrue-points-request.dto.ts](workdir/repos/loyalty-service/src/loyalty/dto/accrue-points-request.dto.ts)

**Current DTO ([accrue-points-request.dto.ts:4-14](workdir/repos/loyalty-service/src/loyalty/dto/accrue-points-request.dto.ts#L4-L14)):**
```typescript
export class AccruePointsRequestDto {
  @IsUUID()
  orderId: string;

  @IsUUID()
  userId: string;

  @IsNumber()
  @Min(0)
  totalPrice: number;
}
```

**New DTO:**
```typescript
export class ProductEligibilityInfoDto {
  @IsString()
  productId: string;

  @IsInt()
  @Min(1)
  quantity: number;

  @IsNumber()
  @Min(0)
  price: number;

  @IsBoolean()
  doubleLoyaltyPointsEligible: boolean;
}

export class AccruePointsRequestDto {
  @IsUUID()
  orderId: string;

  @IsUUID()
  userId: string;

  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => ProductEligibilityInfoDto)
  products: ProductEligibilityInfoDto[];
}
```

**File:** [src/loyalty/loyalty.service.ts](workdir/repos/loyalty-service/src/loyalty/loyalty.service.ts)

**Current Calculation Logic:**
```typescript
// Simplified - assumes 1 point per $1
const points = Math.floor(totalPrice);
```

**New Calculation Logic:**
```typescript
async accruePoints(dto: AccruePointsRequestDto): Promise<AccruePointsResponseDto> {
  // Validate user exists
  await this.userClient.validateUser(dto.userId);

  let totalPoints = 0;

  // Calculate points per product
  for (const product of dto.products) {
    const productPrice = product.price * product.quantity;
    let productPoints = Math.floor(productPrice); // Base: 1 point per $1

    if (product.doubleLoyaltyPointsEligible) {
      productPoints *= 2; // Apply 2x multiplier
    }

    totalPoints += productPoints;
  }

  // Store points (existing balance update logic)
  const balance = this.balances.get(dto.userId) || { userId: dto.userId, points: 0 };
  balance.points += totalPoints;
  this.balances.set(dto.userId, balance);

  // Record transaction
  this.transactions.set(dto.orderId, {
    orderId: dto.orderId,
    userId: dto.userId,
    points: totalPoints,
  });

  return {
    orderId: dto.orderId,
    userId: dto.userId,
    points: totalPoints,
  };
}
```

**Breaking Change Risk:** ⚠️ **HIGH** - Endpoint contract change requires caller (order-service) to use new payload structure.

---

## 4. Contract & Schema Changes

### REST API Changes

**product-service:**

**Affected Endpoint:** `GET /products/:id`

**Before:**
```json
{
  "id": 1,
  "name": "Laptop",
  "description": "High-performance laptop",
  "price": 999.99,
  "availability": true
}
```

**After:**
```json
{
  "id": 1,
  "name": "Laptop",
  "description": "High-performance laptop",
  "price": 999.99,
  "availability": true,
  "doubleLoyaltyPointsEligible": false
}
```

**Backward Compatibility:** ✅ **SAFE** - Additional field does not break existing consumers (additive change).

---

**loyalty-service:**

**Affected Endpoint:** `POST /loyalty/orders`

**Request Before ([accrue-points-request.dto.ts:4-14](workdir/repos/loyalty-service/src/loyalty/dto/accrue-points-request.dto.ts#L4-L14)):**
```json
{
  "orderId": "550e8400-e29b-41d4-a716-446655440000",
  "userId": "123e4567-e89b-12d3-a456-426614174000",
  "totalPrice": 1499.99
}
```

**Request After:**
```json
{
  "orderId": "550e8400-e29b-41d4-a716-446655440000",
  "userId": "123e4567-e89b-12d3-a456-426614174000",
  "products": [
    {
      "productId": "1",
      "quantity": 1,
      "price": 999.99,
      "doubleLoyaltyPointsEligible": true
    },
    {
      "productId": "2",
      "quantity": 2,
      "price": 250.00,
      "doubleLoyaltyPointsEligible": false
    }
  ]
}
```

**Response:** ✅ **UNCHANGED** - `{orderId, userId, points}` structure remains stable.

**Backward Compatibility:** ❌ **BREAKING** - Payload structure incompatible with old clients.

---

### Database Schema Changes

**N/A** - All services use in-memory storage ([Issue 3](workdir/repos/loyalty-service/src/loyalty/loyalty.service.ts)). For production database deployments:

**product-service (hypothetical):**
```sql
ALTER TABLE products 
ADD COLUMN double_loyalty_points_eligible BOOLEAN DEFAULT FALSE NOT NULL;
```

---

## 5. Data Flow Updates

### Current Flow: Order Submission → Loyalty Accrual

```
[User submits order]
         ↓
[order-service POST /orders/:id/submit]
         ↓
[Validate products via GET /products/:id] ──→ product-service
         ↓
[Calculate totalPrice = Σ(price × quantity)]
         ↓
[Send {orderId, userId, totalPrice}] ──→ loyalty-service POST /loyalty/orders
         ↓
[loyalty-service: points = floor(totalPrice)]
         ↓
[Store balance update]
```

### Updated Flow: Product Metadata Forwarding

```
[User submits order]
         ↓
[order-service POST /orders/:id/submit]
         ↓
[Validate products via GET /products/:id] ──→ product-service
│   Response includes: {id, price, doubleLoyaltyPointsEligible}
         ↓
[Build product eligibility array]
│   ProductEligibilityInfo[] = [{productId, quantity, price, doubleLoyaltyPointsEligible}]
         ↓
[Send {orderId, userId, products[]}] ──→ loyalty-service POST /loyalty/orders
         ↓
[loyalty-service: Per-product calculation]
│   For each product:
│       basePoints = floor(price × quantity)
│       finalPoints = doubleLoyaltyPointsEligible ? basePoints × 2 : basePoints
│   totalPoints = Σ(finalPoints)
         ↓
[Store balance update]
```

**Key Changes:**
1. product-service responses enriched with eligibility flag
2. order-service aggregates per-product metadata (no longer sends single totalPrice)
3. loyalty-service iterates over products array for point calculation
4. Granular visibility into which products contribute to point totals

---

## 6. Security & Compliance Considerations

### Authentication & Authorization

**No Changes Required:**
- product-service `GET /products/:id` already enforces `AuthGuard` ([products.controller.ts:38](workdir/repos/product-service/src/products/products.controller.ts#L38))
- product-service `POST /products` requires `admin` role ([products.controller.ts:62](workdir/repos/product-service/src/products/products.controller.ts#L62))
- loyalty-service `POST /loyalty/orders` enforces `AuthGuard` ([loyalty.controller.ts:73](workdir/repos/loyalty-service/src/loyalty/loyalty.controller.ts#L73))
- order-service forwards auth tokens to downstream services ([loyalty_client.go:68-70](workdir/repos/order-service/internal/services/loyalty_client.go#L68-L70))

**RBAC Impact:**
- Creating products with `doubleLoyaltyPointsEligible=true` inherits existing `admin`-only restriction
- No privilege escalation vectors introduced

### Input Validation

**New Validation Points:**

1. **product-service DTO:**
   ```typescript
   @IsBoolean()
   @IsOptional()
   doubleLoyaltyPointsEligible?: boolean = false;
   ```
   **Risk:** Malformed boolean values (e.g., strings, nulls) rejected by class-validator

2. **loyalty-service DTO:**
   ```typescript
   @IsArray()
   @ValidateNested({ each: true })
   products: ProductEligibilityInfoDto[];
   ```
   **Risk:** Empty arrays, missing fields, negative prices/quantities rejected by validation pipeline

**Injection Risks:** ❌ **NONE** - Boolean flag does not introduce SQL/NoSQL injection vectors (in-memory storage only).

### Data Integrity

**Consistency Concerns:**
1. **Stale Product Data:** order-service fetches product details at submission time. If a product's eligibility flag changes between order creation and submission, points may not reflect current state.
   - **Mitigation:** Document that eligibility applies at order submission time (point-in-time snapshot).

2. **Product Deletion:** If a product is deleted after order creation but before submission, validation fails gracefully (existing error handling in [product_client.go:45-73](workdir/repos/order-service/internal/services/product_client.go#L45-L73)).

### Compliance Notes

**PII Impact:** ❌ **NONE** - `doubleLoyaltyPointsEligible` is product metadata, not user data.

**Audit Logging:** ⚠️ **RECOMMENDATION** - Log eligibility flag values in loyalty accrual transactions for audit trails (e.g., "Product X earned 200 points via 2x multiplier").

---

## 7. Testing Strategy

### 7.1 Unit Tests

**product-service:**
- ✅ Create product with `doubleLoyaltyPointsEligible=true`
- ✅ Create product with `doubleLoyaltyPointsEligible=false` (explicit)
- ✅ Create product without field (default: false)
- ✅ Retrieve product and verify field presence
- ❌ Invalid boolean values (e.g., `"yes"`, `null`, `1`)

**order-service:**
- ✅ Build product eligibility array from multi-product order
- ✅ Handle products with mixed eligibility flags
- ✅ Verify payload serialization to loyalty-service
- ✅ Handle product-service response with missing field (backward compat)

**loyalty-service:**
- ✅ Calculate points for single eligible product (2x multiplier)
- ✅ Calculate points for single non-eligible product (1x multiplier)
- ✅ Calculate points for mixed order (eligible + non-eligible)
- ✅ Reject empty products array
- ✅ Reject negative prices/quantities
- ✅ Verify balance updates correctly with 2x points

### 7.2 Integration Tests (api-tests)

**New Test Scenarios:**

1. **Scenario: Double Points Product Purchase**
   ```
   GIVEN admin creates product with doubleLoyaltyPointsEligible=true, price=100
   WHEN user submits order for 1x product (totalPrice=100)
   THEN loyalty balance increases by 200 points (2x multiplier)
   ```

2. **Scenario: Mixed Eligibility Order**
   ```
   GIVEN product A (eligible=true, price=100)
   AND product B (eligible=false, price=50)
   WHEN user orders 1x A + 2x B (totalPrice=200)
   THEN loyalty balance increases by 300 points (200 + 100)
   ```

3. **Scenario: Non-Eligible Product**
   ```
   GIVEN product with doubleLoyaltyPointsEligible=false, price=150
   WHEN user submits order
   THEN loyalty balance increases by 150 points (1x multiplier)
   ```

4. **Scenario: Backward Compatibility**
   ```
   GIVEN product created before feature deployment (no field)
   WHEN user submits order
   THEN loyalty balance increases by standard calculation (1x)
   ```

**Test Files to Create:**
- `api-tests/src/double-loyalty-points.test.ts`

**Existing Tests to Update:**
- `api-tests/src/order-service.test.ts` - Update loyalty accrual assertions to account for per-product calculations
- `api-tests/src/loyalty-service.test.ts` - Update payload fixtures to use new `products[]` structure

### 7.3 Regression Tests

**Critical Paths:**
- ✅ Order submission without loyalty accrual (cancelled orders)
- ✅ Redemption flow unaffected by point calculation changes
- ✅ GET /loyalty/:userId/balance returns correct totals
- ✅ Multi-product orders with quantities > 1
- ✅ Orders with unavailable products (error handling unchanged)

### 7.4 Performance Tests

**Load Considerations:**
- **Payload Size:** New `products[]` array increases payload by ~80 bytes per product (vs. single totalPrice float)
- **Calculation Complexity:** O(n) per-product iteration in loyalty-service (negligible for typical order sizes < 50 items)

**Benchmark Targets:**
- Loyalty accrual endpoint latency < 200ms for orders with 10 products
- No memory leaks in in-memory storage with 10,000+ transactions

---

## 8. Rollout Plan

### Deployment Sequence

**CRITICAL:** loyalty-service must deploy BEFORE order-service to avoid runtime errors when old order-service sends new payload format to unupgraded loyalty-service.

**Phase 1: Foundation (product-service)**
- Deploy product-service with schema update
- Validate GET /products/:id returns new field (default: false)
- Verify backward compatibility with existing consumers
- **Risk:** ⚠️ **LOW** - Additive change, safe to deploy independently

**Phase 2: Consumer (loyalty-service)**
- Deploy loyalty-service with new DTO and calculation logic
- **Critical:** Endpoint must accept ONLY new payload format (breaking change)
- Test via direct API calls with sample payloads
- **Risk:** ⚠️ **HIGH** - Breaks existing order-service integration

**Phase 3: Orchestrator (order-service)**
- Deploy order-service with enhanced loyalty client
- Verify product metadata forwarding to loyalty-service
- Monitor loyalty accrual success rates
- **Risk:** ⚠️ **HIGH** - Dependent on Phase 2 completion

**Phase 4: Validation (api-tests)**
- Run full integration test suite
- Execute new double-points test scenarios
- Validate E2E flow correctness
- **Risk:** ❌ **NONE** - Test infrastructure only

### Rollback Strategy

**Scenario 1: loyalty-service Deployment Fails**
- Rollback loyalty-service to previous version
- order-service remains on old version (no deployment attempted)
- **Impact:** ❌ No user-facing impact

**Scenario 2: order-service Deployment Fails**
- Rollback order-service to previous version
- loyalty-service stays on new version (compatible only with new payload)
- **Impact:** ⚠️ **CRITICAL** - Loyalty accrual will fail with 400 errors
- **Mitigation:** Deploy hotfix to loyalty-service with dual payload support (accept old OR new format)

**Scenario 3: Runtime Errors Detected Post-Deployment**
- Emergency rollback order-service to previous version
- Monitor loyalty-service for orphaned transactions
- **Recovery:** Re-process failed orders via admin script (manual points adjustment)

### Monitoring & Alerts

**Metrics to Track:**
1. Loyalty accrual endpoint error rate (target: < 1%)
2. Average points per order (expect increase due to 2x multiplier)
3. Payload size distribution (monitor for anomalies > 10KB)
4. product-service response times for GET /products/:id (baseline: < 50ms)

**Alerts:**
- ⚠️ loyalty-service returns 400 errors (payload validation failure)
- ⚠️ order-service loyalty client returns 5xx errors (service unavailable)
- ⚠️ Points calculation anomalies (e.g., negative balances, overflows)

---

## 9. Risks & Unknowns

### High-Priority Risks

**Risk 1: Breaking Change Window**
- **Probability:** High (architectural constraint)
- **Impact:** Critical (loyalty accrual downtime during deployment)
- **Description:** The payload structure change creates a brief window where order-service (new version) may send requests to loyalty-service (old version), causing 400 validation errors.
- **Mitigation:**
  1. Deploy loyalty-service first during low-traffic window (3-5am)
  2. Implement health checks to verify loyalty endpoint accepts new payload before deploying order-service
  3. Use feature flag to delay order-service payload switch until validation passes

**Risk 2: Product Data Staleness**
- **Probability:** Medium
- **Impact:** Low (point calculation slightly inaccurate)
- **Description:** Product eligibility flag may change between order creation and submission, causing points to reflect outdated state.
- **Mitigation:**
  1. Document behavior: "Eligibility applies at order submission time"
  2. Consider caching product eligibility flags in order payload during creation (future enhancement)

**Risk 3: Payload Size Growth**
- **Probability:** Low (requires orders with >100 products)
- **Impact:** Medium (network latency increase)
- **Description:** Large orders with many products increase payload size significantly (80 bytes per product).
- **Mitigation:**
  1. Monitor P95 payload sizes post-deployment
  2. Implement pagination for orders exceeding 50 products (future)

### Medium-Priority Risks

**Risk 4: Inconsistent Point Calculation**
- **Probability:** Low (covered by tests)
- **Impact:** Medium (user trust erosion)
- **Description:** Logic errors in per-product iteration could cause incorrect point totals.
- **Mitigation:**
  1. Comprehensive unit tests with edge cases (zero-price products, high quantities)
  2. Add audit logging to compare calculated points vs. expected values
  3. Implement admin dashboard to review accrual history

**Risk 5: Backward Compatibility Gaps**
- **Probability:** Low
- **Impact:** Medium (existing integrations break)
- **Description:** External systems consuming product-service API may not expect new field.
- **Mitigation:**
  1. Verify no external consumers beyond order-service (confirmed via SYSTEMS_MAP)
  2. Document API change in release notes

### Unknowns

**Unknown 1: Business Rules for Eligibility**
- ❓ Can a product's eligibility flag change after orders are placed?
- ❓ Should eligibility expire after a promotion period?
- ❓ Are there limits on the number of eligible products per order?
- **Resolution:** Clarify with product/business team before Phase 1 deployment

**Unknown 2: Fractional Points Handling**
- ❓ Current logic uses `Math.floor(price)` - should double-eligible products round differently?
- ❓ Example: $99.99 → 99 points or 100 points after 2x multiplier?
- **Resolution:** Confirm rounding strategy: `floor(price * 2)` vs. `floor(price) * 2`

**Unknown 3: Retroactive Application**
- ❓ Should existing orders be reprocessed with new calculation rules?
- ❓ How to handle orders with unavailable products (no eligibility data available)?
- **Resolution:** Decide on data migration strategy for historical orders

---

## 10. Pull Request Slicing

### PR Sequence (4 PRs across 3 repositories)

#### PR #1: product-service Schema Update
**Repository:** `bitovi-training/product-service`  
**Branch:** `feature/double-loyalty-points-schema`

**Changes:**
- Add `doubleLoyaltyPointsEligible: boolean` to Product interface
- Update `CreateProductDto` with `@IsBoolean() @IsOptional()` validation
- Add field to in-memory storage seed data (set to `false` for all existing products)
- Update unit tests to verify field presence

**Files Modified:**
1. `src/products/products.service.ts` - Add field to Product type
2. `src/products/dto/create-product.dto.ts` - Add DTO validation
3. `src/products/products.controller.ts` - No changes (auto-serializes new field)
4. `test/products.service.spec.ts` - Add tests for new field

**Acceptance Criteria:**
- ✅ GET /products/:id returns `doubleLoyaltyPointsEligible: false` for existing products
- ✅ POST /products accepts optional field with default value
- ✅ All existing tests pass

**Dependencies:** None (standalone change)

**Deployment:** Safe to deploy independently

---

#### PR #2: loyalty-service Calculation Logic
**Repository:** `bitovi-training/loyalty-service`  
**Branch:** `feature/double-loyalty-points-calculation`

**Changes:**
- Replace `totalPrice` with `products[]` array in `AccruePointsRequestDto`
- Create `ProductEligibilityInfoDto` class with validation
- Update `accruePoints()` to iterate over products and apply 2x multiplier
- Update response handling (unchanged structure)

**Files Modified:**
1. `src/loyalty/dto/accrue-points-request.dto.ts` - Replace DTO structure
2. `src/loyalty/loyalty.service.ts` - Update calculation logic
3. `test/loyalty.service.spec.ts` - Add unit tests for per-product calculations

**Acceptance Criteria:**
- ✅ Endpoint accepts new payload format: `{orderId, userId, products[]}`
- ✅ Endpoint rejects old payload format: `{orderId, userId, totalPrice}`
- ✅ Calculation applies 2x multiplier for eligible products
- ✅ Mixed orders calculate correctly (e.g., 100 eligible + 50 non-eligible = 250 points)

**Dependencies:** None (accepts any caller with new payload format)

**Deployment:** ⚠️ **BREAKING** - Blocks order-service until deployed

---

#### PR #3: order-service Integration Update
**Repository:** `bitovi-training/order-service`  
**Branch:** `feature/double-loyalty-points-integration`

**Changes:**
- Extend `Product` struct in `product_client.go` with `DoubleLoyaltyPointsEligible`
- Replace `AccrueLoyaltyPointsRequest` with product array structure
- Update `SubmitOrder` handler to build product eligibility metadata
- Remove `totalPrice` calculation from loyalty client

**Files Modified:**
1. `internal/services/product_client.go` - Add field to Product struct
2. `internal/services/loyalty_client.go` - Update request payload
3. `internal/handlers/orders.go` - Build product array during submission
4. `internal/models/order.go` - No changes (internal storage unchanged)

**Acceptance Criteria:**
- ✅ Order submission fetches product eligibility from product-service
- ✅ Loyalty accrual payload includes per-product metadata
- ✅ Token forwarding to loyalty-service remains functional
- ✅ Error handling unchanged (product validation failures)

**Dependencies:** 
- ⚠️ **REQUIRES PR #2** (loyalty-service must accept new payload format)
- ✅ **OPTIONAL PR #1** (product-service field is backward-compatible)

**Deployment:** Deploy AFTER loyalty-service (PR #2)

---

#### PR #4: Integration Test Coverage
**Repository:** `bitovi-training/api-tests`  
**Branch:** `feature/double-loyalty-points-tests`

**Changes:**
- Add `double-loyalty-points.test.ts` with 4 scenarios (see Section 7.2)
- Update existing fixtures to include new field
- Update assertions in `loyalty-service.test.ts` to validate per-product calculations

**Files Modified:**
1. `src/double-loyalty-points.test.ts` - New test suite
2. `src/fixtures/products.fixture.ts` - Add eligible/non-eligible products
3. `src/loyalty-service.test.ts` - Update payload assertions

**Acceptance Criteria:**
- ✅ All new test scenarios pass
- ✅ Existing integration tests pass without modifications
- ✅ Coverage includes edge cases (empty orders, zero-price products)

**Dependencies:** 
- ⚠️ **REQUIRES PR #1, #2, #3** (all services must be upgraded)

**Deployment:** Test infrastructure only (no production deployment)

---

### Dependency Graph

```
PR #1 (product-service)
   ├─────────────────────┐
   ▼                     ▼
PR #2 (loyalty-service)  │
   │                     │
   └──────┬──────────────┘
          ▼
PR #3 (order-service)
          │
          ▼
PR #4 (api-tests)
```

**Deployment Order:**
1. Deploy PR #1 (product-service) - ✅ Safe anytime
2. Deploy PR #2 (loyalty-service) - ⚠️ During low-traffic window
3. Wait 5 minutes, verify loyalty endpoint health
4. Deploy PR #3 (order-service) - ⚠️ Monitor error rates
5. Run PR #4 (api-tests) - Validate E2E flow

---

## Summary

**Complexity:** Medium (3 services, 1 breaking change)  
**Deployment Risk:** High (requires coordinated rollout)  
**Estimated Effort:** 5-8 engineering days (2 backend, 2 testing, 1 deployment)  
**Business Value:** Enables targeted promotional mechanics for product catalog

**Key Success Factors:**
1. Deploy loyalty-service before order-service (avoid 400 errors)
2. Comprehensive integration tests to catch calculation errors
3. Monitor payload sizes and error rates post-deployment
4. Clarify business rules for eligibility flag management

**Go/No-Go Criteria:**
- ✅ All unit tests pass for 3 modified services
- ✅ Integration tests validate double-points calculation
- ✅ loyalty-service health check returns 200 after Phase 2 deployment
- ✅ Rollback plan tested in staging environment

---

**End of Solution Plan**
