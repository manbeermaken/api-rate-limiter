# API Rate Limiter

A high-performance API rate limiter built with **FastAPI**, **Redis**, and **Lua scripting**, implementing the **token bucket algorithm** for precise request throttling.

## Overview

This project demonstrates a production-ready rate limiting solution that enforces different limits for authenticated users and guest clients. It uses Redis Lua scripts for atomic operations, ensuring accurate rate limit enforcement even under high concurrency.

### Key Features

- **Token Bucket Algorithm**: Smoothly distributes request allowance over time
- **Redis Lua Scripting**: Atomic operations guarantee accurate counting without race conditions
- **Dual-Tier Rate Limiting**:
  - **Authenticated Users**: 20 requests per minute
  - **Guest Users (IP-based)**: 5 requests per minute
- **Detailed Response Headers**: Includes rate limit info and retry-after guidance
- **Async Support**: Built with FastAPI for high performance

## Architecture

### Token Bucket Algorithm

The token bucket algorithm works by:
1. Starting with a bucket of `capacity` tokens
2. Tokens refill at a constant `refill_rate` (tokens per second)
3. Each request consumes 1 token
4. Requests are allowed only if tokens are available
5. Bucket never exceeds its capacity

This approach provides several advantages:
- Allows burst traffic within capacity limits
- Distributes allowance smoothly over time
- Prevents thundering herd scenarios

### Redis Lua Script

The core logic runs in a single atomic Lua transaction, preventing race conditions:
- Checks current token count and timestamp
- Calculates tokens to add based on time elapsed
- Confirms token availability
- Atomically updates state if allowed
- Returns remaining tokens for response headers

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd api-rate-limiter

# Install dependencies
pip install -e .

# Ensure Redis is running
redis-server
```

### Requirements

- Python >= 3.12
- Redis >= 7.0
- FastAPI >= 0.135
- Redis Python client >= 7.4

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

## Project Structure

```
api-rate-limiter/
├── app/
│   └── app.py                 # FastAPI application with rate limiter
├── tests/
│   ├── locustfile.py          # Locust load testing configuration
│   └── results/               # Test result reports and metrics
│       ├── phase-1-*.csv      # Phase 1 results (Under Limit)
│       ├── phase-2-*.csv      # Phase 2 results (At Limit)
│       └── phase-3-*.csv      # Phase 3 results (Over Limit)
├── pyproject.toml             # Project metadata and dependencies
└── README.md                  # This file
```

## Key Findings

1. **Atomic Operations**: Lua scripting prevents race conditions for accurate token counting
2. **Tier Differentiation**: Different limits for guests vs. authenticated users work as intended
3. **Graceful Rejection**: 429 responses are fast and include helpful retry information
4. **Linear Scaling**: Higher request rates proportionally increase rejection rates
5. **Consistent Performance**: Response times remain stable even under load
