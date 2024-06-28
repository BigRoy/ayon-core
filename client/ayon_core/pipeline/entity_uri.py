from typing import Optional, Union
from urllib.parse import urlparse, parse_qs

from ayon_api import (
    get_folder_by_path,
    get_product_by_name,
    get_representation_by_name,
    get_hero_version_by_product_id,
    get_version_by_name,
    get_last_version_by_product_id
)
from ayon_core.pipeline import get_representation_path


def parse_ayon_entity_uri(uri: str) -> Optional[dict]:
    """Parse AYON entity URI into individual components.

    URI specification:
        ayon+entity://{project}/{folder}?product={product}
            &version={version}
            &representation={representation}
    URI example:
        ayon+entity://test/hero?product=modelMain&version=2&representation=usd

    However - if the netloc is `ayon://` it will by default also resolve as
    `ayon+entity://` on AYON server, thus we need to support both. The shorter
    `ayon://` is preferred for user readability.

    Example:
    >>> parse_ayon_entity_uri(
    >>>     "ayon://test/char/villain?product=modelMain&version=2&representation=usd"  # noqa: E501
    >>> )
    {'project': 'test', 'folderPath': '/char/villain',
     'product': 'modelMain', 'version': 1,
     'representation': 'usd'}
    >>> parse_ayon_entity_uri(
    >>>     "ayon+entity://project/folder?product=renderMain&version=3&representation=exr"  # noqa: E501
    >>> )
    {'project': 'project', 'folderPath': '/folder',
     'product': 'renderMain', 'version': 3,
     'representation': 'exr'}

    Returns:
        dict[str, Union[str, int]]: The individual key with their values as
            found in the ayon entity URI.

    """

    if not (uri.startswith("ayon+entity://") or uri.startswith("ayon://")):
        return {}

    parsed = urlparse(uri)
    if parsed.scheme not in {"ayon+entity", "ayon"}:
        return {}

    result = {
        "project": parsed.netloc,
        "folderPath": "/" + parsed.path.strip("/")
    }
    query = parse_qs(parsed.query)
    for key in ["product", "version", "representation"]:
        if key in query:
            result[key] = query[key][0]

    # Convert version to integer if it is a digit
    version = result.get("version")
    if version is not None and version.isdigit():
        result["version"] = int(version)

    return result


def construct_ayon_entity_uri(
        project_name: str,
        folder_path: str,
        product: str,
        version: Union[int, str],
        representation_name: str
) -> str:
    """Construct AYON entity URI from its components

    Returns:
        str: AYON Entity URI to query entity path.
    """
    if version < 0:
        version = "hero"
    if not (isinstance(version, int) or version in {"latest", "hero"}):
        raise ValueError(
            "Version must either be integer, 'latest' or 'hero'. "
            "Got: {}".format(version)
        )
    return (
        "ayon://{project}/{folder_path}?product={product}&version={version}"
        "&representation={representation}".format(
            project=project_name,
            folder_path=folder_path,
            product=product,
            version=version,
            representation=representation_name
        )
    )


def get_representation_by_names(
        project_name: str,
        folder_path: str,
        product_name: str,
        version_name: Union[int, str],
        representation_name: str,
) -> Optional[dict]:
    """Get representation entity for asset and subset.

    If version_name is "hero" then return the hero version
    If version_name is "latest" then return the latest version
    Otherwise use version_name as the exact integer version name.

    """

    if isinstance(folder_path, dict) and "name" in folder_path:
        # Allow explicitly passing asset document
        folder_entity = folder_path
    else:
        folder_entity = get_folder_by_path(project_name,
                                           folder_path,
                                           fields=["id"])
    if not folder_entity:
        return

    if isinstance(product_name, dict) and "name" in product_name:
        # Allow explicitly passing subset document
        product_entity = product_name
    else:
        product_entity = get_product_by_name(project_name,
                                             product_name,
                                             folder_id=folder_entity["id"],
                                             fields=["id"])
    if not product_entity:
        return

    if version_name == "hero":
        version_entity = get_hero_version_by_product_id(
            project_name,
            product_id=product_entity["id"])
    elif version_name == "latest":
        version_entity = get_last_version_by_product_id(
            project_name,
            product_id=product_entity["id"])
    else:
        version_entity = get_version_by_name(project_name,
                                             version_name,
                                             product_id=product_entity["id"])
    if not version_entity:
        return

    return get_representation_by_name(project_name,
                                      representation_name,
                                      version_id=version_entity["id"])


def get_representation_path_by_names(
        project_name: str,
        folder_path: str,
        product_name: str,
        version_name: str,
        representation_name: str) -> Optional[str]:
    """Get (latest) filepath for representation for folder and product.

    See `get_representation_by_names` for more details.

    Returns:
        str: The representation path if the representation exists.

    """
    representation = get_representation_by_names(
        project_name,
        folder_path,
        product_name,
        version_name,
        representation_name
    )
    if representation:
        path = get_representation_path(representation)
        return path.replace("\\", "/")
