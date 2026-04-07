from fastapi import FastAPI, Request, Response, Depends, HTTPException
import redis.asyncio as redis
import time
import math

r = redis.Redis(host="localhost", port=6379, db=0)

lua_script = """
local bucket_tokens_key = KEYS[1]
local bucket_timestamp_key = KEYS[2]

local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested_tokens = tonumber(ARGV[4])

local current_tokens = tonumber(redis.call("GET", bucket_tokens_key)) or capacity
local last_time = tonumber(redis.call("GET", bucket_timestamp_key)) or now

local time_passed = math.max(0, now - last_time)
local tokens_to_add = time_passed * refill_rate

current_tokens = math.min(capacity, current_tokens + tokens_to_add)

if current_tokens >= requested_tokens then
    current_tokens = current_tokens - requested_tokens
    redis.call("SET", bucket_tokens_key, current_tokens)
    redis.call("SET", bucket_timestamp_key, now)
    return {1, current_tokens}
else
    redis.call("SET", bucket_tokens_key, current_tokens)
    redis.call("SET", bucket_timestamp_key, now)
    return {0, current_tokens}
end
"""

rate_limit = r.register_script(lua_script)
app = FastAPI()


def get_user_identifier_and_tier(request: Request):
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        mock_user_id = auth_header.split(" ")[1]
        return {
            "id": f"user:{mock_user_id}",
            "capacity": 20,
            "refill_rate": 20 / 60,
        }  # 20 req/min
    else:
        client_ip = request.client.host
        return {
            "id": f"ip:{client_ip}",
            "capacity": 5,
            "refill_rate": 5 / 60,
        }  # 5 req/min


async def rate_limiter(
    response: Response, user_data: dict = Depends(get_user_identifier_and_tier)
):
    now = time.time()

    keys = [
        f"ratelimit:{user_data['id']}:tokens",
        f"ratelimit:{user_data['id']}:timestamp",
    ]

    capacity = user_data["capacity"]
    refill_rate = user_data["refill_rate"]
    requested = 1

    args = [capacity, refill_rate, now, requested]

    result = await rate_limit(keys=keys, args=args)
    is_allowed = result[0]
    remaining = result[1]

    time_to_full = (capacity - remaining) / refill_rate
    reset_timestamp = int(now + time_to_full)

    if is_allowed == 1:
        response.headers["X-RateLimit-Limit"] = str(capacity)
        response.headers["X-RateLimit-Remaining"] = str(int(remaining))
        response.headers["X-RateLimit-Reset"] = str(reset_timestamp)
    else:
        # Calculate exactly how many seconds until 1 token is available to use
        tokens_needed = requested - remaining
        seconds_to_wait = math.ceil(tokens_needed / refill_rate)
        # Fallback to at least 1 second to prevent 0-second retries
        retry_after = max(1, seconds_to_wait)

        raise HTTPException(
            status_code=429,
            detail="Too Many Requests",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(capacity),
                "X-RateLimit-Remaining": str(int(remaining)),
                "X-RateLimit-Reset": str(reset_timestamp),
            },
        )


@app.get("/products", dependencies=[Depends(rate_limiter)])
async def products():
    return {"products": ["Laptop", "Smartphone", "Headphones"]}
