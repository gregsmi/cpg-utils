import os
import json

from cpg_utils.config import get_config, set_config_paths
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


def test_config_from_toml(test_resources_path, json_load):
    set_config_paths([os.path.join(test_resources_path, "config_01.toml")])
    get_config()

    cfg1 = json_load("config_01.json")
    dc = get_deploy_config()
    assert dc.to_dict() == cfg1
