"""
Extend cloudpathlib Azure implementation to support hail-az:// scheme.
Inspired by https://github.com/drivendataorg/cloudpathlib/issues/157
"""

import re
import os
from typing import Union, Optional, Any, Callable
from urllib.parse import urlparse
import mimetypes
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.storage.blob import BlobServiceClient
from cloudpathlib import AzureBlobClient, AzureBlobPath
from cloudpathlib.client import register_client_class
from cloudpathlib.cloudpath import register_path_class, CloudPath
from cloudpathlib.exceptions import InvalidPrefixError


@register_client_class('hail-az')
class HailAzureBlobClient(AzureBlobClient):
    def __init__(
        self,
        account_url: Optional[str] = None,
        credential: Optional[Any] = None,
        connection_string: Optional[str] = None,
        blob_service_client: Optional["BlobServiceClient"] = None,
        local_cache_dir: Optional[Union[str, os.PathLike]] = None,
        content_type_method: Optional[Callable] = mimetypes.guess_type,
    ):
        """Class constructor. Sets up a [`BlobServiceClient`](
        https://docs.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.blobserviceclient?view=azure-python).
        Supports the following authentication methods, specific to Hail Batch.
        - Implicit instantiation of a [`DefaultAzureCredential`](https://learn.microsoft.com/en-us/dotnet/api/azure.identity.defaultazurecredential?view=azure-dotnet-preview)
        - Environment variable `"AZURE_APPLICATION_CREDENTIALS"` containing a path to a JSON file that in turn contains three fields: 
        "tenant", "appId", and "password".
        - Account URL via `account_url`, authenticated either with an embedded SAS token, or with
        credentials passed to `credentials`.
        - Connection string via `connection_string`, authenticated either with an embedded SAS
        token or with credentials passed to `credentials`.
        - Instantiated and already authenticated [`BlobServiceClient`](
        https://docs.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.blobserviceclient?view=azure-python).
        If multiple methods are used, priority order is reverse of list above (later in list takes
        priority). If no methods are used, a [`MissingCredentialsError`][cloudpathlib.exceptions.MissingCredentialsError]
        exception will be raised raised.
        Args:
            account_url (Optional[str]): The URL to the blob storage account, optionally
                authenticated with a SAS token. See documentation for [`BlobServiceClient`](
                https://docs.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.blobserviceclient?view=azure-python).
            credential (Optional[Any]): Credentials with which to authenticate. Can be used with
                `account_url` or `connection_string`, but is unnecessary if the other already has
                an SAS token. See documentation for [`BlobServiceClient`](
                https://docs.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.blobserviceclient?view=azure-python)
                or [`BlobServiceClient.from_connection_string`](
                https://docs.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.blobserviceclient?view=azure-python#from-connection-string-conn-str--credential-none----kwargs-).
            connection_string (Optional[str]): A connection string to an Azure Storage account. See
                [Azure Storage SDK documentation](
                https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python#copy-your-credentials-from-the-azure-portal).
            blob_service_client (Optional[BlobServiceClient]): Instantiated [`BlobServiceClient`](
                https://docs.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.blobserviceclient?view=azure-python).
            local_cache_dir (Optional[Union[str, os.PathLike]]): Path to directory to use as cache
                for downloaded files. If None, will use a temporary directory.
            content_type_method (Optional[Callable]): Function to call to guess media type (mimetype) when
                writing a file to the cloud. Defaults to `mimetypes.guess_type`. Must return a tuple (content type, content encoding).
        """
        if connection_string is None:
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING", None)

        if blob_service_client is not None:
            service_client = blob_service_client
        elif connection_string is not None:
            service_client = BlobServiceClient.from_connection_string(
                conn_str=connection_string, credential=credential
            )
        elif account_url is not None:
            # Given an account_url, we can authenticate with an embedded SAS token, provided credential, an environment variable, or default credential.
            parsed = urlparse(account_url)
            if parsed.query or credential is not None:
                # Use passed credential or embedded SAS token.
                # TODO: when both are provided behavior is unclear to user.
                service_client = BlobServiceClient(account_url=account_url, credential=credential)
            elif (azure_application_credentials_file := os.getenv("AZURE_APPLICATION_CREDENTIALS")) is not None:
                service_client = _blob_service_client_from_file(azure_application_credentials_file)
            else:
                # EnvironmentCredential, ManagedIdentityCredential, AzureCliCredential
                msal_credential = DefaultAzureCredential(
                    exclude_powershell_credential = True,
                    exclude_visual_studio_code_credential = True,
                    exclude_shared_token_cache_credential = True,
                    exclude_interactive_browser_credential = True
                )
                service_client = BlobServiceClient(account_url=account_url, credential=msal_credential)
        else:
            # TODO, error type
            raise ValueError("Either connection_string or account_url must be specified.")

        super().__init__(blob_service_client=service_client, local_cache_dir=local_cache_dir, content_type_method=content_type_method)

    def _msal_credential_from_file(file_path: str) -> ClientSecretCredential:
        with open(file_path, "r") as f:
            credentials = json.loads(f.read())
        return ClientSecretCredential(
            tenant_id=credentials["tenant"],
            client_id=credentials["appId"],
            client_secret=credentials["password"]
        )


