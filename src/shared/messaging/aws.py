"""AWS SNS/SQS FIFO adapter (boto3) — implements the EventPublisher port + a consumer.

Same code runs against floci locally (endpoint_url=http://localhost:4566) and real AWS.
Ordering: MessageGroupId = aggregateId (stream). Dedup: MessageDeduplicationId = eventId.
Routing: eventType message attribute drives SNS subscription filter policies.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .envelope import from_json, to_json

if TYPE_CHECKING:
    from src.shared.eventsourcing import StoredEvent

    from .bus import MessageHandler

log = logging.getLogger(__name__)


class SnsFifoPublisher:
    """EventPublisher over an SNS FIFO topic."""

    def __init__(
        self,
        topic_arn: str,
        client: Any | None = None,
        endpoint_url: str | None = None,
        region_name: str | None = None,
    ) -> None:
        if client is None:
            import boto3

            client = boto3.client("sns", endpoint_url=endpoint_url, region_name=region_name)
        self._client = client
        self._topic_arn = topic_arn

    def publish(self, events: list[StoredEvent]) -> None:
        for event in events:
            self._client.publish(
                TopicArn=self._topic_arn,
                Message=to_json(event),
                MessageGroupId=event.stream_id,
                MessageDeduplicationId=event.event_id,
                MessageAttributes={
                    "eventType": {"DataType": "String", "StringValue": event.event_type}
                },
            )


class SqsConsumerRunner:
    """Long-polls one SQS FIFO queue and dispatches to a handler.

    On success the message is deleted; on handler error it is left for SQS to redrive
    (visibility timeout), and after maxReceiveCount it lands in the DLQ. Handlers must be
    idempotent (dedupe on event_id) because delivery is at-least-once.
    """

    def __init__(
        self,
        queue_url: str,
        handler: MessageHandler,
        client: Any | None = None,
        endpoint_url: str | None = None,
        region_name: str | None = None,
        wait_seconds: int = 10,
        batch_size: int = 10,
    ) -> None:
        if client is None:
            import boto3

            client = boto3.client("sqs", endpoint_url=endpoint_url, region_name=region_name)
        self._client = client
        self._queue_url = queue_url
        self._handler = handler
        self._wait_seconds = wait_seconds
        self._batch_size = batch_size

    def poll_once(self) -> int:
        response = self._client.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=self._batch_size,
            WaitTimeSeconds=self._wait_seconds,
        )
        messages = response.get("Messages", [])
        for message in messages:
            event = from_json(message["Body"])
            try:
                self._handler(event)
            except Exception:
                # loop; leaving the message undeleted is what actually triggers SQS
                # redrive -> DLQ after maxReceiveCount, not the exception propagating.
                log.exception(
                    "handler failed for event_id=%s event_type=%s; left for redrive",
                    event.event_id,
                    event.event_type,
                )
                continue
            self._client.delete_message(
                QueueUrl=self._queue_url, ReceiptHandle=message["ReceiptHandle"]
            )
        return len(messages)

    def run_forever(self) -> None:  # pragma: no cover - long-running loop
        while True:
            self.poll_once()
