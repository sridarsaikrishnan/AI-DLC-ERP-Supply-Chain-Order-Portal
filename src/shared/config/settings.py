"""Settings — all configuration in one typed place, sourced from env (12-factor).

Plain stdlib dataclass (no third-party dependency) reading environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    profile: str  # "memory" (local dev/tests, no infra) | "postgres" (Postgres + SNS/SQS)
    database_url: str
    aws_endpoint_url: str | None
    aws_region: str
    domain_topic_arn: str
    erp_odoo_mode: str  # "real" | "stub"
    erp_odoo_timeout_seconds: float
    log_level: str
    reconcile_interval_seconds: int


@lru_cache
def get_settings() -> Settings:
    return Settings(
        profile=os.environ.get("APP_PROFILE", "memory"),
        database_url=os.environ.get(
            "DATABASE_URL", "postgresql+psycopg2://portal:portal@localhost:5432/portal"
        ),
        aws_endpoint_url=os.environ.get("AWS_ENDPOINT_URL"),  # http://localhost:4566 for floci
        aws_region=os.environ.get("AWS_REGION", "us-east-1"),
        domain_topic_arn=os.environ.get(
            "DOMAIN_TOPIC_ARN", "arn:aws:sns:us-east-1:000000000000:platform-domain-events.fifo"
        ),
        erp_odoo_mode=os.environ.get("ERP_ODOO_MODE", "real"),
        erp_odoo_timeout_seconds=float(os.environ.get("ERP_ODOO_TIMEOUT_SECONDS", "10")),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        reconcile_interval_seconds=int(os.environ.get("RECONCILE_INTERVAL_SECONDS", "900")),
    )
