"""One-shot operator entrypoint for a controlled Telegram identity probe."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import getpass
import json
import logging
import sys

from engine.controlled_telegram_identity_probe_v1 import (
    ControlledTelegramIdentityProbeAuthorizationV1,
)
from engine.controlled_telegram_production_configuration_v1 import (
    CONTROLLED_CREDENTIAL_METADATA_VALID,
    INJECTED_SECRET_RESOLVER,
    TELEGRAM_CREDENTIAL_NAME,
    ControlledCredentialMetadataV1,
)
from engine.one_shot_telegram_identity_probe_harness_v1 import (
    run_one_shot_telegram_identity_probe,
)


_LOGGER_NAMES = ("telegram", "httpx", "httpcore", "asyncio")
_MISUSE_JSON = '{"operator_result":"MISUSE"}'
_UNEXPECTED_FAILURE_JSON = '{"operator_result":"UNEXPECTED_FAILURE"}'


def _configure_scoped_logging() -> None:
    for name in _LOGGER_NAMES:
        logging.getLogger(name).setLevel(logging.WARNING)


def _canonical_probed_at(clock_value: object) -> str:
    if (
        not isinstance(clock_value, datetime)
        or clock_value.tzinfo is None
        or clock_value.utcoffset() != timedelta(0)
    ):
        raise ValueError("invalid UTC clock value")
    return clock_value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def run_one_shot_telegram_identity_probe_operator(
    *,
    secret_reader,
    clock,
    harness=run_one_shot_telegram_identity_probe,
) -> tuple[int, str]:
    """Build one controlled invocation and return its exit code and JSON result."""

    _configure_scoped_logging()
    authorization = ControlledTelegramIdentityProbeAuthorizationV1(
        activation_authorized=True,
        workload_authorized=True,
        credential_authorized=True,
        network_authorized=True,
    )
    credential_metadata = ControlledCredentialMetadataV1(
        credential_name=TELEGRAM_CREDENTIAL_NAME,
        source_kind=INJECTED_SECRET_RESOLVER,
        required=True,
        available=True,
        readable=True,
        non_empty=True,
        reason=CONTROLLED_CREDENTIAL_METADATA_VALID,
    )
    probed_at = _canonical_probed_at(clock())
    result = harness(
        authorization=authorization,
        credential_metadata=credential_metadata,
        secret_reader=secret_reader,
        probed_at=probed_at,
    )
    json_text = json.dumps(
        result.to_dict(),
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return (0 if result.bot_identity_confirmed is True else 1, json_text)


def _main_secret_reader():
    return getpass.getpass("Telegram bot token: ")


def _main_clock() -> datetime:
    return datetime.now(timezone.utc)


def main() -> int:
    if len(sys.argv) != 1:
        sys.stdout.write(_MISUSE_JSON + "\n")
        return 2
    try:
        exit_code, json_text = run_one_shot_telegram_identity_probe_operator(
            secret_reader=_main_secret_reader,
            clock=_main_clock,
        )
    except Exception:
        sys.stdout.write(_UNEXPECTED_FAILURE_JSON + "\n")
        return 70
    sys.stdout.write(json_text + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
