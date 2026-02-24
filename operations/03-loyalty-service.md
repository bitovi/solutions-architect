# Implementation Plan: loyalty-service — Support Double Loyalty Points Multiplier

**Date**: 2026-02-24
**Repo**: `bitovi-training/loyalty-service`
**Step**: 3 (can be deployed independently; fully functional once order-service from Step 2 sends `doubleLoyaltyPointsTotal`)

---

## 1. Problem Summary

The loyalty-service must support a **double loyalty points multiplier** for products flagged with `doubleLoyaltyPoints: true` in the product-service. Currently, the accrual endpoint (`POST /loyalty/orders`) calculates points as:

```
points = Math.floor(totalPrice / 10)
```

With this change, the order-service will send an additional `doubleLoyaltyPointsTotal` field representing the subtotal of order items that qualify for double loyalty points. The new calculation will be:

```
regularSubtotal = totalPrice - doubleLoyaltyPointsTotal
regularPoints = Math.floor(regularSubtotal / 10)
doublePoints = Math.floor(doubleLoyaltyPointsTotal / 10) * 2
totalPoints = regularPoints + doublePoints
```

---

## 2. Assumptions & Constraints

- **Technology**: NestJS 11.x, TypeScript 5.7, class-validator, class-transformer, in-memory storage.
- **No database**: Uses `Map<string, Order[]>` and `Map<string, Redemption[]>` in-memory repositories.
- **Backward-compatible**: The `doubleLoyaltyPointsTotal` field is **optional** (defaults to `0`). If the order-service hasn't been updated yet (Step 2), requests will arrive without this field and points will be calculated at the normal 1x rate — identical to current behavior.
- **Validation**: Global `ValidationPipe` with `whitelist: true` and `forbidNonWhitelisted: true` is active. The DTO must explicitly declare the new field, otherwise it will be **stripped** from the request and the feature won't work even when the order-service sends it.
- **Points formula**: `$1 = 10 points` formula is `Math.floor(totalPrice / 10)`. The double multiplier applies a 2x factor to the double-loyalty portion only.
- **Auth**: The `POST /loyalty/orders` endpoint uses `AuthGuard` from `@bitovi-corp/auth-middleware`.

---

## 3. Related Systems/Repos That Are Affected

| Repo | Impact | Dependency Direction |
|---|---|---|
| **product-service** (Step 1) | Source of truth for `doubleLoyaltyPoints` flag on products. No direct integration with loyalty-service. | Indirect upstream (via order-service) |
| **order-service** (Step 2) | Reads `doubleLoyaltyPoints` from product-service, calculates `doubleLoyaltyPointsTotal`, and sends it to loyalty-service via `POST /loyalty/orders`. | Direct upstream caller |

**Deployment independence**: This step can be deployed before Step 2. If deployed first, the new `doubleLoyaltyPointsTotal` field simply won't be present in incoming requests, so it defaults to `0` and points are calculated at the normal rate. Once Step 2 is deployed, the field starts flowing through and double points are applied.

---

## 4. Contract & Schema Changes

### 4.1 Accrual Request DTO — Add `doubleLoyaltyPointsTotal`

**File**: `src/loyalty/dto/accrue-points-request.dto.ts`

**Current**:
```typescript
import { IsNotEmpty, IsNumber, IsUUID, Min } from "class-validator";

export class AccruePointsRequestDto {
  @IsUUID()
  @IsNotEmpty()
  orderId!: string;

  @IsUUID()
  @IsNotEmpty()
  userId!: string;

  @IsNumber()
  @Min(0)
  totalPrice!: number;
}
```

**Proposed**:
```typescript
import { IsNotEmpty, IsNumber, IsOptional, IsUUID, Min } from "class-validator";

export class AccruePointsRequestDto {
  @IsUUID()
  @IsNotEmpty()
  orderId!: string;

  @IsUUID()
  @IsNotEmpty()
  userId!: string;

  @IsNumber()
  @Min(0)
  totalPrice!: number;

  @IsOptional()
  @IsNumber()
  @Min(0)
  doubleLoyaltyPointsTotal?: number;
}
```

### 4.2 Accrual Response — No change

The response `{ orderId, userId, points }` remains the same. The `points` value will simply be higher when double-loyalty products are present.

### 4.3 Balance & Redemption Endpoints — No change

These endpoints read `accruedLoyaltyPoints` from the order-service (via `OrderClient.getOrdersByUserId`). The doubled points are already baked into the `accruedLoyaltyPoints` value stored on the order. No changes needed.

