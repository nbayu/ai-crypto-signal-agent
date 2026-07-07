from pathlib import Path


PINE_PATH = Path(
    "tradingview/ai_agent_scanner_visual.pine"
)


def _pine_source():
    return PINE_PATH.read_text()


def test_pine_decodes_multi_setup_delivery_payload():
    source = _pine_source()

    assert 'str.split(scannerPayload, "~")' in source
    assert 'str.split(record, "|")' in source
    assert "array.size(fields) == 13" in source


def test_pine_selects_only_exact_current_chart_symbol():
    source = _pine_source()

    assert (
        "chartSymbol == "
        "ticker.standard(syminfo.tickerid)"
    ) in source
    assert "scannerSetupFound := true" in source
    assert "break" in source


def test_pine_resets_setup_state_before_payload_scan():
    source = _pine_source()

    reset_position = source.index(
        "scannerSetupFound := false"
    )
    records_position = source.index(
        'records = str.split(scannerPayload, "~")'
    )

    assert reset_position < records_position


def test_pine_requires_complete_scanner_values_before_render():
    source = _pine_source()

    required_guards = (
        "and scannerSetupFound",
        'and scannerDirection != ""',
        "and not na(scannerLowTime)",
        "and not na(scannerHighTime)",
        "and not na(scannerLow)",
        "and not na(scannerHigh)",
        "and not na(scannerFib0)",
        "and not na(scannerFib05)",
        "and not na(scannerFib0618)",
        "and not na(scannerFib0786)",
        "and not na(scannerFib1)",
        "and not na(scannerTp)",
    )

    for guard in required_guards:
        assert guard in source


def test_pine_renders_only_when_valid_fib_is_true():
    source = _pine_source()

    assert "if validFib" in source
    assert "goldenZoneBox := box.new(" in source
    assert "fibAnchorLine := line.new(" in source
    assert "fibTpLine := line.new(" in source


def test_pine_uses_scanner_levels_without_recalculating_fibonacci():
    source = _pine_source()

    assert "scannerFib0618" in source
    assert "scannerFib0786" in source
    assert (
        "scannerEntryLow = math.min("
        in source
    )
    assert (
        "scannerEntryHigh = math.max("
        in source
    )

    forbidden = (
        "ta.pivothigh",
        "ta.pivotlow",
        "ta.highest",
        "ta.lowest",
    )

    for expression in forbidden:
        assert expression not in source


def test_pine_has_no_signal_alert_or_execution_behavior():
    source = _pine_source()

    forbidden = (
        "alertcondition(",
        "alert(",
        "strategy.entry(",
        "strategy.exit(",
        "strategy.order(",
    )

    for expression in forbidden:
        assert expression not in source
