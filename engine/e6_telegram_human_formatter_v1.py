"""Pure human-readable presentation of an E6 publication proposal."""

from __future__ import annotations

from engine.e6_publication_envelope_v1 import E6PublicationEnvelopeV1


_ERROR = "invalid E6 signal message"


def _timeframes(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "None"


def format_e6_signal_message_v1(envelope: E6PublicationEnvelopeV1) -> str:
    """Render one validated envelope without transport or send authority."""

    try:
        if type(envelope) is not E6PublicationEnvelopeV1:
            raise ValueError(_ERROR)
        envelope.__post_init__()
        risks = ", ".join(envelope.risk_reason_codes)
        return "\n".join(
            (
                "AI CRYPTO SIGNAL — MANUAL OWNER REVIEW",
                "",
                "Signal",
                f"Pair: {envelope.canonical_pair}",
                f"Direction: {envelope.side}",
                f"Style: {envelope.mode}",
                f"Venue: {envelope.canonical_venue}",
                "",
                "Timeframes",
                f"Context: {_timeframes(envelope.context_timeframes)}",
                f"Optional Context: {_timeframes(envelope.optional_context_timeframes)}",
                f"Bias: {envelope.bias_timeframe}",
                f"Structure: {envelope.structure_timeframe}",
                f"Trigger: {envelope.trigger_timeframe}",
                "",
                "Actionable Setup",
                (
                    "Golden Zone: "
                    f"{envelope.golden_zone_low} – {envelope.golden_zone_high}"
                ),
                (
                    "Captured Admission: "
                    f"{envelope.admission_price} "
                    f"({envelope.admission_price_source})"
                ),
                f"Exchange Time: {envelope.admission_exchange_timestamp}",
                f"Entry Meaning: {envelope.entry_zone_interpretation}",
                f"Trigger: {envelope.trigger_type}",
                f"Closed Candle: {envelope.trigger_candle_close_at}",
                "",
                "Risk and Targets",
                f"Stop Loss: {envelope.stop_loss}",
                (
                    f"Take Profit TP1: {envelope.tp1} "
                    f"({envelope.tp1_destination_kind})"
                ),
                (
                    f"Take Profit TP2: {envelope.tp2} "
                    f"({envelope.tp2_destination_kind})"
                ),
                (
                    "Score: "
                    f"{envelope.pre_review_score} → {envelope.final_score} "
                    f"(floor > {envelope.mode_score_floor})"
                ),
                f"Risk / Reason Codes: {risks}",
                "",
                "Bounded Reviews",
                (
                    "DeepSeek D6: "
                    f"{envelope.deepseek_d6_outcome} — "
                    f"{envelope.deepseek_d6_summary}"
                ),
                (
                    "Claude D7: "
                    f"{envelope.claude_d7_route} / "
                    f"{envelope.claude_d7_outcome} — "
                    f"{envelope.claude_d7_summary}"
                ),
                (
                    "Provider D8: DeepSeek="
                    f"{envelope.d8_deepseek_provider_outcome}; Claude="
                    f"{envelope.d8_claude_provider_outcome}; "
                    "fail-closed cause="
                    f"{envelope.d8_underlying_fail_closed_cause or 'NONE'}"
                ),
                f"Python Final Gate: {envelope.python_final_gate_decision}",
                (
                    "Publication Eligibility: "
                    f"{envelope.publication_eligibility_decision}"
                ),
                "",
                "Validity",
                f"Valid Until: {envelope.valid_until}",
                (
                    "Quote Freshness: PASS — "
                    f"{envelope.quote_age_seconds}s / "
                    f"{envelope.maximum_quote_age_seconds}s max"
                ),
                (
                    "Trigger Freshness: PASS — "
                    f"{envelope.trigger_age_seconds}s / "
                    f"{envelope.maximum_trigger_age_seconds}s max"
                ),
                f"Lifecycle: {envelope.lifecycle_state}",
                "",
                "Owner Action",
                "Manual owner confirmation is required before ENTRY_ACTIVE.",
                f"Reply: entry {envelope.canonical_pair}",
                f"Or: tidak entry {envelope.canonical_pair}",
                (
                    "No order has been placed. No slot or pair lock has "
                    "been consumed."
                ),
                "This formatter cannot send Telegram or publish the signal.",
                f"Signal ID: {envelope.signal_id}",
            )
        )
    except Exception:
        raise ValueError(_ERROR) from None


__all__ = ("format_e6_signal_message_v1",)