---

## 5. Data Flow Updates

### Before
```
Order Service  ──>  POST /loyalty/orders
                    { orderId, userId, totalPrice }
                    
                    points = floor(totalPrice / 10)
                    
                    Response: { orderId, userId, points }
```

### After
```
Order Service  ──>  POST /loyalty/orders
                    { orderId, userId, totalPrice, doubleLoyaltyPointsTotal? }
                    
                    regularSubtotal = totalPrice - (doubleLoyaltyPointsTotal ?? 0)
                    regularPoints = floor(regularSubtotal / 10)
                    doublePoints = floor((doubleLoyaltyPointsTotal ?? 0) / 10) * 2
                    points = regularPoints + doublePoints
                    
                    Response: { orderId, userId, points }
```

### Example Calculation

Order with:
- Laptop Pro ($1299.99, `doubleLoyaltyPoints: true`)
- Wireless Mouse x2 ($29.99 each, `doubleLoyaltyPoints: false`)

```
totalPrice = 1299.99 + (29.99 × 2) = 1359.97
doubleLoyaltyPointsTotal = 1299.99

regularSubtotal = 1359.97 - 1299.99 = 59.98
regularPoints = floor(59.98 / 10) = 5
doublePoints = floor(1299.99 / 10) * 2 = 129 * 2 = 258
totalPoints = 5 + 258 = 263
```

Without the feature (current behavior): `floor(1359.97 / 10) = 135 points`. With the feature: `263 points` — the double-loyalty product portion earns 2x.

---

## 6. Proposed Changes for the Repo

### 6.1 `src/loyalty/dto/accrue-points-request.dto.ts` — Add optional field

```typescript
import { IsNotEmpty, IsNumber, IsOptional, IsUUID, Min } from "class-validator";

export class AccruePointsRequestDto {
  @IsUUID()
  @IsNotEmpty()
  orderId!: string;

  @IsUUID()
  @IsNotEmpty()
  userId!: string;

  @IsNumber()
  @Min(0)
  totalPrice!: number;

  @IsOptional()
  @IsNumber()
  @Min(0)
  doubleLoyaltyPointsTotal?: number;
}
```

**Key**: The `@IsOptional()` decorator is critical. Without it, requests from the current order-service (before Step 2 is deployed) would fail validation.

### 6.2 `src/loyalty/loyalty.service.ts` — Update `accruePoints` method

**Update the method signature** to accept the new parameter:

```typescript
async accruePoints(
  orderId: string,
  userId: string,
  totalPrice: number,
  doubleLoyaltyPointsTotal: number = 0,
  authToken?: string,
): Promise<{ orderId: string; userId: string; points: number }>
```

**Update the points calculation** (replace the single line `const points = Math.floor(totalPrice / 10);`):

```typescript
// Calculate points with double loyalty multiplier
const doubleLoyaltyTotal = doubleLoyaltyPointsTotal ?? 0;
const regularSubtotal = totalPrice - doubleLoyaltyTotal;
const regularPoints = Math.floor(regularSubtotal / 10);
const doublePoints = Math.floor(doubleLoyaltyTotal / 10) * 2;
const points = regularPoints + doublePoints;
```

**Full updated method**:

```typescript
async accruePoints(
  orderId: string,
  userId: string,
  totalPrice: number,
  doubleLoyaltyPointsTotal: number = 0,
  authToken?: string,
): Promise<{ orderId: string; userId: string; points: number }> {
  if (!orderId) {
    throw new BadRequestException("Order ID is required");
  }

  if (!userId) {
    throw new BadRequestException("User ID is required");
  }

  const userExists = await this.userClient.validateUser(userId);
  if (!userExists) {
    throw new NotFoundException(`User ${userId} not found`);
  }

  try {
    await this.orderClient.getOrderById(orderId, authToken);
  } catch (error) {
    if (error instanceof UnauthorizedException) {
      throw error;
    }
    if (error instanceof ForbiddenException) {
      throw error;
    }
    if (error instanceof NotFoundException) {
      throw new NotFoundException(`Order ${orderId} not found`);
    }
    if (error instanceof BadRequestException) {
      throw error;
    }
    throw new BadRequestException("Invalid order ID");
  }

  if (totalPrice < 0) {
    throw new BadRequestException("Total price must be non-negative");
  }

  // Calculate points with double loyalty multiplier
  const doubleLoyaltyTotal = doubleLoyaltyPointsTotal ?? 0;
  const regularSubtotal = totalPrice - doubleLoyaltyTotal;
  const regularPoints = Math.floor(regularSubtotal / 10);
  const doublePoints = Math.floor(doubleLoyaltyTotal / 10) * 2;
  const points = regularPoints + doublePoints;

  this.orderRepository.save({
    orderId,
    userId,
    points,
    status: "active",
  });

  return { orderId, userId, points };
}
```

