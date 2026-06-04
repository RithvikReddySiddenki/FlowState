from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
# creates the actual FastAPI application
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# currently like a test database for the project
# in format 1: {"id": 1, "company": ..., "role": ..., "current_status":, ...}
applications = {}
# keeps track of the ID number that the next application should get
next_index = 1 

# we create a class that inherits form BaseModel
# we need to specifiy which information we need from the User
class CreateApplication(BaseModel):
    company: str = Field(min_length=1)
    role: str = Field(min_length=1)
    current_status: str = Field(min_length=1)

# we create a class to make it where not all fields are necessary so we can make edits to jsut one field if needed
class UpdateApplication(BaseModel):
    company: str | None = None
    role: str | None = None
    current_status: str | None = None

# creates the route (when someone visits the home route (http://localhost:8000/))
# .get means the route responds to a GET request (use when we want to retrieve data)
@app.get("/")
# funtion that runs when someone visits /
# this is a way to check if the backend is still alive
def read_root():
    return {"message": "FlowState API is running"}

# creates route for /applications is a way to get all the applications from the database for this user
@app.get("/applications")
def get_applications():
    return list(applications.values())

# creates the route to be able to get a speicific application and not all the applications
@app.get("/applications/{application_id}")
def get_application(application_id: int):
    if application_id in applications:
        return applications[application_id]
    return {"message": "Application not found"}


@app.post("/applications")
def create_application(application: CreateApplication):
    global next_index
    new_application = {"id" : next_index, "company": application.company, "role": application.role, "current_status": application.current_status }
    applications[next_index] = new_application
    next_index += 1
    return new_application

# patch create a path to be able to edit an application
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

# delete allow us to delete an application
@app.delete("/applications/{application_id}")
def delete_application(application_id: int):
    if application_id not in applications:
        return {"message": "Application not found"}
    deleted_application = applications.pop(application_id)
    return {
        "message": "Application deleted",
        "deleted_application": deleted_application
    }





