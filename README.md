# Real- Time Fraud-Detection-Pipeline-Project

````markdown
 

This project demonstrates a real-time fraud detection system using **Cloud Pub/Sub**, **Cloud Dataflow (Apache Beam)**, and **BigQuery**.

---

##  Project Overview

- **Objective**: Detect potentially fraudulent transactions in real time.
- **Tools Used**:
  - **Cloud Pub/Sub**: For ingesting streaming data
  - **Apache Beam / Dataflow**: For real-time processing
  - **BigQuery**: For storing and analyzing flagged fraud data
- **Project ID**: `sakina-gcp`

---

##  Fraud Rules Implemented

The pipeline flags a transaction as fraudulent if **any** of the following conditions are met:

1. **High Amount Fraud**: Amount > **$10,000**
2. **Unusual Country**: Country not in `["Canada", "US"]`
3. **Suspicious IP**: IP address starts with `192.168.`

---

## 📁 Input Data (JSON)

Format of transaction data from `sample_transactions.json` (used in the project):

```json
{
  "transaction_id": "txn004",
  "user_id": "user002",
  "amount": 7000,
  "country": "USA",
  "ip": "192.168.2.2",
  "timestamp": "2025-07-18T11:00:00Z"
}
````

---

##  Project Setup

### Step 1: Enable Required GCP Services

```bash
gcloud services enable pubsub.googleapis.com \
                       dataflow.googleapis.com \
                       bigquery.googleapis.com \
                       storage.googleapis.com \
                       logging.googleapis.com \
                       --project=sakina-gcp
```

---

### Step 2: Create Pub/Sub Topic

```bash
gcloud pubsub topics create transactions-topic --project=sakina-gcp
```

---

### Step 3: Create BigQuery Dataset

```bash
bq mk --dataset sakina-gcp:fraud_detection
```

---

##  Publisher Script (`publisher.py`)

Publishes JSON transactions to the Pub/Sub topic at 1 message per second.

```python
import json
import time
from google.cloud import pubsub_v1

project_id = "sakina-gcp"
topic_id = "transactions-topic"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_id)

file_path = "sample_transactions.json"  # Ensure this file is in the same folder

with open(file_path, "r", encoding="utf-8") as f:
    transactions = json.load(f)

print(f" Publishing {len(transactions)} transactions to Pub/Sub topic: {topic_id}")
for txn in transactions:
    message_json = json.dumps(txn)
    message_bytes = message_json.encode("utf-8")
    publisher.publish(topic_path, data=message_bytes)
    print(f" Published: {message_json}")
    time.sleep(1)

print("🎉 Done publishing all transactions.")
```

Run it:

```bash
python publisher.py
```

---

##  Dataflow Pipeline (`pipeline.py`)

Processes streaming data from Pub/Sub, flags fraud, and writes to BigQuery.

```python
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
import json
import logging

class FraudDetectionDoFn(beam.DoFn):
    def process(self, element):
        try:
            record = json.loads(element)
            fraud_reason = None

            if record.get("amount", 0) > 10000:
                fraud_reason = "High amount"
            elif record.get("country") not in ["Canada", "US"]:
                fraud_reason = "Unusual country"
            elif record.get("ip", "").startswith("192.168."):
                fraud_reason = "Suspicious IP"

            if fraud_reason:
                record["fraud_reason"] = fraud_reason
                yield record
        except Exception as e:
            logging.error(f"Error processing record: {e}")

def run():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_topic", required=True)
    parser.add_argument("--output_table", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--temp_location", required=True)
    args, beam_args = parser.parse_known_args()

    options = PipelineOptions(
        beam_args,
        project=args.project,
        region=args.region,
        temp_location=args.temp_location,
        runner="DataflowRunner",
        streaming=True
    )
    options.view_as(StandardOptions).streaming = True

    with beam.Pipeline(options=options) as p:
        (
            p
            | "ReadFromPubSub" >> beam.io.ReadFromPubSub(topic=args.input_topic).with_output_types(bytes)
            | "Decode" >> beam.Map(lambda x: x.decode("utf-8"))
            | "DetectFraud" >> beam.ParDo(FraudDetectionDoFn())
            | "ToBigQuery" >> beam.io.WriteToBigQuery(
                args.output_table,
                schema="transaction_id:STRING,user_id:STRING,amount:FLOAT,country:STRING,ip:STRING,timestamp:TIMESTAMP,fraud_reason:STRING",
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED
            )
        )

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    run()
```

Run the pipeline:

```bash
python pipeline.py \
  --input_topic=projects/sakina-gcp/topics/transactions-topic \
  --output_table=sakina-gcp:fraud_detection.flagged_transactions \
  --project=sakina-gcp \
  --region=us-central1 \
  --temp_location=gs://raw_bronze1/temp \
  --runner=DataflowRunner
```

---

##  Verifying Output in BigQuery

Check row count:

```bash
bq query --use_legacy_sql=false \
'SELECT COUNT(*) as row_count FROM `sakina-gcp.fraud_detection.flagged_transactions`'
```

Query flagged data:

```bash
bq query --use_legacy_sql=false '
SELECT * FROM `sakina-gcp.fraud_detection.flagged_transactions`
ORDER BY timestamp DESC
LIMIT 10'
```

---
 

##  Project Structure

```
bootcamp4/
├── Architecture diag
├── Output SS
├── publisher.py
├── pipeline.py
├── sample_transactions.json
├── README.md
```

---
 
