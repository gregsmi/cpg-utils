"""
Extend cloudpathlib Azure implementation to support hail-az:// scheme.
Inspired by https://github.com/drivendataorg/cloudpathlib/issues/157
"""

import re
import os
import json
import logging
from typing import Union, Optional, Any, Callable
from urllib.parse import urlparse
import mimetypes
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.storage.blob import BlobServiceClient
#import azure.storage.blob
from cloudpathlib import AzureBlobClient, AzureBlobPath
from cloudpathlib.client import register_client_class
from cloudpathlib.cloudpath import register_path_class, CloudPath
from cloudpathlib.exceptions import InvalidPrefixError

# TODO pretty heavy handed
logging.getLogger('azure').setLevel(logging.WARN)
logging.getLogger('msal').setLevel(logging.WARN)
logging.getLogger('urllib3').setLevel(logging.WARN)

@register_client_class('hail-az')
class HailAzureBlobClient(AzureBlobClient):

    _cache_tmp_dir = None # avoids pytest warning

    def __init__(
        self,
        account_url: str,
        local_cache_dir: Optional[Union[str, os.PathLike]] = None,
        content_type_method: Optional[Callable] = mimetypes.guess_type,
    ):
        """Class constructor. Sets up a [`BlobServiceClient`](
        https://docs.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.blobserviceclient?view=azure-python).
        Supports the following authentication methods, specific to Hail Batch.
        - Implicit instantiation of a [`DefaultAzureCredential`](https://learn.microsoft.com/en-us/dotnet/api/azure.identity.defaultazurecredential?view=azure-dotnet-preview)
        - Environment variable `"AZURE_APPLICATION_CREDENTIALS"` containing a path to a JSON file that in turn contains three fields: 
        "tenant", "appId", and "password".
        - Account URL via `account_url`, authenticated with an embedded SAS token. In all cases an Account URL is required, and if a SAS token is provided, it will be used for Authentication.
        If multiple methods are used, priority order is reverse of list above (later in list takes
        priority).
        Args:
            account_url (str): The URL to the blob storage account, optionally
                authenticated with a SAS token. See documentation for [`BlobServiceClient`](
                https://docs.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.blobserviceclient?view=azure-python).
            local_cache_dir (Optional[Union[str, os.PathLike]]): Path to directory to use as cache
                for downloaded files. If None, will use a temporary directory.
            content_type_method (Optional[Callable]): Function to call to guess media type (mimetype) when
                writing a file to the cloud. Defaults to `mimetypes.guess_type`. Must return a tuple (content type, content encoding).
        """
        if account_url is None:
            raise ValueError("account_url must be specified")

        parsed = urlparse(account_url)
        if bool(parsed.query):
            # Use passed embedded SAS token
            service_client = BlobServiceClient(account_url=account_url)
        elif (azure_application_credentials_file := os.getenv("AZURE_APPLICATION_CREDENTIALS")) is not None:
            msal_credential = self._msal_credential_from_file(azure_application_credentials_file)
            service_client = BlobServiceClient(account_url=account_url, credential=msal_credential)
        else:
            # EnvironmentCredential, ManagedIdentityCredential, AzureCliCredential
            msal_credential = DefaultAzureCredential(
                exclude_powershell_credential = True,
                exclude_visual_studio_code_credential = True,
                exclude_shared_token_cache_credential = True,
                exclude_interactive_browser_credential = True
            )
            service_client = BlobServiceClient(account_url=account_url, credential=msal_credential)

        super().__init__(blob_service_client=service_client, local_cache_dir=local_cache_dir, content_type_method=content_type_method)

    def _msal_credential_from_file(self, file_path: str) -> ClientSecretCredential:
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
    Extending Path implementation to support hail-az:// and https:// schemes
    >>> CloudPath('hail-az://myaccount/mycontainer/tmp')
    HailAzureBlobPath('hail-az://myaccount/mycontainer/tmp')
    >>> CloudPath('https://myaccount.blob.core.windows.net/mycontainer/tmp')
    HailAzureBlobPath('hail-az://myaccount/mycontainer/tmp')
    """

    cloud_prefix: str = 'hail-az://'
    client: 'HailAzureBlobClient'
    _handle = None # avoids pytest warning

    def __init__(
        self,
        cloud_path: Union[str, CloudPath],
        client: Optional[HailAzureBlobClient] = None,
    ):
        if isinstance(cloud_path, str):
            parsed = urlparse(cloud_path)
            m = re.match(
                r'(?P<account>[a-z0-9]+)(\.(?P<type>blob|dfs)(\.core\.windows\.net)?)?',
                parsed.netloc,
                flags=re.IGNORECASE,
            )
            if m is None or not self.is_valid_cloudpath(cloud_path):
                raise ValueError(f'Bad Azure path "{cloud_path}"')
            account = m.group('account')
            fstype = m.group('type') or 'blob'
            account_url = f'https://{account}.{fstype}.core.windows.net/'
            cloud_path = (
                f'{HailAzureBlobPath.cloud_prefix}{account}/'
                f'{parsed.path.lstrip("/")}'
            )
            if client is None:
                if parsed.query:
                    account_url = account_url + "?" + parsed.query
                client = HailAzureBlobClient(account_url=account_url)

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
                fr'({HailAzureBlobPath.cloud_prefix}[a-z0-9]+|https://[a-z0-9]+\.(blob|dfs)\.core\.windows\.net)/[a-z0-9]+',
                str(path).lower(),
            )
        )
#                fr'({HailAzureBlobPath.cloud_prefix}|https://[a-z0-9]+\.(blob|dfs)\.core\.windows\.net)/',

        if raise_on_error and not valid:
            raise InvalidPrefixError(
                f'{path} is not a valid path since it does not start with {cls.cloud_prefix} '
                f'or valid Azure https blob or dfs location.'
            )

        return valid

    @property
    def drive(self) -> str:
        return f"{self.account}/{self.container}"

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
        parts = self._no_prefix.split('/', 2)
        return parts[2] if len(parts) == 3 else None
