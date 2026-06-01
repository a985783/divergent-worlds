from __future__ import annotations

from engine.ingest import detect_forks_from_series, detect_forks_zscore, detect_all_forks

def test_detect_forks_from_series():
    # 模拟平缓的基线，中途突变
    rows = [
        {"val": "10.0"}, {"val": "10.2"}, {"val": "9.8"}, {"val": "10.1"},
        {"val": "10.0"}, {"val": "9.9"}, {"val": "10.0"}, # 基线前7步均值约 10
        {"val": "13.5"}, # 突变 35% (> 25%)
        {"val": "10.1"},
        {"val": "7.0"}   # 突变 -30% (> 25%)
    ]
    forks = detect_forks_from_series(rows, "val")
    assert len(forks) >= 2
    indices = [f["index"] for f in forks]
    assert 7 in indices
    assert 9 in indices

def test_detect_forks_zscore():
    # 大部分是 10，其中一个是 50 (显著异常点)
    rows = [
        {"val": "10"}, {"val": "10"}, {"val": "10"}, {"val": "10"},
        {"val": "10"}, {"val": "10"}, {"val": "10"}, {"val": "50"},
        {"val": "10"}, {"val": "10"}
    ]
    forks = detect_forks_zscore(rows, "val", threshold=2.0)
    assert len(forks) == 1
    assert forks[0]["index"] == 7
    assert forks[0]["metric"] == "val"

def test_detect_all_forks():
    rows = [
        {"metric_a": "10", "metric_b": "5"},
        {"metric_a": "10", "metric_b": "5"},
        {"metric_a": "10", "metric_b": "5"},
        {"metric_a": "10", "metric_b": "5"},
        {"metric_a": "10", "metric_b": "5"},
        {"metric_a": "10", "metric_b": "5"},
        {"metric_a": "10", "metric_b": "5"},
        {"metric_a": "30", "metric_b": "5"}, # a 突变
        {"metric_a": "10", "metric_b": "15"}, # b 突变
    ]
    forks = detect_all_forks(rows)
    assert len(forks) >= 2
    metrics = {f["metric"] for f in forks}
    assert "metric_a" in metrics
    assert "metric_b" in metrics
