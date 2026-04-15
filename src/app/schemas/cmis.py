"""CMIS 1.1 Browser Binding Pydantic models."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class CmisObjectResponse(BaseModel):
    """A single CMIS object in succinct format."""

    succinctProperties: dict[str, Any]
    propertiesExtension: dict[str, Any] | None = None
    allowableActions: dict[str, bool] | None = None

    model_config = ConfigDict(populate_by_name=True)


class CmisObjectListResponse(BaseModel):
    """List of CMIS objects (getChildren, query results)."""

    objects: list[CmisObjectResponse]
    hasMoreItems: bool = False
    numItems: int = 0


class CmisRepositoryInfo(BaseModel):
    """CMIS repository info returned at GET /cmis/browser."""

    repositoryId: str
    repositoryName: str
    repositoryDescription: str
    vendorName: str
    productName: str
    productVersion: str
    rootFolderId: str
    cmisVersionSupported: str
    capabilities: dict[str, Any]


class CmisTypeDefinition(BaseModel):
    """CMIS type definition."""

    id: str
    localName: str
    displayName: str
    queryName: str
    baseId: str
    propertyDefinitions: dict[str, dict[str, Any]]
