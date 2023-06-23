import os
import json
from cpg_utils.cloudpath_hail_az import HailAzureBlobPath

from cpg_utils.config import get_config, set_config_paths
from cpg_utils.hail_batch import dataset_path, image_path, output_path, reference_path, remote_tmpdir, web_url
from cpg_utils.deploy_config import (
    DEFAULT_CONFIG,
    DeployConfig,
    get_deploy_config,
    set_deploy_config,
    set_deploy_config_from_env
)


def test_default_config(monkeypatch):
    monkeypatch.delenv("CPG_DEPLOY_CONFIG", raising=False)
    monkeypatch.delenv("CLOUD", raising=False)
    set_deploy_config_from_env()
    dc = get_deploy_config()
    assert dc.to_dict() == DEFAULT_CONFIG


def test_env_config(monkeypatch, json_load):
    cfg1 = json_load("config_01.json")
    monkeypatch.setenv("CPG_DEPLOY_CONFIG", json.dumps(cfg1))
    set_deploy_config(DeployConfig.from_environment())
    dc = get_deploy_config()
    print(json.dumps(dc.to_dict(), indent=4))
    assert dc.to_dict() == cfg1


def test_env_override_config(monkeypatch):
    monkeypatch.delenv("CPG_DEPLOY_CONFIG", raising=False)
    monkeypatch.setenv("CLOUD", "azure")
    dc = DeployConfig.from_environment()
    assert dc.cloud == "azure"


def test_config_from_dict(json_load):
    cfg1 = json_load("config_01.json")
    dc = DeployConfig.from_dict(cfg1)
    assert dc.to_dict() == cfg1


def test_config_from_toml(monkeypatch, test_resources_path, json_load):
    monkeypatch.delenv("CPG_DEPLOY_CONFIG", raising=False)
    set_deploy_config_from_env()

    set_config_paths([os.path.join(test_resources_path, "config_01.toml")])
    get_config() # this should trigger loading deploy_config from TOML file

    cfg1 = json_load("config_01.json")
    scfg1 = json_load("server_config_01.json")
    dc = get_deploy_config()
    assert dc.to_dict() == cfg1
    assert dc.server_config == scfg1

    assert "datasets" not in cfg1
    scfg1["dataset1"] = {"projectId": "dataset1_id"}
    cfg1["datasets"] = scfg1
    assert dc.to_dict(include_datasets=True) == cfg1


def test_config_storage(monkeypatch, test_resources_path):
    set_config_paths([os.path.join(test_resources_path, "config_01.toml")])
    monkeypatch.delenv("CPG_DEPLOY_CONFIG", raising=False)
    set_deploy_config_from_env()

    assert dataset_path("one", "web") == "https://sevgen002sa.blob.core.windows.net/test-web/one"
    assert dataset_path("two", "analysis", "rgp") == "https://raregen001sa.blob.core.windows.net/test-analysis/two"
    assert output_path("three") == "https://sevgen002sa.blob.core.windows.net/test/gregsmi/three"
    assert remote_tmpdir() == "https://sevgen002sa.blob.core.windows.net/hail/batch-tmp"
    assert web_url("four") == "https://test-web-azcpg001.azurewebsites.net/severalgenomes/four"
    assert reference_path("genome_build") == HailAzureBlobPath("https://cpgar01.blob.core.windows.net/reference/GRCh38")
    assert reference_path("seqr/combined_reference") == HailAzureBlobPath("https://cpgar01.blob.core.windows.net/reference/combined_reference_data_grch38.ht")
    assert image_path("vep") == "ar-docker.pkg.dev/cpg-common/images/vep:105.0"



