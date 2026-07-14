import pytest

from engine.scanner_score_adjustment import apply_scanner_score_adjustment


@pytest.mark.parametrize(
    ("score", "distance_ob", "atr", "expected"),
    [
        (50, 21, 10, 42),
        (50, 20, 10, 46),
        (50, 15, 10, 46),
        (50, 10, 10, 50),
        (5, 21, 10, 0),
        (50, 5, 10, 50),
    ],
)
def test_apply_scanner_score_adjustment_boundaries(
    score, distance_ob, atr, expected
):
    assert apply_scanner_score_adjustment(score, distance_ob, atr) == expected
