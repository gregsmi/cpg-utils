from abc import ABC, abstractmethod
from typing import Dict, Optional

from .deploy_config import get_deploy_config, get_server_config

data_manager: "DataManager" = None

class DataManager(ABC):
    """Multi-cloud abstraction for building dataset-related cloud URLs."""

    @staticmethod
    def get_data_manager(cloud_type: Optional[str] = None) -> "DataManager":
        """Instantiates a DataManager object of the appropriate cloud type."""
        if not cloud_type:
            cloud_type = get_deploy_config().cloud
        if cloud_type == "azure":
            return DataManagerAzure()
        assert cloud_type == "gcp"
        return DataManagerGCP()

    @abstractmethod
    def get_global_bucket_url(self, bucket_type: str) -> str:
        """Return deployment-level bucket URL with Hail-style scheme ("gs:" or "https:")."""

    @abstractmethod
    def get_dataset_bucket_url(self, dataset: str, bucket_type: str) -> str:
        """Build dataset-specific bucket URL with Hail-style scheme ("gs:" or "https:")."""


class DataManagerGCP(DataManager):
    """GCP Storage wrapper for building dataset-related cloud URLs."""

    def get_global_bucket_url(self, bucket_type: str) -> str:
        """Return deployment-level bucket URLfor GCP ("gs:")."""
        org_name = get_deploy_config().deployment_name
        return f"gs://{org_name}-{bucket_type}"

    def get_dataset_bucket_url(self, dataset: str, bucket_type: str) -> str:
        """Build dataset-specific Hail-style bucket URL for GCP ("gs:")."""
        org_name = get_deploy_config().deployment_name
        return f"gs://{org_name}-{dataset}-{bucket_type}"


class DataManagerAzure(DataManager):
    """Azure Storage wrapper for building dataset-related cloud URLs."""

    def get_storage_account(self, dataset: Optional[str] = None) -> str:
        """Gets storage host account name based on dataset name or AR base (without scheme)."""
        if dataset:
            # Need to map dataset name to storage account name.
            server_config = get_server_config()
            if dataset not in server_config:
                raise ValueError(f"No such dataset in server config: {dataset}")
            account = server_config[dataset]["projectId"]
        else: # Otherwise use the base deployment storage account.
            account = get_deploy_config().deployment_name
        return f"{account}sa"

    def get_global_bucket_url(self, bucket_type: str) -> str:
        """Return deployment-level bucket URL for Azure ("https:")."""
        return f"https://{self.get_storage_account()}.blob.core.windows.net/{bucket_type}"

    def get_dataset_bucket_url(self, dataset: str, bucket_type: str) -> str:
        """Build dataset-specific Hail-style bucket URL for Azure ("https:")."""
        return f"https://{self.get_storage_account(dataset)}.blob.core.windows.net/{bucket_type}"


def get_data_manager() -> DataManager:
    global data_manager
    if data_manager is None:
        data_manager = DataManager.get_data_manager()
    return data_manager


def clear_data_manager() -> None:
    global data_manager
    data_manager = None


def get_global_bucket_url(bucket_type: str) -> str:
    """Return deployment-level bucket URL with Hail-style scheme ("gs:" or "https:")."""
    return get_data_manager().get_global_bucket_url(bucket_type)


def get_dataset_bucket_url(dataset: str, bucket_type: str) -> str:
    """Return dataset-specific bucket URL with Hail-style scheme ("gs:" or "https:")."""
    return get_data_manager().get_dataset_bucket_url(dataset, bucket_type)


def get_dataset_bucket_config(dataset: str, access_level: str) -> Dict[str, str]:
    """Return full set of dataset-specific bucket URLs for config."""
    assert access_level == "main" or access_level == "test"
    data_manager = get_data_manager()
    return {
        "default" : data_manager.get_dataset_bucket_url(dataset, access_level),
        "web" : data_manager.get_dataset_bucket_url(dataset, f"{access_level}-web"),
        "analysis" : data_manager.get_dataset_bucket_url(dataset, f"{access_level}-analysis"),
        "tmp" : data_manager.get_dataset_bucket_url(dataset, f"{access_level}-tmp"),
        "web_url": f"https://{access_level}-{get_deploy_config().web_host_base}/{dataset}"
    }
