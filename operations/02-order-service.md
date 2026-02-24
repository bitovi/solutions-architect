# Implementation Plan: order-service — Propagate `doubleLoyaltyPoints` to Loyalty Accrual

**Date**: 2026-02-24
**Repo**: `bitovi-training/order-service`
**Step**: 2 (depends on product-service changes from Step 1)

---

## 1. Problem Summary

The order-service sits between the product-service and the loyalty-service. When a product has `doubleLoyaltyPoints: true`, the order-service must:

1. **Read** the new `doubleLoyaltyPoints` field from product-service API responses during product validation.
2. **Track** which order line items have double loyalty points.
3. **Calculate** the subtotal of products that qualify for double loyalty points.
4. **Pass** that `doubleLoyaltyPointsTotal` to the loyalty-service when submitting an order, so the loyalty-service can apply the 2x multiplier on that portion.

---

## 2. Assumptions & Constraints

- **Technology**: Go 1.25.5, standard library `net/http`, `github.com/google/uuid v1.6.0`.
- **No database**: In-memory mock storage (`[]models.Order` slice). No migrations.
- **Product-service contract**: After Step 1, `GET /products/:id` returns `{ id, name, description, price, availability, doubleLoyaltyPoints }`. The `doubleLoyaltyPoints` field is a boolean.
- **Loyalty-service contract**: After Step 3, `POST /loyalty/orders` will accept an optional `doubleLoyaltyPointsTotal` field (a float64 representing the subtotal of products that qualify for double loyalty points).
- **Backward compatibility**: The `doubleLoyaltyPointsTotal` field is optional in the loyalty accrual request. If the loyalty-service hasn't been updated yet, it will ignore the extra field (NestJS `whitelist: true` strips unknown fields). Points will be calculated at the normal rate until the loyalty-service is also updated. **This is safe for incremental deployment.**
- **Order-service OpenAPI spec** (`api/openapi.yaml`) is the API contract source of truth and must be updated.

---

## 3. Related Systems/Repos That Are Affected

| Repo | Impact | Dependency Direction |
|---|---|---|
| **product-service** (Step 1) | Must be deployed first. Adds `doubleLoyaltyPoints: boolean` to Product entity and API responses. | Upstream data provider |
| **loyalty-service** (Step 3) | Must accept optional `doubleLoyaltyPointsTotal` in `POST /loyalty/orders` to apply the 2x multiplier. Can be deployed before or after this step (backward-compatible). | Downstream consumer |

---

## 4. Contract & Schema Changes

### 4.1 Product-Service Response (consumed by order-service)

The `ProductResponse` struct in `internal/services/product_client.go` must be updated to include the new field.

**Current**:
```go
type ProductResponse struct {
    ID           int     `json:"id"`
    Name         string  `json:"name"`
    Description  string  `json:"description"`
    Price        float64 `json:"price"`
    Availability bool    `json:"availability"`
}
```

**Proposed**:
```go
type ProductResponse struct {
    ID                   int     `json:"id"`
    Name                 string  `json:"name"`
    Description          string  `json:"description"`
    Price                float64 `json:"price"`
    Availability         bool    `json:"availability"`
    DoubleLoyaltyPoints  bool    `json:"doubleLoyaltyPoints"`
}
```

### 4.2 Loyalty-Service Request (sent by order-service)

The `loyaltyAccrualRequest` struct in `internal/services/loyalty_client.go` must include an optional `doubleLoyaltyPointsTotal` field.

**Current**:
```go
type loyaltyAccrualRequest struct {
    OrderID    string  `json:"orderId"`
    UserID     string  `json:"userId"`
    TotalPrice float64 `json:"totalPrice"`
}
```

**Proposed**:
```go
type loyaltyAccrualRequest struct {
    OrderID                  string  `json:"orderId"`
    UserID                   string  `json:"userId"`
    TotalPrice               float64 `json:"totalPrice"`
    DoubleLoyaltyPointsTotal float64 `json:"doubleLoyaltyPointsTotal,omitempty"`
}
```

### 4.3 Order-Service Internal Models

**`internal/models/order.go`** — Add `DoubleLoyaltyPoints` boolean to `OrderProduct`:

**Current**:
```go
type OrderProduct struct {
    ProductID string `json:"productId"`
    Quantity  int    `json:"quantity"`
}
```

