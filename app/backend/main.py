import uuid
from uuid import UUID
from datetime import datetime
from fastapi import FastAPI, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from pydantic import BaseModel

from app.backend.database import Base, engine, get_database
from app.backend.models import Messages

from app.llm.prompt import BASE_PROMPT, INTENT_PROMPT
from app.llm.llm_api import (
    getting_client_courses,
    getting_intents,
    getting_relevant_courses,
    getting_gigachat_access_token, 
    getting_answer,
    sending_error_message
)

class UserText(BaseModel):
    user_text: str

class ModelText(BaseModel):
    model_answer: str

class TableTexts(BaseModel):
    message_id: UUID
    user_id: int
    message_type: str
    message_text: str
    timestamp: datetime

class UserId(BaseModel):
    user_id: str 

app = FastAPI()
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="app/frontend"), name="static")
templates = Jinja2Templates(directory="app/frontend/html_templates")

@app.get("/")
def sending_user_id(request: Request):
    return templates.TemplateResponse(
        name="start_template.html",
        request=request,
        context={}
    )

@app.post("/getting_user_id")
def getting_user_id(user_id: str = Form(...)):
    response = RedirectResponse(url="/starting_chat", status_code=303)
    response.set_cookie(key="user_id", value=user_id)
    return response

@app.get("/starting_chat")
def starting_chat(request: Request):
    return templates.TemplateResponse(
        name="start_chat_template.html",
        request=request,
        context={}
    )

@app.post("/getting_starting")
def getting_starting_chat():
    response = RedirectResponse(url="/sending_to_chat", status_code=303)
    return response

@app.get("/sending_to_chat")
def chat_page(request: Request):
    user_id = request.cookies.get("user_id")
    return templates.TemplateResponse(
        name="chat_template.html",
        request=request,
        context={"user_id": user_id}
    )

@app.post("/message/completion")
def messaging(request: Request, body: UserText, database=Depends(get_database), conn=Depends(get_database)):
    user_id = request.cookies.get("user_id")
    result = conn.execute(text("""SELECT message_text, timestamp FROM messages 
                                WHERE user_id = :user_id 
                                ORDER BY timestamp 
                                LIMIT 3"""), {"user_id": user_id}).fetchall()
    context = " ".join([row[0] for row in result])
    
    catalog = getting_client_courses(user_id=user_id)
    # topic_client_courses = getting_topic_courses(client_courses=catalog, client_text=body.user_text)
    
    ACCESS_TOKEN = getting_gigachat_access_token()
    if ACCESS_TOKEN == "":
        model_text = sending_error_message(ACCESS_TOKEN=ACCESS_TOKEN)
    else:
        intents = getting_intents(ACCESS_TOKEN=ACCESS_TOKEN, 
                                USER_PROMPT=body.user_text, 
                                SYSTEM_PROMPT=INTENT_PROMPT)
        if intents == "": 
            model_text = sending_error_message(ACCESS_TOKEN=ACCESS_TOKEN)
        else:
            relevant_courses, extra = getting_relevant_courses(catalog, intents=intents)
            model_text = getting_answer(ACCESS_TOKEN=ACCESS_TOKEN, 
                                    BASE_PROMPT=BASE_PROMPT,
                                    context=context,
                                    user_id=user_id,
                                    catalog=relevant_courses,
                                    USER_PROMPT=body.user_text,
                                    extra=extra)
            if model_text == "":
                model_text = sending_error_message(ACCESS_TOKEN=ACCESS_TOKEN)
            else:
                messages = Messages(message_id=uuid.uuid4(), 
                                    user_id=user_id,
                                    message_type="user", 
                                    message_text=body.user_text,
                                    timestamp=datetime.now())
                database.add(messages)

                messages = Messages(message_id=uuid.uuid4(), 
                                    user_id=user_id,
                                    message_type="assistant", 
                                    message_text=model_text,
                                    timestamp=datetime.now())
                database.add(messages)

                database.commit()
    return ModelText(model_answer=model_text)

@app.get("/table/allcontent")
def getting_table(conn=Depends(get_database)):
    result = conn.execute(text("SELECT * FROM messages")).fetchall()
    result_json = [TableTexts(**dict(row._mapping)) for row in result]
    return result_json

@app.post("/table/usercontent")
def getting_user_content(body: UserId, conn=Depends(get_database)):
    result = conn.execute(text("""SELECT * FROM messages 
                               WHERE user_id = :user_id"""), {"user_id": body.user_id}).fetchall()
    result_json = [TableTexts(**dict(row._mapping)) for row in result]
    return result_json
    