from flask import request, Blueprint
from flaskr.models.Workspace import _workspaceColl
from flaskr.models.Post import _postColl
from flaskr.models.Tag import _tagColl
from flaskr.errors.bad_request import BadRequestError
from flaskr.errors.not_found import NotFoundError
from flaskr.errors.forbidden import ForbiddenError
from datetime import datetime
from flaskr.middlewares.auth import access_token_required
from bson import ObjectId

wsBP = Blueprint("ws", __name__, url_prefix="/api/v1/workspaces")


@wsBP.get("")
@access_token_required
def getAllWorkspaces(requestUserId):
    wss = _workspaceColl.find({"user_id": requestUserId}, {"user_id": 0})

    return {"workspaces": list(wss)}


@wsBP.post("")
@access_token_required
def createWorkspace(requestUserId):
    data = request.json

    if not data or not data.get("title"):
        raise BadRequestError("Please provide data")

    ws_title = data.get("title").strip()

    if not ws_title:
        raise BadRequestError("Title is blank")

    ws = {
        "user_id": requestUserId,
        "title": ws_title,
        "created_at": datetime.now(),
    }

    ws_id = _workspaceColl.insert_one(ws).inserted_id

    new_ws = _workspaceColl.find_one({"_id": ws_id})

    return {"workspace": new_ws}


@wsBP.get("/<workspaceId>")
@access_token_required
def getWorkspace(requestUserId, workspaceId):
    ws = _workspaceColl.find_one({"_id": ObjectId(workspaceId)})

    if not ws:
        raise BadRequestError("Workspace is not exist")

    if ws["user_id"] != requestUserId:
        raise ForbiddenError("Don't have permission")

    include = request.args.get("include")
    if include:
        pipeline = [
            {
                "$match": {
                    "workspace_id": ObjectId(workspaceId),
                }
            },
            {
                "$lookup": {
                    "from": "tags",
                    "let": {
                        "post_id": "$_id",
                    },
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$$post_id", "$post_id"]}}},
                        {"$sort": {"pos": 1}},
                    ],
                    "as": "tags",
                },
            },
            {
                "$sort": {
                    "pos": 1,
                },
            },
        ]
        posts = _postColl.aggregate(pipeline)
        ws["posts"] = list(posts)

    return ws


@wsBP.put("/<workspaceId>")
@access_token_required
def updateWorkspace(requestUserId, workspaceId):
    ws = _workspaceColl.find_one({"_id": ObjectId(workspaceId)})

    if not ws:
        raise NotFoundError("Id not found")
    if ws["user_id"] != requestUserId:
        raise ForbiddenError("Don't have permission")

    data = request.json
    if not data or not data.get("title"):
        raise BadRequestError("Please provide data")

    ws_title = data.get("title").strip()
    if not ws_title:
        raise BadRequestError("Title is blank")

    ws = _workspaceColl.find_one_and_update(
        {
            "_id": ObjectId(workspaceId),
        },
        {"$set": {"title": ws_title}},
        return_document=True,
    )

    return ws


@wsBP.delete("/<workspaceId>")
@access_token_required
def deleteWorkspace(requestUserId, workspaceId):
    ws = _workspaceColl.find_one({"_id": ObjectId(workspaceId)})

    if not ws:
        raise NotFoundError("Id not found")
    if ws["user_id"] != requestUserId:
        raise ForbiddenError("Don't have permission")

    posts = _postColl.find({"workspace_id": ObjectId(workspaceId)}, {"_id": 1})
    post_ids = [ObjectId(post["_id"]) for post in posts]

    _tagColl.delete_many({"post_id": {"$in": post_ids}})
    _postColl.delete_many({"_id": {"$in": post_ids}})
    _workspaceColl.delete_one({"_id": ObjectId(workspaceId)})

    return {"message": "deleted successfully"}
