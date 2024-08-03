from flaskr.db import db

database = db.getDB()

_tagColl = None

try:
    _tagColl = database.create_collection("tags")
except:
    _tagColl = database.get_collection("tags")

tag_validator = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["post_id", "title", "category", "body", "status", "deadline", "pos", "created_at"],
        "properties": {
            "post_id": {
                "bsonType": "objectId",
                "description": "must be an objectid and is required",
            },
            "title": {
                "bsonType": "string",
                "description": "must be a string and is required",
            },
            "category": {
                "bsonType": "string",
                "description": "must be a string and is required",
            },
            "body": {
                "bsonType": "string",
                "description": "must be a string and is required",
            },
            "status": {
                "enum": ["on the way", "completed", "is over"],
                "description": "can only be one of [on the way], [completed] or [is over] and is required",
            },
            "deadline": {
                "bsonType": "date",
                "description": "must be a date and is required",
            },
            "pos": {
                "bsonType": "double",
                "description": "must be a double and is required",
            },
            "created_at": {
                "bsonType": "date",
                "description": "must be a date and is required",
            },
        },
    }
}

database.command("collMod", "tags", validator=tag_validator)
