from fastapi import FastAPI
import main
app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/pr/{pr_no}")
def check_by_pr(pr_no: str):
    return main.search_by_pr(pr_no)

@app.get("/version/{version}")
def check_by_version(version: str):
    return main.search_by_version(version)

@app.get("/keyword/{key}")
def check_by_keyword(key: str):
    return main.search_by_keyword(key)

@app.get("/tibug/{key}")
def get_in_tibug(key: str):
    return main.search_in_tibug_by_keyword(key)

