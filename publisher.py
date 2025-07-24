import json
import time
from google.cloud import pubsub_v1

# --- GCP Setup ---
project_id = "sakina-gcp"
topic_id = "transactions-topic"

# Create Publisher client
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_id)

# --- Load Transaction Data ---
file_path = "sample_transactions.json"  # Ensure this file is in the same folder

try:
    with open(file_path, "r", encoding="utf-8") as f:
        transactions = json.load(f)
except Exception as e:
    print(f"❌ Error loading JSON file: {e}")
    exit(1)

# --- Publish Messages ---
print(f"🚀 Publishing {len(transactions)} transactions to Pub/Sub topic: {topic_id}")
for txn in transactions:
    try:
        message_json = json.dumps(txn)
        message_bytes = message_json.encode("utf-8")

        future = publisher.publish(topic_path, data=message_bytes)
        print(f"✅ Published: {message_json}")
        time.sleep(1)  # 1 msg/sec to stay within free-tier limits
    except Exception as e:
        print(f"❌ Failed to publish message: {e}")

print("🎉 Done publishing all transactions.")
