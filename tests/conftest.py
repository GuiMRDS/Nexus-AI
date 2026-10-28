import pytest

import nexus_ai.api as api_module


@pytest.fixture(autouse=True)
def monitoring_isolado(tmp_path, monkeypatch):
    """Cada teste usa um banco de monitoramento próprio, fora de data/monitoring."""
    monkeypatch.setenv("NEXUS_MONITORING_DB", str(tmp_path / "monitoring.db"))
    api_module.get_monitoring.cache_clear()
    yield
    api_module.get_monitoring.cache_clear()
