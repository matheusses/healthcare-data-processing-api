"""Unit tests for local Tempo observability configuration."""

from pathlib import Path


def test_tempo_enables_metrics_generator_local_blocks() -> None:
    """TraceQL metrics need metrics-generator + local-blocks to avoid empty ring."""
    tempo_config = (
        Path(__file__).resolve().parents[3] / "observability" / "tempo.yml"
    ).read_text(encoding="utf-8")

    assert "metrics_generator:" in tempo_config
    assert "ring:" in tempo_config
    assert "store: inmemory" in tempo_config
    assert "processors:" in tempo_config
    assert "- local-blocks" in tempo_config


def test_prometheus_remote_write_receiver_enabled_in_compose() -> None:
    """Tempo metrics generator remote_write requires Prometheus receiver enabled."""
    compose_config = (Path(__file__).resolve().parents[3] / "docker-compose.yml").read_text(
        encoding="utf-8"
    )

    assert "--web.enable-remote-write-receiver" in compose_config
