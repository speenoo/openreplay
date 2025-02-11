import logging
import uuid
from typing import Optional

from decouple import config
from fastapi import Depends, HTTPException, Header, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import schemas
from chalicelib.core import users, roles
from routers.base import get_routers

logger = logging.getLogger(__name__)

"""
Models:

USER

schemas         -> hardcoded
id              -> from db
userName        -> email, comes from Okta
name:
    givenName   -> from Okta
    middleName  -> from Okta
    familyName  -> from Okta
emails:                  
    primary     -> from Okta
    value       -> from Okta
    type        -> from Okta
displayName     -> from Okta (potentially, givenName+" "+familyName)
locale          -> from Okta (e.g. en-US)
externalId      -> from Okta
active          -> ! doesn't exist, but represent deleted users
groups          -> users: {"display": group.displayName, "value": group.id}
meta            -> hardcoded

    
GROUP

schemas         -> hardcoded
id              -> from db
meta            -> hardcoded
displayName     -> from db
members         -> users: {"display": user.userName, "value": user.id}


"""

class Name(BaseModel):
    givenName: str
    familyName: str

class Email(BaseModel):
    primary: bool
    value: str
    type: str

class UserRequest(BaseModel):
    schemas: list[str]
    userName: str
    name: Name
    emails: list[Email] # ignore for now
    displayName: str
    locale: str
    externalId: str
    groups: list[dict]
    password: str # ignore
    active: bool


class UserResponse(BaseModel):
    schemas: list[str]
    id: str
    userName: str
    name: Name
    emails: list[Email] # ignore for now
    displayName: str
    locale: str
    externalId: str
    active: bool
    groups: list[dict]
    meta: dict = Field(default={"resourceType": "User"})

class PatchUserRequest(BaseModel):
    schemas: list[str]
    Operations: list[dict]


