"""Secret resolution behind a port.

A `secret_ref` stored on a connection (or a webhook signing key ref) is resolved to the
actual value here — never stored in plaintext in the DB (SECURITY-12). Local dev uses
env vars; production uses AWS Secrets Manager. Same call sites either way.
"""

from __future__ import annotations

import os
from typing import Any, Protocol


class SecretNotFound(Exception):
    pass


class SecretStore(Protocol):
    def get_secret(self, secret_ref: str) -> str: ...


class EnvSecretStore:
    """Resolves `env:VAR_NAME` (or a bare name) from environment variables."""

    def get_secret(self, secret_ref: str) -> str:
        name = secret_ref.split("env:", 1)[-1]
        value = os.environ.get(name)
        if value is None:
            raise SecretNotFound(secret_ref)
        return value


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
        except Exception as exc:  # noqa: BLE001
            raise SecretNotFound(secret_ref) from exc
        return str(response["SecretString"])
