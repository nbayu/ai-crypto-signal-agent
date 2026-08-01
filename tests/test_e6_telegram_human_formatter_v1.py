from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import engine.e6_telegram_human_formatter_v1 as subject
from test_e6_publication_envelope_v1 import _envelope, _unsafe_clone


def test_formatter_is_deterministic_and_returns_one_string(tmp_path):
    envelope, *_ = _envelope(
        tmp_path,
        decision="CAUTION",
        side="SHORT",
        name="formatter-deterministic",
    )
    first = subject.format_e6_signal_message_v1(envelope)
    second = subject.format_e6_signal_message_v1(envelope)
    assert type(first) is str
    assert first == second
    assert first
    assert not first.endswith("\n")


def test_human_message_contains_signal_and_timeframe_sections(tmp_path):
    envelope, *_ = _envelope(tmp_path, name="formatter-sections")
    message = subject.format_e6_signal_message_v1(envelope)
    assert "AI CRYPTO SIGNAL — MANUAL OWNER REVIEW" in message
    assert "Signal\n" in message
    assert "Timeframes\n" in message
    assert "Actionable Setup\n" in message
    assert "Risk and Targets\n" in message
    assert "Bounded Reviews\n" in message
    assert "Validity\n" in message
    assert "Owner Action\n" in message
    assert f"Pair: {envelope.canonical_pair}" in message
    assert f"Direction: {envelope.side}" in message
    assert f"Style: {envelope.mode}" in message
    assert "Context: 1w, 1d" in message
    assert "Bias: 4h" in message
    assert "Structure: 1h" in message
    assert "Trigger: 15m" in message


def test_message_presents_zone_admission_stop_and_distinct_targets(tmp_path):
    envelope, *_ = _envelope(tmp_path, name="formatter-geometry")
    message = subject.format_e6_signal_message_v1(envelope)
    assert (
        f"Golden Zone: {envelope.golden_zone_low} – "
        f"{envelope.golden_zone_high}"
    ) in message
    assert f"Captured Admission: {envelope.admission_price}" in message
    assert envelope.admission_exchange_timestamp in message
    assert f"Stop Loss: {envelope.stop_loss}" in message
    assert f"Take Profit TP1: {envelope.tp1}" in message
    assert f"Take Profit TP2: {envelope.tp2}" in message
    assert envelope.tp1 != envelope.tp2


def test_message_presents_scores_risks_and_d6_d7_d8_evidence(tmp_path):
    envelope, *_ = _envelope(
        tmp_path,
        decision="CAUTION",
        side="SHORT",
        name="formatter-reviews",
    )
    message = subject.format_e6_signal_message_v1(envelope)
    assert (
        f"Score: {envelope.pre_review_score} → {envelope.final_score} "
        f"(floor > {envelope.mode_score_floor})"
    ) in message
    assert "Risk / Reason Codes: CAUTION_LIMITED_EVIDENCE" in message
    assert "DeepSeek D6: CAUTION" in message
    assert envelope.deepseek_d6_summary in message
    assert "Claude D7: L1 / ROUTE_L1_CLAUDE_REVIEW_REQUIRED" in message
    assert "Bounded advisory evidence." in message
    assert "Provider D8: DeepSeek=" in message
    assert "fail-closed cause=NONE" in message
    assert envelope.python_final_gate_decision in message
    assert envelope.publication_eligibility_decision in message


def test_message_has_explicit_manual_owner_instruction_and_no_auto_entry(tmp_path):
    envelope, *_ = _envelope(tmp_path, name="formatter-owner")
    message = subject.format_e6_signal_message_v1(envelope)
    assert "Manual owner confirmation is required before ENTRY_ACTIVE." in message
    assert f"Reply: entry {envelope.canonical_pair}" in message
    assert f"Or: tidak entry {envelope.canonical_pair}" in message
    assert "No order has been placed." in message
    assert "No slot or pair lock has been consumed." in message
    assert "cannot send Telegram or publish" in message
    lowered = message.casefold()
    for prohibited in (
        "order executed successfully",
        "exchange order executed",
        "position opened automatically",
        "entry executed automatically",
        "trade has been opened",
        "telegram message sent",
        "signal sent to telegram",
        "automatic entry",
        "auto-entry",
        "slot consumed",
        "llm final authority",
    ):
        assert prohibited not in lowered


def test_validity_and_freshness_are_human_readable(tmp_path):
    envelope, *_ = _envelope(tmp_path, name="formatter-validity")
    message = subject.format_e6_signal_message_v1(envelope)
    assert f"Valid Until: {envelope.valid_until}" in message
    assert "Quote Freshness: PASS" in message
    assert "Trigger Freshness: PASS" in message
    assert f"Lifecycle: {envelope.lifecycle_state}" in message


def test_no_credentials_tokens_or_transport_authority_are_exposed(tmp_path):
    envelope, *_ = _envelope(tmp_path, name="formatter-sensitive")
    message = subject.format_e6_signal_message_v1(envelope).casefold()
    for marker in (
        "api_secret",
        "api key",
        "private_key",
        "bot_token",
        "chat_id",
        "authorization:",
        "bearer ",
        "telegram token",
    ):
        assert marker not in message
    source = Path(subject.__file__).read_text(encoding="utf-8").casefold()
    assert "import telegram" not in source
    assert "requests" not in source
    assert "httpx" not in source
    assert "send_message" not in source


def test_input_type_and_invalid_envelope_fail_closed(tmp_path):
    envelope, *_ = _envelope(tmp_path, name="formatter-invalid")
    invalid = _unsafe_clone(envelope, telegram_send_allowed=True)
    with pytest.raises(ValueError, match="^invalid E6 signal message$"):
        subject.format_e6_signal_message_v1({"mode": "SWING"})
    with pytest.raises(ValueError, match="^invalid E6 signal message$"):
        subject.format_e6_signal_message_v1(invalid)


def test_formatter_public_surface_is_one_pure_function():
    assert subject.__all__ == ("format_e6_signal_message_v1",)
    signature = inspect.signature(subject.format_e6_signal_message_v1)
    assert tuple(signature.parameters) == ("envelope",)
