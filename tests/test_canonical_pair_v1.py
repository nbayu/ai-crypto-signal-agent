"""Direct contracts for canonical pair identity."""

import pytest

from engine.canonical_pair_v1 import CanonicalPairError, normalize_pair


@pytest.mark.parametrize("value", ("sol/usdt", "SOL/USDT", "SOL/USDT:USDT", " SOL / USDT "))
def test_equivalent_pair_forms_normalize_identically(value):
    assert normalize_pair(value) == "SOL/USDT"


def test_legacy_concatenated_pair_is_supported():
    assert normalize_pair("btcusdt") == "BTC/USDT"


@pytest.mark.parametrize("value", (None, "", "SOL", "SOL/", "/USDT", "SOL/USDT:USD", "SOL/SOL", "A/USDT"))
def test_malformed_or_unsupported_pairs_fail_closed(value):
    with pytest.raises(CanonicalPairError, match="PAIR_INVALID"):
        normalize_pair(value)
