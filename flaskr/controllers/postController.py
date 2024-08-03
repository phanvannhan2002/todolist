from flask import request, Blueprint
from flaskr.errors.bad_request import BadRequestError
from flaskr.errors.forbidden import ForbiddenError

from flaskr.models.Post import _postColl
from flaskr.models.Workspace import _workspaceColl
from flaskr.models.Tag import _tagColl
from bson import ObjectId

from datetime import datetime
from flaskr.middlewares.auth import access_token_required


postBP = Blueprint("post", __name__, url_prefix="/api/v1/posts")


@postBP.post("")
@access_token_required
def createPost(requestUserId):
    data = request.json
    if not data:
        raise BadRequestError("Please provide data")

    workspaceId = ObjectId(data.get("workspaceId"))
    workspace = _workspaceColl.find_one({"_id": workspaceId})
    if not workspace:
        raise BadRequestError("Invalid data")

    if workspace["user_id"] != requestUserId:
        raise ForbiddenError("Permission denied!")

    post = {
        "workspace_id": workspaceId,
        "title": data.get("title"),
        "pos": data.get("pos"),
        "created_at": datetime.now(),
    }

    post_id = _postColl.insert_one(post).inserted_id
    new_post = _postColl.find_one({"_id": post_id})
    return {"post": new_post}


@postBP.get("")
@access_token_required
def getPosts(requestUserId):
    workspaceId = ObjectId(request.args.get("workspaceId"))

    workspace = _workspaceColl.find_one({"_id": workspaceId})

    if not workspace or workspace["user_id"] != requestUserId:
        raise ForbiddenError("Permission denied!")

    if request.args.get("includeTag"):
        pipeline = [
            {
                "$match": {
                    "workspace_id": workspaceId,
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
                }
            },
        ]
        posts = _postColl.aggregate(pipeline)
    else:
        posts = _postColl.find({"workspace_id": workspaceId})

    if not posts:
        raise BadRequestError("Invalid data")
    return {"posts": list(posts)}


@postBP.get("/<postId>")
@access_token_required
def getPost(requestUserId, postId):
    post = _postColl.find_one({"_id": ObjectId(postId)})

    if not post:
        raise BadRequestError("Invalid data")

    workspace = _workspaceColl.find_one({"_id": post["workspace_id"]})
    if workspace["user_id"] != requestUserId:
        raise ForbiddenError("Permission denied!")

    if request.args.get("includeTag"):
        tags = _tagColl.aggregate(
            [
                {
                    "$match": {
                        "post_id": post["_id"],
                    },
                },
                {
                    "$sort": {
                        "pos": 1,
                    }
                }
            ]
        )
        post["tags"] = list(tags)

    return {"post": post}


@postBP.patch("/<postId>")
@access_token_required
def updatePost(requestUserId, postId):
    data = request.json
    if not data:
        raise BadRequestError("Please provide data")

    post = _postColl.find_one({"_id": ObjectId(postId)})
    if not post:
        raise BadRequestError("Invalid data")

    workspace = _workspaceColl.find_one({"_id": post["workspace_id"]})
    if workspace["user_id"] != requestUserId:
        raise ForbiddenError("Permission denied!")

    requestData = {
        "title": data.get("title"),
        "pos": data.get("pos"),
    }
    
    updateTag = {k: v for k, v in requestData.items() if v is not None}

    updatedPost = _postColl.find_one_and_update(
        {"_id": ObjectId(postId)}, {"$set": updateTag}, return_document=True
    )
    return {"post": updatedPost}


@postBP.delete("/<postId>")
@access_token_required
def deletePost(requestUserId, postId):
    post = _postColl.find_one({"_id": ObjectId(postId)})
    if not post:
        raise BadRequestError("Invalid data")

    workspace = _workspaceColl.find_one({"_id": post["workspace_id"]})
    if workspace["user_id"] != requestUserId:
        raise ForbiddenError("Permission denied!")

    _postColl.delete_one({"_id": ObjectId(postId)})
    return {"status": "Deleted Successfully"}
