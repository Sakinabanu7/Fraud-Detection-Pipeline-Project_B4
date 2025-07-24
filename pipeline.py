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
        runner="DataflowRunner",  # ✅ DataflowRunner for Cloud execution
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
