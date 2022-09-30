import os
from unittest.mock import patch

import pytest
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from cpg_utils.cloudpath_hail_az import HailAzureBlobPath, HailAzureBlobClient
import cloudpathlib.exceptions

def test_account_url():
    with pytest.raises(ValueError):
        HailAzureBlobClient(account_url=None)


@patch('cpg_utils.cloudpath_hail_az.BlobServiceClient', autospec=True)
def test_sas_auth(mock_blob_service_client):
    path = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob?not_a_real_sas_token')
    assert mock_blob_service_client.call_args.kwargs['account_url'].endswith('?not_a_real_sas_token')


@patch('cpg_utils.cloudpath_hail_az.BlobServiceClient', autospec=True)
def test_env_auth(mock_blob_service_client, test_resources_path):
    with patch.dict(os.environ, {"AZURE_APPLICATION_CREDENTIALS": os.path.join(test_resources_path, 'azure_creds.json')}):
        path = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob')
        assert isinstance(mock_blob_service_client.call_args.kwargs['credential'], ClientSecretCredential)


@patch('cpg_utils.cloudpath_hail_az.BlobServiceClient', autospec=True)
def test_default_auth(mock_blob_service_client):
    path = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob')
    assert isinstance(mock_blob_service_client.call_args.kwargs['credential'], DefaultAzureCredential)


def test_valid_cloudpath():
    with pytest.raises(cloudpathlib.exceptions.InvalidPrefixError):
        HailAzureBlobPath.is_valid_cloudpath("foo://bar/baz/bah", raise_on_error=True)
    with pytest.raises(cloudpathlib.exceptions.InvalidPrefixError):
        HailAzureBlobPath.is_valid_cloudpath("hail-az://bar.blob.core.windows.net/baz/bah", raise_on_error=True)
    with pytest.raises(cloudpathlib.exceptions.InvalidPrefixError):
        HailAzureBlobPath.is_valid_cloudpath("https://bar/baz/bah", raise_on_error=True)
    with pytest.raises(cloudpathlib.exceptions.InvalidPrefixError):
        HailAzureBlobPath.is_valid_cloudpath("https://bar.blob.core.windows.COM/baz/bah", raise_on_error=True)


@patch('cpg_utils.cloudpath_hail_az.BlobServiceClient', autospec=True)
def test_client_provided( _ ):
    client = HailAzureBlobClient('https://fakeaccount.blob.core.windows.net')
    path = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob', client=client)
    assert path.client == client


@patch('cpg_utils.cloudpath_hail_az.BlobServiceClient', autospec=True)
def test_cloudpath_provided( _ ):
    path1 = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer')
    path2 = HailAzureBlobPath(path1)
    assert path1.as_uri() == path2.as_uri()


@patch('cpg_utils.cloudpath_hail_az.BlobServiceClient', autospec=True)
def test_path_completeness(monkeypatch):
    with pytest.raises(ValueError):
        path = HailAzureBlobPath('hail-az://fakeaccount')
    with pytest.raises(ValueError):
        path = HailAzureBlobPath('hail-az://fakeaccount/')
    HailAzureBlobPath('hail-az://fakeaccount/fakecontainer')
    HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob')
    HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob/')
    HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob/subpath')
    HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob/subpath/')

@patch('cpg_utils.cloudpath_hail_az.BlobServiceClient', autospec=True)
def test_properties(monkeypatch):
    path = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer')
    assert path.account == 'fakeaccount'
    assert path.container == 'fakecontainer'
    assert not path.blob
    path = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/')
    assert not path.blob
    path = HailAzureBlobPath('hail-az://fakeaccount/fakecontainer/fakeblob')
    assert path.blob == 'fakeblob' 
    