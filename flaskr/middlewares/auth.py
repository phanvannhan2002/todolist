from functools import wraps
import jwt
from flask import request
import os
from bson import ObjectId
from flaskr.errors.forbidden import ForbiddenError
from flaskr.errors.unauthenicated import UnauthenticatedError
from flaskr.models.User import _userColl


def access_token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            try:
                token = request.headers["Authorization"].split(" ")[1]
            except:
                raise UnauthenticatedError("Invalid Authentication Header!")
        if not token:
            raise UnauthenticatedError("Authentication Token is missing!")

        data = None
        requestUserId = None
        try:
            data = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])
            requestUserId = data["user_id"]
        except :
            raise UnauthenticatedError("Signature has expired or Invalid Authentication token!")

        if requestUserId is None:
            raise UnauthenticatedError("Invalid Authentication token!")

        return f(ObjectId(requestUserId), *args, **kwargs)

    return decorated


def admin_only(f):
    @wraps(f)
    def decorated(requestUserId, *args, **kwargs):
        isAdmin = (
            _userColl.find_one({"_id": requestUserId}, {"role": 1})["role"]
            == "admin"
        )

        if not isAdmin:
            raise ForbiddenError("Must be admin!")

        return f(requestUserId, *args, **kwargs)

    return decorated
