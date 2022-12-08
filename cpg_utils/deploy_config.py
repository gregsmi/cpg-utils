import json
import logging
from dataclasses import InitVar, dataclass
from os import getenv
from typing import Any, Dict, Optional

from .secrets import SecretManager

deploy_config: "DeployConfig" = None
DEFAULT_CONFIG = {
    "cloud": "gcp",
    "sample_metadata_project": "sample-metadata",
    "sample_metadata_host": "http://localhost:8000",
    "analysis_runner_project": "analysis-runner",
    "analysis_runner_host": "http://localhost:8001",
    "container_registry": "australia-southeast1-docker.pkg.dev",
    "web_host_base": "web.populationgenomics.org.au",
    "reference_base": "gs://cpg-reference",
    "deployment_name": "cpg"
}

@dataclass
class DeployConfig:

    cloud: str = DEFAULT_CONFIG["cloud"],
    sample_metadata_project: str = DEFAULT_CONFIG["sample_metadata_project"]
    sample_metadata_host: str = DEFAULT_CONFIG["sample_metadata_host"]
    analysis_runner_project: str = DEFAULT_CONFIG["analysis_runner_project"]
    analysis_runner_host: str = DEFAULT_CONFIG["analysis_runner_host"]
    container_registry: str = DEFAULT_CONFIG["container_registry"]
    web_host_base: str = DEFAULT_CONFIG["web_host_base"]
    reference_base: str = DEFAULT_CONFIG["reference_base"]
    deployment_name: str = DEFAULT_CONFIG["deployment_name"]

    datasets: InitVar[Optional[Dict[str, Any]]] = None
    _server_config: Dict[str, Any] = None
    _secret_manager: SecretManager = None
    
    def __post_init__(self, datasets):
        self._server_config = datasets

    @staticmethod
    def from_dict(config: Dict[str, str]) -> "DeployConfig":
        return DeployConfig(**config)

    @staticmethod
    def from_environment() -> "DeployConfig":
        deploy_config = json.loads(getenv("CPG_DEPLOY_CONFIG", json.dumps(DEFAULT_CONFIG)))
        # Allow individual field overrides.
        deploy_config["cloud"] = getenv("CLOUD", deploy_config["cloud"])
        deploy_config["sample_metadata_host"] = getenv("SM_HOST_URL", deploy_config["sample_metadata_host"])
        return DeployConfig.from_dict(deploy_config)

    def to_dict(self, include_datasets: bool = False) -> Dict[str, str]:
        deploy_config = {k:v for k,v in self.__dict__.items() if not k.startswith('_')}
        if include_datasets:
            # Filter server_config to avoid outputting sensitive data.
            datasets = { ds: { "projectId": config["projectId"] } for ds, config in self.server_config.items() }
            deploy_config["datasets"] = datasets
        return deploy_config

    @property
    def secret_manager(self) -> SecretManager:
        if self._secret_manager is None:
            self._secret_manager = SecretManager.get_secret_manager(self.cloud)
        return self._secret_manager

    @property
    def server_config(self) -> Dict[str, Any]:
        if self._server_config is None:
            config = self.read_global_config("server-config")
            self._server_config = json.loads(config)
        return self._server_config

    def set_server_config(self, server_config: Dict[str, Any]) -> None:
        self._server_config = server_config

    def read_project_id_config(self, project_id: str, config_key: str) -> str:
        config_host = project_id + "vault" if self.cloud == "azure" else project_id
        return self.secret_manager.read_secret(config_host, config_key)

    def read_global_config(self, config_key: str) -> str:
        project_id = self.deployment_name if self.cloud == "azure" else self.analysis_runner_project
        return self.read_project_id_config(project_id, config_key)

    def read_dataset_config(self, dataset: str, config_key: str) -> str:
        if dataset not in self.server_config:
            return ""
        dataset_id = self.server_config[dataset]["projectId"]
        return self.read_project_id_config(dataset_id, config_key)


def get_deploy_config() -> DeployConfig:
    global deploy_config
    if deploy_config is None:
        set_deploy_config_from_env()
    return deploy_config


def set_deploy_config(config: DeployConfig) -> None:
    global deploy_config
    logging.info(f"setting deploy_config: {json.dumps(config.to_dict())}")
    deploy_config = config


def set_deploy_config_from_env() -> None:
    set_deploy_config(DeployConfig.from_environment())


def get_server_config() -> Dict[str, Any]:
    return get_deploy_config().server_config


def set_server_config(server_config: Dict[str, Any]) -> None:
    get_deploy_config().set_server_config(server_config)
