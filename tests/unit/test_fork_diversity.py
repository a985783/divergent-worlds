from __future__ import annotations

from engine.fork_generator import validate_branch_diversity
from engine.schemas import BranchWorld

def test_branch_diversity_high():
    branches = [
        BranchWorld(
            branch_name="Branch Alpha",
            core_assumption="This is a sudden surge in consumer demand.",
            changed_variables={"demand": 1.5, "price": 1.2},
            initial_probability=0.5,
            support_signals=["sign1", "sign2", "sign3"],
            failure_signals=["fail1", "fail2"],
        ),
        BranchWorld(
            branch_name="Branch Beta",
            core_assumption="A regulatory intervention restricts supply chains.",
            changed_variables={"supply": 0.5, "tax": 1.4},
            initial_probability=0.5,
            support_signals=["sign4", "sign5", "sign6"],
            failure_signals=["fail3", "fail4"],
        )
    ]
    score, warnings = validate_branch_diversity(branches)
    assert score > 0.6
    # No duplicate warnings or close assumption warnings
    assert not any("名称重复" in w for w in warnings)
    assert not any("核心假设过于相似" in w for w in warnings)

def test_branch_diversity_low_duplicate_names():
    branches = [
        BranchWorld(
            branch_name="Branch Alpha",
            core_assumption="Demand surges rapidly.",
            changed_variables={"demand": 1.5},
            initial_probability=0.5,
            support_signals=["sign1", "sign2", "sign3"],
            failure_signals=["fail1", "fail2"],
        ),
        BranchWorld(
            branch_name="Branch Alpha",
            core_assumption="Demand surges rapidly.",
            changed_variables={"demand": 1.5},
            initial_probability=0.5,
            support_signals=["sign4", "sign5", "sign6"],
            failure_signals=["fail3", "fail4"],
        )
    ]
    score, warnings = validate_branch_diversity(branches)
    assert score < 0.5
    assert any("名称重复" in w for w in warnings)
    assert any("核心假设过于相似" in w for w in warnings)
