"""Direct offline contracts for independent scanner eligibility."""

from engine import active_signal_ledger_v1 as active
from engine.owner_blueprint_scanner_gate_v1 import (
    GLOBAL_PAIR_ACTIVE,
    STYLE_CAPACITY_FULL,
    evaluate_candidate,
    style_availability,
)


NOW = "2026-07-28T00:00:00Z"
HASH_A = "a" * 64
HASH_B = "b" * 64


def _add(path, ledger, *, style, number, pair):
    ledger = active.reserve_published_signal(
        path, expected_revision=ledger["ledger_revision"],
        transaction_id=f"tx-{style}-{number}", transition_id=f"reserve-{style}-{number}",
        signal_id=f"signal-{style}-{number}", delivery_id=f"delivery-{style}-{number}",
        mode=style, symbol=pair, published_at=NOW, source_payload_hash=HASH_A,
        publication_payload_hash=HASH_B, updated_at=NOW,
    )
    return active.mark_entry_active(
        path, expected_revision=ledger["ledger_revision"],
        transition_id=f"entry-{style}-{number}", signal_id=f"signal-{style}-{number}",
        entry_at=NOW, updated_at=NOW,
    )


def test_full_style_pauses_only_that_style(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = active.initialize_ledger(path, created_at=NOW)
    for number in range(3):
        ledger = _add(path, ledger, style=active.SCALP, number=number, pair=f"SCALP{number}/USDT")
    assert style_availability(ledger) == {
        active.SWING: 3, active.INTRADAY: 3, active.SCALP: 0,
    }
    blocked = evaluate_candidate(ledger, style=active.SCALP, pair="NEXT/USDT")
    assert not blocked.eligible and blocked.reason == STYLE_CAPACITY_FULL
    assert evaluate_candidate(ledger, style=active.SWING, pair="NEXT/USDT").eligible
    assert evaluate_candidate(ledger, style=active.INTRADAY, pair="NEXT/USDT").eligible


def test_active_pair_is_suppressed_across_styles_and_close_restores_next_cycle(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = active.initialize_ledger(path, created_at=NOW)
    ledger = _add(path, ledger, style=active.SWING, number=0, pair="sol/usdt")
    blocked = evaluate_candidate(ledger, style=active.INTRADAY, pair="SOL/USDT:USDT")
    assert not blocked.eligible and blocked.reason == GLOBAL_PAIR_ACTIVE
    closed = active.transition_terminal(
        path, expected_revision=ledger["ledger_revision"], transition_id="owner-close",
        signal_id="signal-SWING-0", terminal_state=active.CLOSED_MANUAL,
        terminal_at=NOW, terminal_reason="OWNER_CONFIRMED_CLOSE", updated_at=NOW,
    )
    assert evaluate_candidate(closed, style=active.INTRADAY, pair="SOL/USDT").eligible