### 6.3 `src/loyalty/loyalty.controller.ts` — Pass the new field through

Update the `accrueOrderPoints` method to pass `doubleLoyaltyPointsTotal`:

```typescript
@Post("/orders")
@HttpCode(201)
@UseGuards(AuthGuard)
async accrueOrderPoints(
  @Body() body: AccruePointsRequestDto,
  @Headers("authorization") authorization?: string,
): Promise<{ orderId: string; userId: string; points: number }> {
  const authToken = this.extractToken(authorization);
  return this.loyaltyService.accruePoints(
    body.orderId,
    body.userId,
    body.totalPrice,
    body.doubleLoyaltyPointsTotal ?? 0,
    authToken,
  );
}
```

### 6.4 `src/loyalty/loyalty.service.spec.ts` — Add accrual tests

Add a new `describe` block for accrual with double loyalty points:

```typescript
describe("LoyaltyService - Accrual with Double Loyalty Points", () => {
  let service: LoyaltyService;
  let orderClient: jest.Mocked<OrderClient>;
  let userClient: jest.Mocked<UserClient>;
  let orderRepository: OrderRepository;

  beforeEach(async () => {
    const mockOrderClient = {
      getOrdersByUserId: jest.fn(),
      getOrderById: jest.fn(),
    };
    const mockUserClient = {
      validateUser: jest.fn(),
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        LoyaltyService,
        { provide: OrderClient, useValue: mockOrderClient },
        { provide: UserClient, useValue: mockUserClient },
        OrderRepository,
        RedemptionRepository,
      ],
    }).compile();

    service = module.get<LoyaltyService>(LoyaltyService);
    orderClient = module.get(OrderClient);
    userClient = module.get(UserClient);
    orderRepository = module.get<OrderRepository>(OrderRepository);

    userClient.validateUser.mockResolvedValue(true);
    orderClient.getOrderById.mockResolvedValue({
      id: "test-order-id",
      userId: "alice",
      products: [],
      totalPrice: 100,
      orderDate: "2026-01-01",
      status: "PROCESSING",
      accruedLoyaltyPoints: 0,
    });
  });

  it("should calculate normal points when doubleLoyaltyPointsTotal is 0", async () => {
    const result = await service.accruePoints(
      "test-order-id",
      "alice",
      100,
      0,
    );
    // floor(100 / 10) = 10
    expect(result.points).toBe(10);
  });

  it("should calculate normal points when doubleLoyaltyPointsTotal is omitted", async () => {
    const result = await service.accruePoints(
      "test-order-id",
      "alice",
      100,
    );
    // floor(100 / 10) = 10
    expect(result.points).toBe(10);
  });

  it("should apply double points for the doubleLoyaltyPointsTotal portion", async () => {
    // totalPrice = 100, doubleLoyaltyPointsTotal = 60
    // regularSubtotal = 100 - 60 = 40, regularPoints = floor(40/10) = 4
    // doublePoints = floor(60/10) * 2 = 12
    // total = 4 + 12 = 16
    const result = await service.accruePoints(
      "test-order-id",
      "alice",
      100,
      60,
    );
    expect(result.points).toBe(16);
  });

  it("should handle all products being double loyalty", async () => {
    // totalPrice = 200, doubleLoyaltyPointsTotal = 200
    // regularSubtotal = 0, regularPoints = 0
    // doublePoints = floor(200/10) * 2 = 40
    // total = 40
    const result = await service.accruePoints(
      "test-order-id",
      "alice",
      200,
      200,
    );
    expect(result.points).toBe(40);
  });

  it("should handle fractional amounts correctly", async () => {
    // totalPrice = 1359.97, doubleLoyaltyPointsTotal = 1299.99
    // regularSubtotal = 59.98, regularPoints = floor(59.98/10) = 5
    // doublePoints = floor(1299.99/10) * 2 = 129 * 2 = 258
    // total = 263
    const result = await service.accruePoints(
      "test-order-id",
      "alice",
      1359.97,
      1299.99,
    );
    expect(result.points).toBe(263);
  });

  it("should store the accrued points in the order repository", async () => {
    await service.accruePoints(
      "test-order-id",
      "alice",
      100,
      60,
    );
    const orders = orderRepository.findByUserId("alice");
    expect(orders).toHaveLength(1);
    expect(orders[0].points).toBe(16);
    expect(orders[0].status).toBe("active");
  });
});
```

