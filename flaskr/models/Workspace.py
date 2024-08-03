from flaskr.db import db

database = db.getDB()

_workspaceColl = None

try:
    _workspaceColl = database.create_collection("workspaces")
except:
    _workspaceColl = database.get_collection("workspaces")

workspace_validator = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["user_id", "title", "created_at"],
        "properties": {
            "user_id": {
                "bsonType": "objectId",
                "description": "must be an objectid and is required",
            },
            "title": {
                "bsonType": "string",
                "description": "must be a string and is required",
            },
            "created_at": {
                "bsonType": "date",
                "description": "must be a date and is required",
            },
        },
    }
}

database.command("collMod", "workspaces", validator=workspace_validator)
