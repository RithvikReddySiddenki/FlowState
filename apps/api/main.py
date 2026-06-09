import os

from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

# loads variables from apps/api/.env
load_dotenv()

# creates the actual FastAPI application
app = FastAPI()

# allows the frontend on localhost:3000 to talk to backend on localhost:8000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# allows FastAPI to store login session data in a signed browser cookie
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-secret-change-later"),
)

# Google OAuth setup
oauth = OAuth()

oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
    },
)

# currently like a test database for the project
# in format 1: {"id": 1, "company": ..., "role": ..., "current_status": ...}
applications = {}

# keeps track of the ID number that the next application should get
next_index = 1


# we create a class that inherits from BaseModel
# this specifies which information we need from the user
class CreateApplication(BaseModel):
    company: str = Field(min_length=1)
    role: str = Field(min_length=1)
    current_status: str = Field(min_length=1)


# this class makes it so not all fields are necessary when editing an application
class UpdateApplication(BaseModel):
    company: str | None = None
    role: str | None = None
    current_status: str | None = None


# creates the route for the home route: http://localhost:8000/
# this is a way to check if the backend is still alive
@app.get("/")
def read_root():
    return {"message": "FlowState API is running"}


# -------------------------
# Google OAuth routes
# -------------------------

# starts the Google login process
@app.get("/auth/google/login")
async def google_login(request: Request):
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not redirect_uri:
        return {"message": "GOOGLE_REDIRECT_URI is missing from .env"}
    return await oauth.google.authorize_redirect(request, redirect_uri)


# Google sends the user back here after login
@app.get("/auth/google/callback")
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")

    if not user_info:
        return {"message": "Could not get user info from Google"}

    # stores basic user info in the session cookie
    request.session["user"] = {
        "email": user_info["email"],
        "name": user_info.get("name"),
        "google_id": user_info["sub"],
    }

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend_url}/dashboard")


# lets the frontend check if the user is logged in
@app.get("/auth/me")
def auth_me(request: Request):
    user = request.session.get("user")
    if not user:
        return {
            "authenticated": False,
            "user": None,
        }
    return {
        "authenticated": True,
        "user": user,
    }


# logs the user out
@app.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out"}


# Application routes

# gets all applications
@app.get("/applications")
def get_applications():
    return list(applications.values())


# gets one specific application
@app.get("/applications/{application_id}")
def get_application(application_id: int):
    if application_id in applications:
        return applications[application_id]

    return {"message": "Application not found"}


# creates a new application
@app.post("/applications")
def create_application(application: CreateApplication):
    global next_index

    new_application = {
        "id": next_index,
        "company": application.company,
        "role": application.role,
        "current_status": application.current_status,
    }

    applications[next_index] = new_application
    next_index += 1

    return new_application


# edits an existing application
@app.patch("/applications/{application_id}")
def edit_application(application_id: int, updated_application: UpdateApplication):
    if application_id not in applications:
        return {"message": "Application not found"}

    if updated_application.company is not None:
        applications[application_id]["company"] = updated_application.company

    if updated_application.role is not None:
        applications[application_id]["role"] = updated_application.role

    if updated_application.current_status is not None:
        applications[application_id]["current_status"] = updated_application.current_status

    return applications[application_id]


# deletes an application
@app.delete("/applications/{application_id}")
def delete_application(application_id: int):
    if application_id not in applications:
        return {"message": "Application not found"}

    deleted_application = applications.pop(application_id)

    return {
        "message": "Application deleted",
        "deleted_application": deleted_application,
    }
