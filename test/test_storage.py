import pytest
from cpg_utils.deploy_config import set_deploy_config_from_env
from cpg_utils.storage import clear_data_manager, get_dataset_bucket_url, get_global_bucket_url


@pytest.fixture
def mock_config_fixture(json_load):
    def mock_get_server_config():
        return json_load("server_config_01.json")
    return mock_get_server_config


def test_gcp_storage(monkeypatch):
    monkeypatch.setenv("CLOUD", "gcp")
    set_deploy_config_from_env()
    clear_data_manager()

    assert get_dataset_bucket_url("dataset0", "test") == "gs://cpg-dataset0-test"
    assert get_global_bucket_url("global") == "gs://cpg-global"


def test_azure_storage(monkeypatch, mock_config_fixture):
    monkeypatch.setattr("cpg_utils.storage.get_server_config", mock_config_fixture)
    monkeypatch.setenv("CLOUD", "azure")
    monkeypatch.delenv("CPG_DEPLOY_CONFIG", raising=False)
    set_deploy_config_from_env()
    clear_data_manager()

    with pytest.raises(ValueError) as e:
        get_dataset_bucket_url("dataset0", "main-read")
        assert "No such dataset in server config" in str(e.value)

    assert get_dataset_bucket_url("dataset1", "test") == "https://dataset1_idsa.blob.core.windows.net/test"
    assert get_global_bucket_url("global") == "https://cpgsa.blob.core.windows.net/global"
