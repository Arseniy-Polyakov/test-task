import os
import json
import uuid
# import faiss
import pandas as pd
import numpy as np
import requests
import json_repair
# from sklearn.feature_extraction.text import TfidfVectorizer
from uuid import UUID
from app.llm.prompt import INTENT_PROMPT, BASE_PROMPT, ERROR_PROMPT

def getting_client_courses(user_id: str):
    df = pd.read_csv("app//llm//df.csv")
    user_data = df.groupby("user_name").get_group(f"Пользователь_{user_id}")
    return user_data 
    
# def getting_topic_courses(client_courses, client_text: str) -> list:
#     courses_descriptions = client_courses["course_description"].tolist()
#     vectorizer = TfidfVectorizer()
#     all_embeddings = vectorizer.fit_transform(courses_descriptions)
#     client_embedding = vectorizer.transform([client_text])
#     all_embeddings = all_embeddings.toarray().astype("float32")
#     client_embedding = client_embedding.toarray().astype("float32")
    
#     index = faiss.IndexFlatL2(client_embedding.shape[1])
#     index.add(all_embeddings)
#     _, indeces = index.search(client_embedding.reshape(1, -1), k=5)
#     target_indeces = indeces[0]
    
#     df = pd.read_csv("app//llm//df.csv")
#     topic_client_courses = df.iloc[[
#         target_indeces[0], 
#         target_indeces[1], 
#         target_indeces[2],
#         target_indeces[3],
#         target_indeces[4]]]
#     return topic_client_courses

def getting_relevant_courses(topic_client_courses, intents: dict):
    extra = ""
    try:
        price = intents["price"]
        if price == "1":
            topic_client_courses = topic_client_courses[(topic_client_courses["price"] >= 25000) & (topic_client_courses["price"] <= 40000)]
        elif price == "2":
            topic_client_courses = topic_client_courses[(topic_client_courses["price"] >= 40000) & (topic_client_courses["price"] <= 55000)]
        elif price == "3":
            topic_client_courses = topic_client_courses[topic_client_courses["price"] >= 55000]
        else: 
            topic_client_courses = topic_client_courses
    except:
        topic_client_courses = topic_client_courses
    
    try:
        discount = intents["discount"]
        if discount == "1":
            topic_client_courses = topic_client_courses[topic_client_courses["discount"] <= 10]
        elif discount == "2":
            topic_client_courses = topic_client_courses[(topic_client_courses["discount"] >= 10) & (topic_client_courses["discount"] <= 20)]
        elif discount == "3":
            topic_client_courses = topic_client_courses[(topic_client_courses["discount"] >= 20)]
        else:
            topic_client_courses = topic_client_courses
    except:
        topic_client_courses = topic_client_courses
    
    try:
        extra = intents["extra"]
        if extra == "0":
            topic_client_courses = topic_client_courses.sort_values(by=["probability"], ascending=False)
            topic_client_courses_main = topic_client_courses[["recommended_course", 
                                                     "course_description",
                                                     "discount",
                                                     "probability",
                                                     "price"]]
            topic_client_courses_rows = [["Название курса: " + row["recommended_course"],
                                "Описание курса: " + row["course_description"],
                                "Скидка (в процентах): " + str(row["discount"]),
                                "Степень заинтересованности клиента в курсе (в процентах) " + str(row["probability"]),
                                "Цена (в рублях) " + str(row["price"])] for _, row in topic_client_courses_main.iterrows()]
            topic_client_courses_line = " ".join(np.array(topic_client_courses_rows).flatten())
        else:
            topic_client_courses_line = ""    
    except:
        topic_client_courses_line = "" 
    return topic_client_courses_line, extra

def getting_gigachat_access_token() -> str:
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    AUTHORIZATION_ID = os.getenv("GIGACHAT_AUTHORIZATION_ID")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": "Basic " + AUTHORIZATION_ID
    }
    data = {
        "scope": "GIGACHAT_API_PERS"
    }
    response = requests.post(url=url, headers=headers, data=data, verify=False)
    if response.status_code == 200:
        ACCESS_TOKEN = response.json()["access_token"]
    else:
        ACCESS_TOKEN = ""
    return ACCESS_TOKEN

def getting_intents(ACCESS_TOKEN: str, SYSTEM_PROMPT: str, USER_PROMPT: str):
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + ACCESS_TOKEN 
    }
    data = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT}
        ],
        "top_p": 0.0
    }
    response = requests.post(url=url, headers=headers, data=json.dumps(data), verify=False)
    if response.status_code == 200:
        answer = response.json()["choices"][0]["message"]["content"]
        answer_cleaned = json_repair.loads(answer)
    else:
        answer_cleaned = ""
    return answer_cleaned

def getting_answer(ACCESS_TOKEN: str, 
                    BASE_PROMPT: str, 
                    context: str, 
                    user_id: UUID,
                    catalog: str,
                    USER_PROMPT: str,
                    extra: str) -> json:
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + ACCESS_TOKEN 
    }
    
    SYSTEM_PROMPT = f"""{BASE_PROMPT}
                    Тематика запроса пользователя: {catalog}
                    Контекст диалога: {context} 
                    Уникальный номер клиента: {user_id}
                    Extra {extra}"""
    data = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Список подходящих курсов: " + USER_PROMPT}
        ],
        "top_p": 0.0
    }
    response = requests.post(url=url, headers=headers, data=json.dumps(data), verify=False)
    if response.status_code == 200:
        answer = response.json()["choices"][0]["message"]["content"]
    else:
        answer = ""
    return answer

def sending_error_message(ACCESS_TOKEN: str):
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + ACCESS_TOKEN 
    }
    data = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": ERROR_PROMPT}
        ],
        "top_p": 0.0
    }
    response = requests.post(url=url, headers=headers, data=json.dumps(data), verify=False)
    if response.status_code == 200:
        answer = response.json()["choices"][0]["message"]["content"]
    else:
        answer = """К сожалению, в данный момент я не смогу вас проконсультировать.
                    Чтобы решить ваш вопрос, я позвал оператора в чат, скоро он подключится.
                    Также вы можете позвонить по номеру телефона 8 (999) XXX-XX-XX или написать на электронную почту fin_example@fin.com"""
    return answer 

