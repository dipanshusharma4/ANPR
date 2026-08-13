from fastapi import APIRouter, HTTPException, Depends, Body, Form, Request
from typing import Optional, Union
import json

from models.users import User
from config.db import db
from schemas.users import usersEntity, userEntity, AdminSignup
from bson import ObjectId
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from auth.auth import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/login")

# ----------------------------
# Admin auth routes (async) 
# ----------------------------

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/login")
@router.post("/admin/signup", tags=["Admin"])
async def signup(
    request: Request,
    admin: Optional[Union[AdminSignup, dict, str]] = Body(None),
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
):
    """Create an admin account.

    This handler accepts multiple request formats to be tolerant of different clients:
      - JSON body matching AdminSignup (preferred)
      - form fields `email` + `password` (application/x-www-form-urlencoded or multipart/form-data)
      - a form field `admin` that contains a JSON string (e.g. admin={"email":"..","password":".."})
      - raw JSON body even if Content-Type was omitted (we try request.json())

    Returns a simple success message on insertion.
    """

    # If `admin` arrived as a plain string (common when clients put JSON into a single form field),
    # try to decode it as JSON.
    if isinstance(admin, str):
        try:
            parsed = json.loads(admin)
            admin = AdminSignup(**parsed)
        except Exception:
            # if it fails, set admin to None so the normal resolution logic runs and returns 422.
            admin = None

    # If a dict was provided (FastAPI sometimes parses body into dict), coerce to the pydantic model
    if isinstance(admin, dict):
        try:
            admin = AdminSignup(**admin)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid admin object: {e}")

    # If admin model still None, attempt to construct from form fields
    if admin is None:
        if email is not None and password is not None:
            try:
                admin = AdminSignup(email=email, password=password)
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"Invalid form fields: {e}")
        else:
            # As a last attempt, try to parse raw JSON body (helps when Content-Type is missing/mis-set)
            try:
                body = await request.json()
            except Exception:
                raise HTTPException(status_code=422, detail="Invalid request body: expected JSON or form data")
            try:
                admin = AdminSignup(**body)
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"Invalid request body: {e}")

    # At this point `admin` should be an AdminSignup instance
    if not isinstance(admin, AdminSignup):
        raise HTTPException(status_code=422, detail="Invalid admin payload")

    # Check existing
    existing = await db.admins.find_one({"email": admin.email})
    if existing:
        raise HTTPException(status_code=400, detail="Admin already exists")

    # Hash password and store
    hashed = hash_password(admin.password)
    await db.admins.insert_one({"email": admin.email, "password": hashed})
    return {"msg": "Admin registered"}


@router.post("/admin/login",tags=["Admin"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    admin = await db.admins.find_one({"email": form_data.username})
    if not admin or not verify_password(form_data.password, admin["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": admin["email"]})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/admin/me",tags=["Admin"])
async def get_me(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    email = payload.get("sub")
    admin = await db.admins.find_one({"email": email})
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return {"email": admin["email"]}


#Backend trigger\
@router.post("/admin/backend_trigger", tags=["Admin"])
async def backend_trigger(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    email = payload.get("sub")
    admin = await db.admins.find_one({"email": email})
    
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return {"msg": "Backend process triggered"}

# ----------------------------
# User CRUD routes (async)
# ----------------------------

@router.get('/users',tags=["Users"])
async def find_all_users():
    users = db.users.find()
    return usersEntity(await users.to_list(length=100))


@router.get('/users/{id}',tags=["Users"])
async def find_one_user(id: str):
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")

    user = await db.users.find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return userEntity(user)


@router.post('/users',tags=["Users"])
async def create_user(user: User):
    new_user = user.dict()
    result = await db.users.insert_one(new_user)
    created_user = await db.users.find_one({"_id": result.inserted_id})
    return userEntity(created_user)


@router.put('/users/{id}',tags=["Users"])
async def update_user(id: str, user: User):
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")

    await db.users.update_one({"_id": oid}, {"$set": user.dict()})
    updated_user = await db.users.find_one({"_id": oid})
    return userEntity(updated_user)


@router.delete('/users/{id}',tags=["Users"])
async def delete_user(id: str):
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")

    deleted_user = await db.users.find_one_and_delete({"_id": oid})
    if not deleted_user:
        raise HTTPException(status_code=404, detail="User not found")
    return userEntity(deleted_user)