**Proposed**:
```go
type OrderProduct struct {
    ProductID           string `json:"productId"`
    Quantity            int    `json:"quantity"`
    DoubleLoyaltyPoints bool   `json:"doubleLoyaltyPoints,omitempty"`
}
```

### 4.4 OpenAPI Spec Update (`api/openapi.yaml`)

Add `doubleLoyaltyPoints` to the Product schema (under `components.schemas`) and to the `OrderProduct` items schema:

In the Order schema's products items, add:
```yaml
doubleLoyaltyPoints:
  type: boolean
  description: Whether this product yields double loyalty points
```

In the Product schema (if present), add:
```yaml
doubleLoyaltyPoints:
  type: boolean
  description: Whether this product yields double loyalty points when included in an order
```

---

## 5. Data Flow Updates

### Before
```
                      ValidateProduct()
Order Service  ──────────────────────────>  Product Service
    │                 returns (price, name)
    │
    │  SubmitOrder()
    │──────────────────────────────────>  Loyalty Service
         POST /loyalty/orders
         { orderId, userId, totalPrice }
         
         points = floor(totalPrice / 10)
```

### After
```
                      ValidateProduct()
Order Service  ──────────────────────────>  Product Service
    │          returns (price, name, doubleLoyaltyPoints)
    │
    │  SubmitOrder() — calculates doubleLoyaltyPointsTotal
    │──────────────────────────────────>  Loyalty Service
         POST /loyalty/orders
         { orderId, userId, totalPrice, doubleLoyaltyPointsTotal }
         
         regularTotal = totalPrice - doubleLoyaltyPointsTotal
         points = floor(regularTotal / 10) + floor(doubleLoyaltyPointsTotal / 10) * 2
```

---

## 6. Proposed Changes for the Repo

### 6.1 `internal/models/order.go` — Add `DoubleLoyaltyPoints` to `OrderProduct`

```go
type OrderProduct struct {
    ProductID           string `json:"productId"`
    Quantity            int    `json:"quantity"`
    DoubleLoyaltyPoints bool   `json:"doubleLoyaltyPoints,omitempty"`
}
```

This stores the double-loyalty flag per line item so it's available at submission time without re-querying the product-service.

### 6.2 `internal/services/product_client.go` — Read the new field

**Update `ProductResponse`** to include `DoubleLoyaltyPoints`:
```go
type ProductResponse struct {
    ID                   int     `json:"id"`
    Name                 string  `json:"name"`
    Description          string  `json:"description"`
    Price                float64 `json:"price"`
    Availability         bool    `json:"availability"`
    DoubleLoyaltyPoints  bool    `json:"doubleLoyaltyPoints"`
}
```

**Update `ValidateProduct`** to return the flag. Change the signature from:
```go
func (c *ProductServiceClient) ValidateProduct(productID string, authToken string) (float64, string, error)
```

to:
```go
func (c *ProductServiceClient) ValidateProduct(productID string, authToken string) (float64, string, bool, error)
```

The third return value is `doubleLoyaltyPoints`. Update the implementation:
```go
func (c *ProductServiceClient) ValidateProduct(productID string, authToken string) (float64, string, bool, error) {
    product, err := c.GetProduct(productID, authToken)
    if err != nil {
        return 0, "", false, err
    }

    if !product.Availability {
        return 0, "", false, fmt.Errorf("product '%s' (%s) is not available", productID, product.Name)
    }

    return product.Price, product.Name, product.DoubleLoyaltyPoints, nil
}
```

**Update the `ProductClient` interface** to match:
```go
type ProductClient interface {
    GetProduct(productID string, authToken string) (*ProductResponse, error)
    ValidateProduct(productID string, authToken string) (float64, string, bool, error)
}
```

### 6.3 `internal/services/order_service.go` — Store double-loyalty flag & calculate subtotal

**Update `CreateOrder`**: When validating products, capture the `doubleLoyaltyPoints` flag and store it on the `OrderProduct`:

```go
for i := range products {
    price, name, doubleLoyalty, err := s.productClient.ValidateProduct(products[i].ProductID, authToken)
    if err != nil {
        if strings.Contains(err.Error(), "product not found") {
            invalidProducts = append(invalidProducts, products[i].ProductID)
            continue
        }
        return nil, fmt.Errorf("%w: %v", ErrProductServiceUnavailable, err)
    }

    _ = name
    
    // Store the double loyalty flag on the product
    products[i].DoubleLoyaltyPoints = doubleLoyalty
    
    totalPrice += price * float64(products[i].Quantity)
}
```