@register_path_class('hail-az')
class HailAzureBlobPath(AzureBlobPath):
    """
    Extending Path implementation to support hail-az:// scheme
    >>> CloudPath('hail-az://myaccount/mycontainer/tmp')
    HailAzureBlobPath('hail-az://myaccount/mycontainer/tmp')
    >>> CloudPath('https://myaccount.blob.core.windows.net/mycontainer/tmp')
    HailAzureBlobPath('hail-az://myaccount/mycontainer/tmp')
    """

    cloud_prefix: str = 'hail-az://'
    client: 'HailAzureBlobClient'

    def __init__(
        self,
        cloud_path: Union[str, CloudPath],
        client: Optional[HailAzureBlobClient] = None,
        token: Optional[str] = None,
    ):
        if isinstance(cloud_path, str):
            parsed = urlparse(cloud_path)
            m = re.match(
                r'(?P<account>[a-z0-9]+)(\.(?P<type>blob|dfs)(\.core\.windows\.net)?)?',
                parsed.netloc,
                flags=re.IGNORECASE,
            )
            if m is None:
                raise ValueError(f'Bad Azure path "{cloud_path}"')
            account = m.group('account')
            fstype = m.group('type') or 'blob'
            account_url = f'https://{account}.{fstype}.core.windows.net/'
            cloud_path = (
                f'{HailAzureBlobPath.cloud_prefix}{account}/'
                f'{parsed.path.lstrip("/")}'
            )
            if (
                client is None
                or parsed.query
                or token
                or client.service_client.account_name != account
            ):
                if token is not None:
                    token = '?' + token.lstrip('?')
                elif parsed.query:
                    token = '?' + parsed.query
                client = HailAzureBlobClient(account_url=account_url, credential=token)

        super().__init__(cloud_path, client=client)

    @classmethod
    def is_valid_cloudpath(
        cls, path: Union[str, CloudPath], raise_on_error=False
    ) -> bool:
        """
        Also allowing HTTP.
        """
        valid = bool(
            re.match(
                fr'({HailAzureBlobPath.cloud_prefix}|https://[a-z0-9]+\.(blob|dfs)\.core\.windows\.net)',
                str(path).lower(),
            )
        )

        if raise_on_error and not valid:
            raise InvalidPrefixError(
                f'{path} is not a valid path since it does not start with {cls.cloud_prefix} '
                f'or valid Azure https blob or dfs location.'
            )

        return valid

    @property
    def account(self) -> str:
        """
        Just the account part.
        """
        return self._no_prefix.split('/', 2)[0]

    @property
    def container(self) -> str:
        """
        Minus the account part.
        """
        return self._no_prefix.split('/', 2)[1]

    @property
    def blob(self) -> str:
        """
        No prefix, no account part.
        """
        return super().blob.split('/', 2)[2]
