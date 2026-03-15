import os
import pytest


def test_load_config_from_file(tmp_path):
    import json
    cfg_path = str(tmp_path / "config.json")
    with open(cfg_path, "w") as f:
        json.dump({"serper_api_key": "test", "anthropic_api_key": "test", "pubmed_email": "test@test.com"}, f)

    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from run_research import load_config
    cfg = load_config(cfg_path)
    assert cfg["serper_api_key"] == "test"


def test_load_config_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
    monkeypatch.setenv("SERPER_API_KEY", "serper-env")
    monkeypatch.setenv("PUBMED_EMAIL", "env@test.com")

    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from run_research import load_config
    cfg_path = str(tmp_path / "nonexistent.json")
    cfg = load_config(cfg_path)
    assert cfg["anthropic_api_key"] == "sk-env"
    assert cfg["serper_api_key"] == "serper-env"
    assert cfg["pubmed_email"] == "env@test.com"


def test_load_config_env_overrides_file(tmp_path, monkeypatch):
    import json
    cfg_path = str(tmp_path / "config.json")
    with open(cfg_path, "w") as f:
        json.dump({"serper_api_key": "from-file", "anthropic_api_key": "from-file", "pubmed_email": "file@test.com"}, f)
    monkeypatch.setenv("SERPER_API_KEY", "from-env")

    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from run_research import load_config
    cfg = load_config(cfg_path)
    assert cfg["serper_api_key"] == "from-env"  # env wins
    assert cfg["anthropic_api_key"] == "from-file"  # file kept


def test_load_registry(tmp_path):
    import yaml
    reg_path = str(tmp_path / "registry.yaml")
    with open(reg_path, "w") as f:
        yaml.dump({"topics": [{"id": "test", "title": "Test", "status": "planned", "search_queries": ["q1"]}]}, f)

    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from run_research import load_registry
    topics = load_registry(reg_path)
    assert len(topics) == 1
    assert topics[0]["id"] == "test"


def test_find_topic():
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from run_research import find_topic
    topics = [{"id": "a", "title": "A"}, {"id": "b", "title": "B"}]
    assert find_topic(topics, "a")["title"] == "A"
    assert find_topic(topics, "c") is None


def test_parse_since():
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from run_research import parse_since
    result = parse_since("30d")
    assert len(result) == 10  # YYYY-MM-DD format
    assert result[4] == "-"