**Update `UpdateOrderProducts`**: Similarly, when validating new products added to an existing order, capture and store the `doubleLoyaltyPoints` flag. All calls to `s.productClient.ValidateProduct()` in this method must be updated to accept the 4-return-value signature.

In the validation loop for new products:
```go
for _, productID := range newProductIDs {
    _, _, doubleLoyalty, err := s.productClient.ValidateProduct(productID, authToken)
    if err != nil {
        // ... existing error handling ...
    }
    // Update the double loyalty flag
    if p, ok := existingProducts[productID]; ok {
        p.DoubleLoyaltyPoints = doubleLoyalty
        existingProducts[productID] = p
    }
}
```

In the recalculation loop:
```go
for _, orderProduct := range updatedProducts {
    price, _, _, err := s.productClient.ValidateProduct(orderProduct.ProductID, authToken)
    // ...
}
```

**Update `SubmitOrder`**: Calculate the `doubleLoyaltyPointsTotal` before calling the loyalty-service. This requires re-querying product prices (or storing them — but since products are fetched during create/update and prices may have changed, recalculating is safer):

```go
func (s *OrderService) SubmitOrder(orderID string, authToken string) (*models.Order, error) {
    for i, order := range mockOrders {
        if order.ID == orderID {
            if order.Status != models.OrderStatusPending {
                return nil, errors.New("only pending orders can be submitted")
            }
            mockOrders[i].Status = models.OrderStatusProcessing

            // Calculate double loyalty points subtotal
            doubleLoyaltyPointsTotal := 0.0
            for _, product := range order.Products {
                if product.DoubleLoyaltyPoints {
                    price, _, _, err := s.productClient.ValidateProduct(product.ProductID, authToken)
                    if err == nil {
                        doubleLoyaltyPointsTotal += price * float64(product.Quantity)
                    }
                }
            }

            if s.loyaltyClient != nil {
                points, err := s.loyaltyClient.AccruePoints(
                    order.ID,
                    order.UserID,
                    order.TotalPrice,
                    doubleLoyaltyPointsTotal,
                    authToken,
                )
                if err != nil {
                    return nil, err
                }
                mockOrders[i].AccruedLoyaltyPoints = points
            }

            return &mockOrders[i], nil
        }
    }

    return nil, ErrOrderNotFound
}
```

### 6.4 `internal/services/loyalty_client.go` — Pass `doubleLoyaltyPointsTotal`

**Update the `LoyaltyClient` interface**:
```go
type LoyaltyClient interface {
    AccruePoints(orderID string, userID string, totalPrice float64, doubleLoyaltyPointsTotal float64, authToken string) (int, error)
}
```

**Update `loyaltyAccrualRequest`**:
```go
type loyaltyAccrualRequest struct {
    OrderID                  string  `json:"orderId"`
    UserID                   string  `json:"userId"`
    TotalPrice               float64 `json:"totalPrice"`
    DoubleLoyaltyPointsTotal float64 `json:"doubleLoyaltyPointsTotal,omitempty"`
}
```

**Update `AccruePoints` method**:
```go
func (c *LoyaltyServiceClient) AccruePoints(orderID string, userID string, totalPrice float64, doubleLoyaltyPointsTotal float64, authToken string) (int, error) {
    if c.baseURL == "" {
        return 0, fmt.Errorf("loyalty service URL not configured")
    }

    payload := loyaltyAccrualRequest{
        OrderID:                  orderID,
        UserID:                   userID,
        TotalPrice:               totalPrice,
        DoubleLoyaltyPointsTotal: doubleLoyaltyPointsTotal,
    }
    // ... rest unchanged ...
}
```

### 6.5 `api/openapi.yaml` — Update OpenAPI specification

**Update the Product schema** (in `components.schemas`) to add the new field. If a Product schema exists, add:

```yaml
doubleLoyaltyPoints:
  type: boolean
  description: Whether this product yields double loyalty points when included in an order
```

**Update the Order schema's products items** to include the field:

Under `Order.properties.products.items.properties`, add:
```yaml
doubleLoyaltyPoints:
  type: boolean
  description: Whether this product yields double loyalty points
```

