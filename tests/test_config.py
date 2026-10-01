from src.config import load_config


def test_config_has_ten_companies():
    cfg = load_config()
    assert len(cfg["companies"]) == 10


def test_chunk_overlap_smaller_than_chunk():
    chunking = load_config()["chunking"]
    assert 0 <= chunking["overlap_words"] < chunking["size_words"]


def test_llm_settings_present():
    llm = load_config()["llm"]
    assert llm["provider"] == "github_models"
    assert llm["endpoint"].startswith("https://")
    assert llm["model"]
