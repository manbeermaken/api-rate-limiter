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
    return {1, tostring(current_tokens)}
else
    redis.call("SET", bucket_tokens_key, current_tokens)
    redis.call("SET", bucket_timestamp_key, now)
    return {0, tostring(current_tokens)}
end