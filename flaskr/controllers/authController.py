from flask import request, Blueprint
import jwt
import os
from werkzeug.security import generate_password_hash, check_password_hash
import bson
from flaskr.models.User import _userColl
from flaskr.errors.bad_request import BadRequestError
from flaskr.errors.not_found import NotFoundError
from flaskr.errors.unauthenicated import UnauthenticatedError
import re
from datetime import datetime, timezone, timedelta
from flaskr.middlewares.auth import access_token_required
import hashlib
import secrets
from flaskr.utils.email_helper import EmailSender

authBP = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@authBP.post("/login")
def login():
    data = request.json
    if not data:
        raise BadRequestError("Please provide data")

    email = data.get("email")
    password = data.get("password")

    if not email or not password or not re.match(r"^[\w\.-]+@[\w\.-]+$", email.strip()):
        raise BadRequestError("Invalid data")

    email = email.strip()
    password = password.strip()

    user = _userColl.find_one({"email": email})

    if user and check_password_hash(user["hash_password"], password):
        token = jwt.encode(
            {
                "user_id": str(user["_id"]),
                "exp": datetime.now(tz=timezone.utc)
                + timedelta(days=int(os.getenv("JWT_LIFETIME"))),
            },
            os.getenv("JWT_SECRET"),
            algorithm="HS256",
        )
        return {
            "user": {
                "id": user["_id"],
                "username": user["username"],
                "role": user["role"],
            },
            "access_token": token,
        }

    raise UnauthenticatedError("Invalid email or password")


@authBP.post("/register")
def register():
    data = request.json
    if not data:
        raise BadRequestError("Please provide data")

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if (
        not username
        or not email
        or not password
        or not re.match(r"^[\w\.-]+@[\w\.-]+$", email.strip())
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
            "role": "user",
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


@authBP.post("/forgot-password")
def forgotPassword():
    data = request.json

    user = None
    if data and data.get("email"):
        email = data.get("email").strip()
        if re.match(r"^[\w\.-]+@[\w\.-]+$", email):
            user = _userColl.find_one({"email": email})
    else:
        raise BadRequestError("Invalid data")

    if user:
        token = secrets.token_hex(16)
        expires_time = datetime.now() + timedelta(minutes=10)

        user["pwr_token"] = hashlib.sha256(token.encode()).hexdigest()
        user["pwr_expire"] = expires_time

        _userColl.replace_one({"_id": user["_id"]}, user)

        email_sender = EmailSender.get_instance()
        subject = "Khôi phục mật khẩu"
        recipients = [email]
        sender = "todolistpython1@gmail.com"
        body = (
            f"Mã khôi phục tài khoản của bạn là {token}. Có hiệu lực trong vòng 10 phút"
        )
        email_sender.send_email(subject, recipients, sender, body)
    else:
        raise NotFoundError("Email not found")

    return {"message": "token has sent to your email address"}


@authBP.post("/reset-password")
def resetPassword():
    data = request.json
    if not data:
        raise BadRequestError("Please provide data")

    email = data.get("email")
    token = data.get("token")
    password = data.get("password")

    if (
        not email
        or not token
        or not password
        or not re.match(r"^[\w\.-]+@[\w\.-]+$", email.strip())
    ):
        raise BadRequestError("Invalid data")

    email = email.strip()
    token = token.strip()
    password = password.strip()

    user = _userColl.find_one({"email": email})
    if user:
        hashed_token = user["pwr_token"]
        input_hashed_token = hashlib.sha256(token.encode()).hexdigest()

        if hashed_token != input_hashed_token:
            raise BadRequestError("Invalid token!")

        if datetime.now() > user["pwr_expire"]:
            raise BadRequestError("Token expired")

        hash_password = generate_password_hash(password)
        _userColl.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "hash_password": hash_password,
                    "pwr_token": "used",
                    "pwr_expire": datetime.now(),
                }
            },
        )
        return {"message": "Password has changed successfully"}
    else:
        raise NotFoundError("Email not found")
