from pydantic import BaseModel, EmailStr ,Field, SecretStr
def userEntity(item) -> dict:
    return {
        "id": str(item.get("_id")),
        "name": item.get("name"),
        "email": item.get("email"),
        "password": item.get("password"),
        "post": item.get("post"),
    }


def usersEntity(entity) -> list:
    return [userEntity(item) for item in entity]


def serializeDict(a) -> dict:
    # convert ObjectId to string for _id and keep other fields
    return {"id": str(a.get("_id")), **{k: v for k, v in a.items() if k != "_id"}}


def serializeList(entity) -> list:
    return [serializeDict(a) for a in entity]



class AdminSignup(BaseModel):
    email: EmailStr
    password: str

class AdminLogin(BaseModel):
    email: EmailStr
    password: str
