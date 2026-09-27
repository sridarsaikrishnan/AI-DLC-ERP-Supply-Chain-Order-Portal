"""Async worker hosts: SQS FIFO consumers, the outbox relay loop, and the reconcile scheduler.

Runs in the AWS/Postgres deployment. Local dev processes inline via the in-memory bus in
the api process, so the worker is only needed once the SNS/SQS + Postgres path is active.
"""
