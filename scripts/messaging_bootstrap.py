"""Provision the messaging topology (SNS FIFO topic + SQS FIFO queues + DLQs).

Idempotent. Runs against floci locally (AWS_ENDPOINT_URL=http://localhost:4566) using the
same boto3 code that would target real AWS. In production these resources are defined in
CDK; this script is for local/CI.

Usage:
    AWS_ENDPOINT_URL=http://localhost:4566 AWS_DEFAULT_REGION=us-east-1 \
    AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test python -m scripts.messaging_bootstrap
"""

from __future__ import annotations

import json
import os

import boto3

TOPIC = "platform-domain-events.fifo"

# queue -> the event types it should receive (SNS filter policy); None => all
QUEUES: dict[str, list[str] | None] = {
    "order-processing.fifo": ["OrderSubmitted", "OrderAmended"],
    "order-delivery.fifo": ["OrderReadyForDelivery", "OrderCancellationRequested"],
    "order-fulfillment.fifo": ["ShipmentRecorded", "InvoiceRecorded"],
    "projections.fifo": None,
    "webhook-dispatch.fifo": [
        "OrderSentToErp",
        "OrderConfirmed",
        "OrderClosed",
        "OrderRejected",
        "OrderRetrying",
        "ShipmentRecorded",
        "InvoiceRecorded",
    ],
}
MAX_RECEIVE = 5


def _client(service: str):
    return boto3.client(service, endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))


def main() -> None:
    sns = _client("sns")
    sqs = _client("sqs")

    topic_arn = sns.create_topic(
        Name=TOPIC,
        Attributes={"FifoTopic": "true", "ContentBasedDeduplication": "false"},
    )["TopicArn"]
    print(f"topic: {topic_arn}")

    for queue_name, event_types in QUEUES.items():
        dlq_name = queue_name.replace(".fifo", "-dlq.fifo")
        dlq_url = sqs.create_queue(QueueName=dlq_name, Attributes={"FifoQueue": "true"})["QueueUrl"]
        dlq_arn = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["QueueArn"])[
            "Attributes"
        ]["QueueArn"]

        queue_url = sqs.create_queue(
            QueueName=queue_name,
            Attributes={
                "FifoQueue": "true",
                "RedrivePolicy": json.dumps(
                    {"deadLetterTargetArn": dlq_arn, "maxReceiveCount": MAX_RECEIVE}
                ),
            },
        )["QueueUrl"]
        queue_arn = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])[
            "Attributes"
        ]["QueueArn"]

        attributes: dict[str, str] = {"RawMessageDelivery": "true"}
        if event_types is not None:
            attributes["FilterPolicy"] = json.dumps({"eventType": event_types})
            attributes["FilterPolicyScope"] = "MessageAttributes"

        sns.subscribe(
            TopicArn=topic_arn,
            Protocol="sqs",
            Endpoint=queue_arn,
            Attributes=attributes,
            ReturnSubscriptionArn=True,
        )
        print(f"queue: {queue_name} (dlq: {dlq_name}, maxReceive={MAX_RECEIVE})")

    print("messaging topology ready")


if __name__ == "__main__":
    main()