### 6.6 `internal/models/product.go` — Update local Product model

Add the field to the local `Product` struct (used for representing product-service data):

```go
type Product struct {
    ID                  string    `json:"id"`
    Name                string    `json:"name"`
    Description         string    `json:"description,omitempty"`
    Price               float64   `json:"price"`
    Category            string    `json:"category,omitempty"`
    InStock             bool      `json:"inStock,omitempty"`
    DoubleLoyaltyPoints bool      `json:"doubleLoyaltyPoints,omitempty"`
    CreatedAt           time.Time `json:"createdAt,omitempty"`
    UpdatedAt           time.Time `json:"updatedAt,omitempty"`
}
```

### 6.7 Test Updates

#### `internal/handlers/orders_test.go`

Update any mock `ProductClient` implementations to return 4 values from `ValidateProduct`:

```go
// MockProductClient for tests
type MockProductClient struct {
    // ...
}

func (m *MockProductClient) ValidateProduct(productID string, authToken string) (float64, string, bool, error) {
    // Return price, name, doubleLoyaltyPoints, error
    // For most test products: return price, name, false, nil
    // For testing double loyalty: return price, name, true, nil
}
```

Update the `MockLoyaltyClient` to accept the new parameter:
```go
func (m *MockLoyaltyClient) AccruePoints(orderID string, userID string, totalPrice float64, doubleLoyaltyPointsTotal float64, authToken string) (int, error) {
    // ...
}
```

Add new test cases:
- **Create order with doubleLoyaltyPoints product**: Verify the `DoubleLoyaltyPoints` flag is stored on the `OrderProduct`.
- **Submit order with mixed products**: Verify that `doubleLoyaltyPointsTotal` is correctly calculated and passed to the loyalty client.
- **Submit order with no double-loyalty products**: Verify `doubleLoyaltyPointsTotal` is 0.

#### `tests/integration/order_workflow_test.go`

Update integration test workflow to verify loyalty points are correctly calculated when double-loyalty products are present. This depends on the loyalty-service also being updated (Step 3).

### 6.8 Mock Order Data — `internal/services/order_service.go`

Update `mockOrders` and `ResetOrderMockData()` to include `DoubleLoyaltyPoints` on order products where applicable (matching the seed data in product-service: product IDs that correspond to Laptop Pro and Mechanical Keyboard should have `DoubleLoyaltyPoints: true`).

---

## 7. Security & Compliance Considerations

- **No new endpoints**: Changes are internal to existing flows.
- **No new auth requirements**: The `doubleLoyaltyPoints` field is read from the product-service using existing authenticated requests.
- **Data integrity**: The `doubleLoyaltyPointsTotal` is calculated server-side from trusted product-service data. Clients cannot manipulate the double-points calculation.
- **No PII exposure**: The field is a business configuration flag, not sensitive data.

---

## 8. Risks, Unknowns, and Open Questions

| Item | Type | Detail |
|---|---|---|
| Interface change risk | Risk | Changing `ValidateProduct` from 3 to 4 return values is a **breaking change** to the `ProductClient` interface. All implementations (real + mock) must be updated simultaneously. This affects test mocks in `orders_test.go`. |
| Deployment ordering | Note | This can be deployed before the loyalty-service update (Step 3). If deployed first, `doubleLoyaltyPointsTotal` will be sent to the loyalty-service but ignored (NestJS `whitelist: true` strips unknown fields). Points will be calculated at the normal 1x rate until Step 3 is deployed. |
| Product price changes | Risk | The `doubleLoyaltyPointsTotal` is recalculated at submission time by re-querying the product-service. If a product's price changed between order creation and submission, the subtotal may differ from `TotalPrice`. This is consistent with existing behavior. |
| Re-querying at submit time | Decision | `SubmitOrder` currently does NOT re-query product prices — it uses the stored `TotalPrice`. For the double-loyalty calculation, we need to query product prices again OR store prices per line item. The proposed plan re-queries only double-loyalty products at submit time. An alternative is to store the per-product price on `OrderProduct` during creation. |
| `LoyaltyClient` interface change | Risk | Adding the `doubleLoyaltyPointsTotal` parameter to `AccruePoints` changes the `LoyaltyClient` interface. All callers and mock implementations must be updated. |
