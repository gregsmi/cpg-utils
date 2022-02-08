"""Convenience functions related to cloud infrastructure."""

import os
from typing import Optional
from google.auth import jwt
from google.cloud import secretmanager
import google.api_core.exceptions
import azure.core.exceptions
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

def get_cloud_setting() -> str:
    """Returns the cloud backend setting, based solely on environment variables
    
    Valid values are `gcp` (default) and `azure`."""

    # Default to gcp if no environment variable is set.
    if 'CPG_CLOUD' not in os.environ:
        return 'gcp'
    # Otherwise return azure if selected, then default to gcp.
    if os.environ['CPG_CLOUD'].lower() == 'azure':
        return 'azure'
    else:
        return 'gcp'


def email_from_id_token(id_token: str) -> str:
    """Decodes the ID token (JWT) to get the email address of the caller.

    See http://bit.ly/2YAIkzy for details.

    This function assumes that the token has been verified beforehand."""

    # Note, email and upn extracted from the access token are mutable and not always present in
    # Azure access tokens, depending on the nature of the account for which an access token is being generated.
    # See the following link for detail:
    #  - https://docs.microsoft.com/en-us/azure/active-directory/develop/active-directory-optional-claims

    if get_cloud_setting() == 'azure':
        decoded = jwt.decode(id_token, verify=False)
        return decoded['email'] if 'email' in decoded.keys() else decoded['upn']
    else:
        jwt.decode(id_token, verify=False)['email']


def read_secret(project_id: str, secret_name: str) -> Optional[str]:
    """Reads the latest version of a Cloud secret.

    Returns None if the secret doesn't exist."""

    if get_cloud_setting() == 'azure':
        return _read_secret_azure(keyvault_name=project_id, secret_name=secret_name)
    else:
        return _read_secret_gcp(project_id=project_id, secret_name=secret_name)


def _read_secret_azure(keyvault_name: str, secret_name: str) -> Optional[str]:
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=f"https://{keyvault_name}.vault.azure.net", credential=credential)

    try:
        return client.get_secret(secret_name).value
    except azure.core.exceptions.ResourceNotFoundError:
        # Fail gracefully if no secret of this name exists.
        return None
    except azure.core.exceptions.HttpResponseError:
        # Fail gracefully on other errors.
        return None


def _read_secret_gcp(project_id: str, secret_name: str) -> Optional[str]:
    secret_manager = secretmanager.SecretManagerServiceClient()
    secret_path = secret_manager.secret_path(project_id, secret_name)

    try:
        response = secret_manager.access_secret_version(
            request={'name': f'{secret_path}/versions/latest'}
        )
        return response.payload.data.decode('UTF-8')
    except google.api_core.exceptions.ClientError:
        # Fail gracefully if there's no secret version yet.
        return None
    except AttributeError:
        # Sometimes the google API fails when no version is present, with:
        #   File "{site-packages}/google/api_core/exceptions.py",
        #   line 532, in from_grpc_error if isinstance(rpc_exc, grpc.Call) or _is_informative_grpc_error(rpc_exc):
        #   AttributeError: 'NoneType' object has no attribute 'Call'
        return None


def write_secret(project_id: str, secret_name: str, secret_value: str) -> None:
    """Sets the new latest version of a Cloud secret."""

    if get_cloud_setting() == 'azure':
        _write_secret_azure(keyvault_name=project_id, secret_name=secret_name, secret_value=secret_value)
    else:
        _write_secret_gcp(project_id=project_id, secret_name=secret_name, secret_value=secret_value)


def _write_secret_azure(keyvault_name: str, secret_name: str, secret_value: str) -> None:
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=f"https://{keyvault_name}.vault.azure.net", credential=credential)

    # Set the secret value, this can raise HttpResponse error.
    new_secret = client.set_secret(
        name=secret_name, 
        value=secret_value.encode('UTF-8')
    )

    # Disable all previous versions.
    secret_versions = client.list_properties_of_secret_versions(name=secret_name)

    for version in secret_versions:
        if (version.enabled == True and version.version != new_secret.properties.version):
            client.update_secret_properties(name=version.name, version=version.version, enabled=False)


def _write_scret_gcp(project_id: str, secret_name: str, secret_value: str) -> None:
    secret_manager = secretmanager.SecretManagerServiceClient()
    secret_path = secret_manager.secret_path(project_id, secret_name)

    response = secret_manager.add_secret_version(
        request={
            'parent': secret_path,
            'payload': {'data': secret_value.encode('UTF-8')},
        }
    )

    # Disable all previous versions.
    for version in secret_manager.list_secret_versions(request={'parent': secret_path}):
        # Don't attempt to change the state of destroyed / already disabled secrets and
        # don't disable the latest version.
        if (
            version.state == secretmanager.SecretVersion.State.ENABLED
            and version.name != response.name
        ):
            secret_manager.disable_secret_version(request={'name': version.name})
