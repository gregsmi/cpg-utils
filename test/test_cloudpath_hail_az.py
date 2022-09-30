#import azure.core.exceptions
import azure.identity
#import azure.storage.blob
import os
import pytest
from cpg_utils.cloudpath_hail_az import HailAzureBlobClient, HailAzureBlobPath
import cloudpathlib.exceptions

#from cpg_utils.deploy_config import set_deploy_config_from_env
#from cpg_utils.storage import clear_data_manager, DataManager, get_data_manager, get_dataset_bucket_url
#from cpg_utils.job_config import get_config, remote_tmpdir, set_config_paths, set_job_config, _validate_configs

class MockDefaultAzureCredential:
    def __init__(
        self, 
        exclude_powershell_credential,
        exclude_visual_studio_code_credential,
        exclude_shared_token_cache_credential,
        exclude_interactive_browser_credential
    ):
        pass

class MockClientSecretCredential:
    def __init__(
        self,
        tenant_id,
        client_id,
        client_secret
    ):
        pass


def test_account_url():
    with pytest.raises(ValueError):
        HailAzureBlobClient(account_url=None)


def test_sas_auth(monkeypatch):
    monkeypatch.setattr(azure.identity, 'DefaultAzureCredential', MockDefaultAzureCredential)
    path = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob?not_a_real_sas_token')
    # Can't test that the underlying credential is sas based, but we can verify that the underlying BlobServiceClient was created without issue
    assert path.client.service_client is not None


def test_env_auth(monkeypatch, test_resources_path):
    monkeypatch.setattr(azure.identity, 'ClientSecretCredential', MockClientSecretCredential)
    monkeypatch.setenv('AZURE_APPLICATION_CREDENTIALS', os.path.join(test_resources_path, 'azure_creds.json'))
    path = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob')
    # Can't test that the underlying credential is sas based, but we can verify that the underlying BlobServiceClient was created without issue
    assert path.client.service_client is not None
    monkeypatch.delenv('AZURE_APPLICATION_CREDENTIALS')


def test_default_auth(monkeypatch):
    monkeypatch.setattr(azure.identity, 'DefaultAzureCredential', MockDefaultAzureCredential)
    path = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob')
    # Can't test that the underlying credential is sas based, but we can verify that the underlying BlobServiceClient was created without issue
    assert path.client.service_client is not None


def test_valid_cloudpath():
    with pytest.raises(cloudpathlib.exceptions.InvalidPrefixError):
        HailAzureBlobPath.is_valid_cloudpath("foo://bar/baz/bah", raise_on_error=True)
    with pytest.raises(cloudpathlib.exceptions.InvalidPrefixError):
        HailAzureBlobPath.is_valid_cloudpath("hail-az://bar.blob.core.windows.net/baz/bah", raise_on_error=True)
    with pytest.raises(cloudpathlib.exceptions.InvalidPrefixError):
        HailAzureBlobPath.is_valid_cloudpath("https://bar/baz/bah", raise_on_error=True)
    with pytest.raises(cloudpathlib.exceptions.InvalidPrefixError):
        HailAzureBlobPath.is_valid_cloudpath("https://bar.blob.core.windows.COM/baz/bah", raise_on_error=True)


def test_client_provided(monkeypatch):
    monkeypatch.setattr(azure.identity, 'DefaultAzureCredential', MockDefaultAzureCredential)
    client = HailAzureBlobClient('https://fakeaccount.blob.core.windows.net')
    path = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob', client=client)
    assert path.client == client


def test_cloudpath_provided(monkeypatch):
    monkeypatch.setattr(azure.identity, 'DefaultAzureCredential', MockDefaultAzureCredential)
    path1 = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer')
    path2 = HailAzureBlobPath(path1)
    assert path1.as_uri() == path2.as_uri()


def test_path_completeness(monkeypatch):
    monkeypatch.setattr(azure.identity, 'DefaultAzureCredential', MockDefaultAzureCredential)
    with pytest.raises(ValueError):
        path = HailAzureBlobPath('hail-az://fakeaccount')
    with pytest.raises(ValueError):
        path = HailAzureBlobPath('hail-az://fakeaccount/')
    HailAzureBlobPath('hail-az://fakeaccount/fakecontainer')
    HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob')
    HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob/')
    HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob/subpath')
    HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob/subpath/')

def test_properties(monkeypatch):
    monkeypatch.setattr(azure.identity, 'DefaultAzureCredential', MockDefaultAzureCredential)
    path = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer')
    assert path.account == 'fakeaccount'
    assert path.container == 'fakecontainer'
    assert not path.blob
    path = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/')
    assert not path.blob
    path = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob')
    assert path.blob == 'fakeblob' 


# def test_invalid_path():
#     HailAzureBlobPath('hail-az://@#$%')
    