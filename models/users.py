from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
    password: str
    post: str
    

def admin_helper(admin) -> dict:
    return {
        "id": str(admin["_id"]),
        "email": admin["email"]
    }
