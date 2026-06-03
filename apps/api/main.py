from fastapi import FastAPI
# creates the actual FastAPI application
app = FastAPI()

# creates the route (when someone visits the home route (http://localhost:8000/))
# .get means the route responds to a GET request (use when we want to retrieve data)
@app.get("/")
# funtion that runs when someone visits / (home)
def read_root():
    return {"message": "FlowState API is running"}