import os
from importlib import import_module

# Import dynamically so static analyzers do not report an unresolved optional SDK
# import when the package is installed in a different interpreter/environment.
Hindsight = import_module("hindsight_client").Hindsight

# Load environment variables from .env without requiring python-dotenv.
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.isfile(env_path):
    with open(env_path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
 
API_KEY = os.getenv("HINDSIGHT_API_KEY")
BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "incident-memory")

client = Hindsight(
    base_url="https://api.hindsight.vectorize.io",
    api_key=API_KEY
)

print(f"Connecting to Hindsight bank '{BANK_ID}'...")

# Realistic Enterprise Incident Post-Mortems
incidents = [
    {
        "title": "PostgreSQL Connection Pool Starvation - auth-cluster-04",
        "content": (
            "INCIDENT #4102 POST-MORTEM: auth-service experienced HTTP 504 Gateway Timeouts "
            "due to PostgreSQL pool exhaustion. Crucial Finding: Increasing max_connections "
            "from 200 to 500 worsened the issue by causing lock contention and high CPU. "
            "Root Cause: Dead connection leaks from unclosed transactions in payment callback webhooks. "
            "Verified Resolution: Do NOT bump max_connections. Apply sysctl 'net.ipv4.tcp_tw_reuse = 1' "
            "and set HikariCP idleTimeout to 30000ms with maxLifetime to 1800000ms. "
            "Refer to Runbook SRE-88."
        )
    },
    {
        "title": "Kafka Rebalance Storm on billing-events-topic",
        "content": (
            "INCIDENT #4189 POST-MORTEM: billing-pipeline workers repeatedly disconnected from Kafka, "
            "causing rebalance storms and 1.2M unacknowledged lag spikes. "
            "Root Cause: Message processing time exceeded max.poll.interval.ms (300s) during batch tax calculation. "
            "Verified Resolution: Increase max.poll.interval.ms to 600000ms, decrease max.poll.records to 100, "
            "and offload tax calculations to an asynchronous thread worker pool. "
            "Refer to Runbook SRE-104."
        )
    },
    {
        "title": "Redis Cluster OOM Crash - session-cache-prod",
        "content": (
            "INCIDENT #4250 POST-MORTEM: session-cache cluster crashed under peak flash sale traffic with OOM errors. "
            "Root Cause: Eviction policy had accidentally reverted to 'noeviction' after node failover instead of 'volatile-lru'. "
            "Verified Resolution: Reconfigure maxmemory-policy to 'volatile-lru', enable active-defrag in redis.conf, "
            "and enforce 24-hour TTL on all OAuth session token keys. "
            "Refer to Runbook SRE-62."
        )
    }
]

for idx, inc in enumerate(incidents, 1):
    print(f"Retaining incident {idx}/{len(incidents)}: {inc['title']}...")
    client.retain(
        bank_id=BANK_ID,
        content=f"[{inc['title']}] {inc['content']}"
    )

print("\nAll 3 enterprise post-mortems successfully retained in Hindsight!")