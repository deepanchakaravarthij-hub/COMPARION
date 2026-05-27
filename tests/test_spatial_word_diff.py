from __future__ import annotations

from app.services.comparison.pdf_engine import word_diff_page


def test_spatial_word_diff_ignores_reordered_identical_words() -> None:
    words_a = [
        {"text": "User", "x": 0.1, "y": 0.1, "w": 0.05, "h": 0.02},
        {"text": "loss", "x": 0.16, "y": 0.1, "w": 0.04, "h": 0.02},
    ]
    words_b = [
        {"text": "loss", "x": 0.16, "y": 0.1, "w": 0.04, "h": 0.02},
        {"text": "User", "x": 0.1, "y": 0.1, "w": 0.05, "h": 0.02},
    ]

    assert word_diff_page(words_a, words_b, page=1) == []


def test_spatial_word_diff_detects_numeric_change() -> None:
    words_a = [{"text": "147", "x": 0.12, "y": 0.18, "w": 0.05, "h": 0.03}]
    words_b = [{"text": "149", "x": 0.12, "y": 0.18, "w": 0.05, "h": 0.03}]

    changes = word_diff_page(words_a, words_b, page=1)
    assert len(changes) == 2
    assert {change["type"] for change in changes} == {"removed", "added"}
    assert all(change["category"] == "text" for change in changes)


def test_spatial_word_diff_ignores_fuzzy_ocr_noise() -> None:
    words_a = [{"text": "acquisitions", "x": 0.1, "y": 0.2, "w": 0.08, "h": 0.02}]
    words_b = [{"text": "acquisitlons", "x": 0.1, "y": 0.2, "w": 0.08, "h": 0.02}]

    assert word_diff_page(words_a, words_b, page=1) == []


def test_spatial_word_diff_flags_unmatched_insertions() -> None:
    words_a = [{"text": "Total", "x": 0.1, "y": 0.2, "w": 0.04, "h": 0.02}]
    words_b = [
        {"text": "Total", "x": 0.1, "y": 0.2, "w": 0.04, "h": 0.02},
        {"text": "149", "x": 0.15, "y": 0.2, "w": 0.03, "h": 0.02},
    ]

    changes = word_diff_page(words_a, words_b, page=1)
    assert len(changes) == 1
    assert changes[0]["type"] == "added"
    assert changes[0]["source_ref"]["document"] == "b"