### 6.5 `test/e2e/loyalty.e2e-spec.ts` — Add E2E accrual test

Add a new `describe` block for the accrual endpoint with double loyalty points. Note: the E2E test depends on the mock `OrderClient` and `UserClient` behavior. If the app uses stub data for users and orders, the test might need to create orders first or use known test data.

```typescript
describe("POST /loyalty/orders (accrual with double loyalty)", () => {
  it("should accrue double points for doubleLoyaltyPointsTotal portion", () => {
    return request(app.getHttpServer())
      .post("/loyalty/orders")
      .send({
        orderId: "test-order-uuid",
        userId: "alice",
        totalPrice: 100,
        doubleLoyaltyPointsTotal: 60,
      })
      .expect(201)
      .expect((res) => {
        expect(res.body.orderId).toBe("test-order-uuid");
        expect(res.body.userId).toBe("alice");
        // regularPoints = floor(40/10) = 4, doublePoints = floor(60/10)*2 = 12
        expect(res.body.points).toBe(16);
      });
  });

  it("should calculate normal points when doubleLoyaltyPointsTotal is absent", () => {
    return request(app.getHttpServer())
      .post("/loyalty/orders")
      .send({
        orderId: "test-order-uuid-2",
        userId: "alice",
        totalPrice: 100,
      })
      .expect(201)
      .expect((res) => {
        expect(res.body.points).toBe(10);
      });
  });
});
```

**Note**: These E2E tests may need adjustment depending on the actual stub data and order/user validation behavior. The test UUIDs must be valid and the order-client mock must recognise them.

---

## 7. Security & Compliance Considerations

- **Input validation**: `doubleLoyaltyPointsTotal` is validated as `@IsNumber()` and `@Min(0)`. Negative values are rejected. The value cannot exceed `totalPrice` logically (but no explicit validation for this — the calculation simply handles it mathematically). Consider adding validation: `doubleLoyaltyPointsTotal <= totalPrice`.
- **No auth changes**: The endpoint already requires `AuthGuard`. No new auth requirements.
- **Server-side calculation**: The points multiplier is applied server-side. Clients cannot directly request double points — the `doubleLoyaltyPointsTotal` is calculated by the order-service based on trusted product-service data.
- **Audit trail**: The `Order` entity stored in the loyalty-service repository records the total `points` earned. It does not separately track the regular vs. double portions. This is acceptable for the current in-memory implementation but should be considered if a persistent store is added later.

---

## 8. Risks, Unknowns, and Open Questions

| Item | Type | Detail |
|---|---|---|
| `doubleLoyaltyPointsTotal` > `totalPrice` | Edge Case | If `doubleLoyaltyPointsTotal` exceeds `totalPrice` (e.g., due to a bug in order-service), `regularSubtotal` becomes negative, producing negative `regularPoints`. Consider adding validation: `if (doubleLoyaltyPointsTotal > totalPrice) throw BadRequestException`. |
| Whitelist stripping | Risk | The global `ValidationPipe` with `whitelist: true` will **strip** the `doubleLoyaltyPointsTotal` field if it's not declared in the DTO. This is why the DTO update is critical — without it, the field is silently dropped and double points never apply. |
| Existing accrual tests | Note | There are **no existing unit tests** for the `accruePoints` method in `loyalty.service.spec.ts`. The spec tests only cover balance, redemption, and history. New tests should be added for both normal and double-loyalty accrual. |
| E2E test dependencies | Risk | The E2E accrual test needs valid order and user data. The `OrderClient` and `UserClient` may validate the `orderId` and `userId` against stub data. Test UUIDs must match the stub data or the mocks must be configured. |
| Deployment safety | Confirmed Safe | If deployed before Step 2 (order-service), the field is absent in requests and defaults to `0` — identical to current behavior. If deployed after Step 2, the order-service is already sending the field but it's being stripped by the old DTO — points calculate normally. Once both are deployed, double points activate. |
| Method signature change | Note | Adding `doubleLoyaltyPointsTotal` as a new parameter to `accruePoints()` with a default value (`= 0`) is backward-compatible with any callers within the service (e.g., tests). No existing code breaks. |
