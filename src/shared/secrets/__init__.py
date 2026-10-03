"""Secret store port + implementations.

`SecretsManagerSecretStore` (boto3) is intentionally NOT re-exported here — import it from
`src.shared.secrets.aws` in the composition root. Keeping it out of this package's public
surface means importing `src.shared.secrets` (for the `SecretStore` port) stays free of
the AWS SDK, which the "domain is framework-free" import-linter contract requires.
"""

from __future__ import annotations

from .store import EnvSecretStore, SecretNotFound, SecretStore

__all__ = ["EnvSecretStore", "SecretNotFound", "SecretStore"]
