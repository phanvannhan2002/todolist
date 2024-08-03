from flask import request, Blueprint
from flaskr.models.Workspace import _workspaceColl
from flaskr.models.Post import _postColl
from flaskr.models.Tag import _tagColl
from flaskr.models.User import _userColl
from flaskr.errors.bad_request import BadRequestError
from flaskr.errors.not_found import NotFoundError
from flaskr.errors.forbidden import ForbiddenError
from datetime import datetime
from flaskr.middlewares.auth import access_token_required, admin_only
from bson import ObjectId
import re
from werkzeug.security import generate_password_hash, check_password_hash

userBP = Blueprint("user", __name__, url_prefix="/api/v1/users")


@userBP.get("")
@access_token_required
@admin_only
def getAllUser(_):
    users = _userColl.find({}, {"hash_password": 0})

    return {"users": list(users)}


@userBP.post("")
@access_token_required
@admin_only
def createUser(_):
    data = request.json
    if not data:
        raise BadRequestError("Please provide data")

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

    if (
        not username
        or not email
        or not password
        or not re.match(r"^[\w\.-]+@[\w\.-]+$", email.strip())
        or not role
    ):
        raise BadRequestError("Invalid data")

    username = username.strip()
    email = email.strip()
    password = password.strip()

    if _userColl.find_one(
        {
            "$or": [
                {"username": username},
                {"email": email},
            ]
        }
    ):
        raise BadRequestError("User already exist")

    newUser = _userColl.insert_one(
        {
            "username": username,
            "email": email,
            "hash_password": generate_password_hash(password),
            "role": role,
            "created_at": datetime.now(),
        }
    )
    newUser = _userColl.find_one({"_id": newUser.inserted_id})

    return {
        "user": {
            "id": newUser["_id"],
            "username": newUser["username"],
            "email": newUser["email"],
            "role": newUser["role"],
            "created_at": newUser["created_at"],
        },
    }


@userBP.get("/<userId>")
@access_token_required
def getUser(requestUserId, userId):
    requestUser = _userColl.find_one({"_id": ObjectId(requestUserId)})
    
    if not requestUser or (requestUser["role"] != "admin" and str(requestUserId) != userId):
        raise ForbiddenError("Don't have permission")
    
    if requestUserId == userId:
        user = requestUser
    else:
        user = _userColl.find_one({"_id": ObjectId(userId)})

    if not user:
        raise NotFoundError("Id not found")
    
    print(user)

    return {
        "user": {
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "created_at": user["created_at"],
        }
    }


@userBP.put("/<userId>")
@access_token_required
@admin_only
def updateUser(requestUserId, userId):
    user = _userColl.find_one({"_id": ObjectId(userId)})
    
    if not user or (user["role"] == "admin"):
        raise ForbiddenError("Don't have permission")

    role = request.json.get("role")    
    if not role:
        raise BadRequestError("Role is empty!")
    
    updatedUser = _userColl.find_one_and_update({"_id": ObjectId(userId)}, {
        "$set": {
            "role": role,
        }
    }, return_document=True, projection={"hash_password" : 0})

    return {
        "user": updatedUser,
    }
    
# @userBP.put("/<userId>")
# @access_token_required
# def updateUser(requestUserId, userId):
#     requestUser = _userColl.find_one({"_id": ObjectId(requestUserId)})

#     if not requestUser or (requestUser["role"] != "admin" and str(requestUserId) != userId):
#         raise ForbiddenError("Don't have permission")



#     return {
#         "message": "updated successfully(user don't have any information updatable)"
#     }


@userBP.delete("/<userId>")
@access_token_required
@admin_only
def deleteUser(_, userId):
    user = _userColl.find_one({"_id": ObjectId(userId)})

    if not user:
        raise NotFoundError("Id not found")

    if user["role"] == "admin":
        raise BadRequestError("Can't delete admin")

    workspaces = _workspaceColl.find({"user_id": user["_id"]}, {"_id": 1})
    workspace_ids = [ObjectId(workspace["_id"]) for workspace in workspaces]

    posts = _postColl.find({"workspace_id": {"$in": workspace_ids}}, {"_id": 1})
    post_ids = [ObjectId(post["_id"]) for post in posts]

    _tagColl.delete_many({"post_id": {"$in": post_ids}})
    _postColl.delete_many({"_id": {"$in": post_ids}})
    _workspaceColl.delete_many({"_id": {"$in": workspace_ids}})
    _userColl.delete_one({"_id": user["_id"]})

    return {"message": "deleted successfully"}
