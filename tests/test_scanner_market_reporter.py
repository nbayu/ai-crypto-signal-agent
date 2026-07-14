from engine.scanner_market_reporter import print_market_summary


def test_print_market_summary_zero_counts(capsys):
    result = print_market_summary(0, 0, 0)

    assert result is None
    assert capsys.readouterr().out == (
        "\n"
        "========== MARKET SUMMARY ==========\n"
        "Scanned  : 0\n"
        "Rejected : 0\n"
        "Qualified: 0\n"
        "===================================\n"
        "\n"
    )


def test_print_market_summary_nonzero_counts(capsys):
    result = print_market_summary(3, 1, 2)

    assert result is None
    assert capsys.readouterr().out == (
        "\n"
        "========== MARKET SUMMARY ==========\n"
        "Scanned  : 3\n"
        "Rejected : 1\n"
        "Qualified: 2\n"
        "===================================\n"
        "\n"
    )
