# API Rate Limiter

A high-performance API rate limiter built with **FastAPI**, **Redis**, and **Lua scripting**, implementing the **token bucket algorithm** for precise request throttling.

## Overview

This project demonstrates a production-ready rate limiting solution that enforces different limits for authenticated users and guest clients. It uses Redis Lua scripts for atomic operations, ensuring accurate rate limit enforcement even under high concurrency.

## Usage

Start the server:

```bash
fastapi run app/app.py
```

### Making Requests

**As a Guest (IP-based limiting):**
```bash
curl -X GET http://localhost:8000/products
```

**As an Authenticated User:**
```bash
curl -X GET http://localhost:8000/products \
  -H "Authorization: Bearer user_123"
```

### Response Headers

Successful requests include:
- `X-RateLimit-Limit`: Request capacity
- `X-RateLimit-Remaining`: Remaining tokens in bucket
- `X-RateLimit-Reset`: Unix timestamp when bucket resets

Rate-limited responses (HTTP 429) include:
- `Retry-After`: Seconds to wait before retrying
- All rate limit headers above

## Testing

Load testing was conducted using **Locust** across three phases to validate rate limit behavior:

### Test Configuration

- **Phase 1 (Under Limit)**: Guests wait 14-16s between requests, Authenticated users wait 3.5-4s
- **Phase 2 (At Limit)**: Guests wait 11-13s between requests, Authenticated users wait 2.8-3.2s  
- **Phase 3 (Over Limit)**: Guests wait 4-6s between requests, Authenticated users wait 1-2s

### Phase 1: Under Limit

**Scenario**: Request rates below configured limits, ensuring smooth operation.

| Metric | Guest | Authenticated | Aggregated |
|--------|-------|-------|-------|
| Total Requests | 8 | 96 | 104 |
| Failures | 0 | 0 | 0 |
| Failure Rate | 0% | 0% | 0% |
| Median Response Time | 7ms | 6ms | 6ms |
| Average Response Time | 7.3ms | 5.5ms | 5.6ms |
| P95 Response Time | 14ms | 8ms | 8ms |
| P99 Response Time | 14ms | 12ms | 14ms |
| Throughput | 0.067 req/s | 0.81 req/s | 0.879 req/s |

**Analysis**: All requests succeed with consistent response times. The rate limiter allows traffic normally when below thresholds.

---

### Phase 2: At Limit

**Scenario**: Request rates at exactly the configured limits, testing rate limit precision.

| Metric | Guest | Authenticated | Aggregated |
|--------|-------|-------|-------|
| Total Requests | 11 | 120 | 131 |
| Failures | 0 | 0 | 0 |
| Failure Rate | 0% | 0% | 0% |
| Median Response Time | 5ms | 6ms | 6ms |
| Average Response Time | 6.3ms | 5.9ms | 5.9ms |
| P95 Response Time | 11ms | 9ms | 9ms |
| P99 Response Time | 11ms | 11ms | 22ms |
| Throughput | 0.092 req/s | 1.003 req/s | 1.095 req/s |

**Analysis**: Requests continue to pass with no rejections as traffic matches the refill rate. The rate limiter operates at equilibrium.

---

### Phase 3: Over Limit

**Scenario**: Request rates exceeding configured limits, validating rate limit enforcement.

| Metric | Guest | Authenticated | Aggregated |
|--------|-------|-------|-------|
| Total Requests | 24 | 235 | 259 |
| Failures | 10 | 58 | 68 |
| Failure Rate | 41.7% | 24.7% | **26.3%** |
| Median Response Time | 7ms | 7ms | 7ms |
| Average Response Time | 7.5ms | 5.7ms | 5.9ms |
| P95 Response Time | 9ms | 8ms | 8ms |
| P99 Response Time | 23ms | 8ms | 10ms |
| Throughput | 0.201 req/s | 1.971 req/s | 2.172 req/s |
| Failure Rate (req/s) | 0.084 | 0.486 | 0.570 |

**Analysis**: Rate limiting actively rejects excess requests with HTTP 429 responses. Guest users experience 41.7% rejection (2.5x over limit), while authenticated users see 24.7% rejection (~2x over limit). Response times remain fast even under rejection, indicating efficient rate limiter processing.
