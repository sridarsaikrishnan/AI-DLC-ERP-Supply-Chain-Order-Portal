"""AWS Secrets Manager implementation of the `SecretStore` port.

Deliberately in its own module (not `store.py`): it imports boto3, and keeping it out of
the port module means a domain module can depend on `SecretStore` without transitively
pulling in the AWS SDK — the "domain is framework-free" import-linter contract. Only the
composition root (api/worker layer) imports this.
"""

from __future__ import annotations

from typing import Any

from .store import SecretNotFound


class SecretsManagerSecretStore:
    """Resolves an AWS Secrets Manager ARN/name via boto3 (floci locally, AWS in prod)."""

    def __init__(
        self, client: Any | None = None, endpoint_url: str | None = None, region_name: str | None = None
    ) -> None:
        if client is None:
            import boto3

            client = boto3.client("secretsmanager", endpoint_url=endpoint_url, region_name=region_name)
        self._client = client

    def get_secret(self, secret_ref: str) -> str:
        try:
            response = self._client.get_secret_value(SecretId=secret_ref)
        except Exception as exc:
            raise SecretNotFound(secret_ref) from exc
        return str(response["SecretString"])

    def put_secret(self, secret_ref: str, value: str) -> None:
        try:
            self._client.create_secret(Name=secret_ref, SecretString=value)
        except self._client.exceptions.ResourceExistsException:
            self._client.put_secret_value(SecretId=secret_ref, SecretString=value)