# Authentication Dependency
def auth_required(authorization: str = Header(..., alias="Authorization")):
    """Dependency to check Authorization header."""
    token = authorization.replace("Bearer ", "")
    if token != config("OCTA_TOKEN"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    return token


public_app, app, app_apikey = get_routers(prefix="/sso/scim/v2")

@public_app.get("/Users", dependencies=[Depends(auth_required)])
async def get_users(
    start_index: int = Query(1, alias="startIndex"),
    count: Optional[int] = Query(1, alias="count"),
    filter: Optional[str] = Query(None, alias="filter"),
):
    """Get SCIM Users"""
    if filter:
        single_filter = filter.split(" ")
        filter_value = single_filter[2].strip('"')

        filtered_users = users.get_by_email_with_uuid(filter_value)
        filtered_users = [filtered_users] if filtered_users else []
    else:
        filtered_users = users.get_users_paginated(start_index, count)
    
    serialized_users = []
    for user in filtered_users:
        logger.info(user)
        serialized_users.append(
            UserResponse(
                schemas = ["urn:ietf:params:scim:schemas:core:2.0:User"],
                id = user["data"]["userId"],
                userName = user["email"],
                name = Name.model_validate(user["data"]["name"]),
                emails = [Email.model_validate(user["data"]["emails"])],
                displayName = user["name"],
                locale = user["data"]["locale"],
                externalId = user["internalId"],
                active = True, # ignore for now, since, can't insert actual timestamp
                groups = [], # ignore
            ).model_dump(mode='json')
        )
    return JSONResponse(
        status_code=200,
        content={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": len(serialized_users),
            "startIndex": start_index,
            "itemsPerPage": len(serialized_users),
            "Resources": serialized_users,
        },
    )

@public_app.get("/Users/{user_id}", dependencies=[Depends(auth_required)])
def get_user(user_id: str):
    """Get SCIM User"""
    user = users.get_by_uuid(user_id, 1)
    if not user:
        return JSONResponse(
            status_code=404,
            content={
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                "detail": "User not found",
                "status": 404,
            }
        )

    res = UserResponse(
        schemas = ["urn:ietf:params:scim:schemas:core:2.0:User"],
        id = user["data"]["userId"],
        userName = user["email"],
        name = Name.model_validate(user["data"]["name"]),
        emails = [Email.model_validate(user["data"]["emails"])],
        displayName = user["name"],
        locale = user["data"]["locale"],
        externalId = user["internalId"],
        active = True, # ignore for now, since, can't insert actual timestamp
        groups = [], # ignore
    )
    return JSONResponse(status_code=201, content=res.model_dump(mode='json'))


@public_app.post("/Users", dependencies=[Depends(auth_required)])
async def create_user(r: UserRequest):
    """Create SCIM User"""
    existing_user = users.get_by_email_only(r.userName)
    
    if existing_user:
        return JSONResponse(
            status_code = 409,
            content = {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                "detail": "User already exists in the database.",
                "status": 409,
            }
        )
    else:
        try:
            # Need to handle groups later, for now ignore them
            user = users.create_scim_user(tenant_id=1, user_uuid=uuid.uuid4().hex, username=r.emails[0].value, admin=False,
                                   display_name=r.displayName, full_name=r.name.model_dump(mode='json'), emails=r.emails[0].model_dump(mode='json'),
                                   origin="okta", locale=r.locale, role_id=2, internal_id=r.externalId)
            res = UserResponse(
                schemas = ["urn:ietf:params:scim:schemas:core:2.0:User"],
                id = user["data"]["userId"], # Transformed to camel case
                userName = r.userName,
                name = r.name,
                emails = r.emails,
                displayName = r.displayName,
                locale = r.locale,
                externalId = r.externalId,
                active = r.active, # ignore for now, since, can't insert actual timestamp
                groups = [], # ignore
            )
            return JSONResponse(status_code=201, content=res.model_dump(mode='json'))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        

@public_app.put("/Users/{user_id}", dependencies=[Depends(auth_required)]) # insert your header later
def update_user(user_id: str, r: UserRequest):
    user = users.get_by_uuid(user_id, 1)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changes = r.model_dump(mode='json', exclude={"schemas", "emails", "name", "locale", "groups", "password", "active"}) # some of these should be added later if necessary
    nested_changes = r.model_dump(mode='json', include={"name", "emails"})
    logger.info(nested_changes)
    mapping = {"userName": "email", "displayName": "name", "externalId": "internal_id"} # mapping between scim schema field names and local database model, can be done as config?
    for k, v in mapping.items():
        if k in changes:
            changes[v] = changes.pop(k)
    changes["data"] = {}
    for k, v in nested_changes.items():
        value_to_insert = v[0] if k == "emails" else v
        changes["data"][k] = value_to_insert
    logger.info(changes)
    try:
        # Need to handle groups later, for now ignore them
        users.update(1, user["userId"], changes)
        logger.info("test")
        res = UserResponse(
            schemas = ["urn:ietf:params:scim:schemas:core:2.0:User"],
            id = user["data"]["userId"],
            userName = r.userName,
            name = r.name,
            emails = r.emails,
            displayName = r.displayName,
            locale = r.locale,
            externalId = r.externalId,
            active = r.active, # ignore for now, since, can't insert actual timestamp
            groups = [], # ignore
        )
        
        return JSONResponse(status_code=201, content=res.model_dump(mode='json'))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@public_app.patch("/Users/{user_id}", dependencies=[Depends(auth_required)])
def deactivate_user(user_id: str, r: PatchUserRequest):
    active = r.model_dump(mode='json')["Operations"][0]["value"]["active"]
    logger.info(active)
    if active:
        raise HTTPException(status_code=404, detail="Activating user is not supported")
    user = users.get_by_uuid(user_id, 1)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(user)
    users.delete_member_as_admin(1, user["userId"])

    return Response(status_code=204, content="")

# @app.delete("/Users/{user_id}", dependencies=[Depends(auth_required)])
@public_app.delete("/Users/{user_uuid}", dependencies=[Depends(auth_required)])
def delete_user(user_uuid: str):
    user = users.get_by_uuid(user_uuid, 1)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    users.__hard_delete_user_uuid(user_uuid)
    return Response(status_code=204, content="")


"""
Group endpoints

Potential issues:
1. Every user can be assigned only to single role
2. Deleting the group might be constrained by existing users linked to the role, 
   since those can't be left orphans
3. 

"""

class GroupRequest(BaseModel):
    schemas: list[str] = Field(default=["urn:ietf:params:scim:schemas:core:2.0:Group"])
    displayName: str
    members: list

class GroupResponse(BaseModel):
    schemas: list[str]
    id: int
    meta: dict = Field(default={"resourceType": "Group"})
    displayName: str
    members: list

@public_app.get("/Groups", dependencies=[Depends(auth_required)])
def get_groups(): # Might need to add query params later
    groups = roles.get_roles(1)
    res = []
    for group in groups:
        res.append(GroupResponse(
            schemas=["urn:ietf:params:scim:schemas:core:2.0:Group"],
            id=group["roleId"],
            displayName=group["name"],
            members=[], # add later
    ).model_dump(mode='json'))
    return JSONResponse(
        status_code=200,
        content=res
    )

@public_app.get("/Groups/{group_id}", dependencies=[Depends(auth_required)])
def get_group(group_id: str):
    group = roles.get_role(1, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    return JSONResponse(
        status_code=200,
        content=GroupResponse(
            schemas=["urn:ietf:params:scim:schemas:core:2.0:Group"],
            id=group["role_id"],
            displayName=group["name"],
            members=[], # add later
    ))

# @app.post("/scim/v2/Groups")
@app.post("/scim/v2/Groups", dependencies=[Depends(auth_required)])
def create_group(r: GroupRequest):
    try:
        data = schemas.RolePayloadSchema(name=r.displayName, permissions=[schemas.Permissions.SESSION_REPLAY])
        role = roles.create_as_admin(1, data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(
        status_code=200,
        content=GroupResponse(
            schemas=["urn:ietf:params:scim:schemas:core:2.0:Group"],
            id=role["role_id"],
            displayName=role["name"],
            members=[], # add later
    ))


@public_app.put("/Groups/{group_id}", dependencies=[Depends(auth_required)])
def update_group(group_id: str, r: GroupRequest):
    group = roles.get_role(1, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return JSONResponse(status_code=200, detail="")
    # for member in group_data.members:
    #     user = db.query(User).filter(User.id == member["value"]).first()
    #     if user:
    #         group.users.append(user)
    
    # db.commit()
    # db.refresh(group)
    # return group

@public_app.delete("/scim/v2/Groups/{group_id}", dependencies=[Depends(auth_required)])
# @app.delete("/scim/v2/Groups/{group_id}", dependencies=[Depends(auth_required)])
def delete_group(group_id: str):
    group = roles.get_role(1, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return JSONResponse(status_code=200, detail="")    
    # group = db.query(Group).filter(Group.id == group_id).first()
    # if not group:
    #     raise HTTPException(status_code=404, detail="Group not found")
    
    # db.delete(group)
    # db.commit()
    # return "", 204