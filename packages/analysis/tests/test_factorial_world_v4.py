from pollipi_analysis.simulation.factorial_world_v4 import (
    FACTORIAL_V4_FINGERPRINT,
    build_registry,
    suite_fingerprint,
)


def test_factorial_v4_registry_and_fingerprint_are_stable():
    registry = build_registry()
    assert len(registry) == 120
    assert {row.split for row in registry} == {"calibration", "test"}
    assert any(row.lens > 0 for row in registry if row.split == "test")
    assert not any(row.lens > 0 for row in registry if row.split == "calibration")
    assert suite_fingerprint() == FACTORIAL_V4_FINGERPRINT
