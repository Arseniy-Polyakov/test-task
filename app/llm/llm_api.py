import os
import json
import uuid
import pandas as pd
import requests
from uuid import UUID

def getting_client_courses(user_id: str) -> str:
    df = pd.read_csv("app//llm//df.csv")
    df_client = df.groupby("user_name").get_group(f"Пользователь_{user_id}").sort_values("probability", ascending=False)
    df_target = df_client[["recommended_course", 
                           "course_description",
                           "discount",
                           "probability",
                           "price"]]
    df_target_renamed = df_target.rename(mapper={"recommended_course": "Рекомендованный курс",
                                                 "course_description": "Описание курса",
                                                 "discount": "Скидка на курс",
                                                 "probability": "Вероятность интереса клиента",
                                                 "price": "Цена курса"}, axis=1)
    courses = " ".join(["Рекомендованный курс: " + row["Рекомендованный курс"] + 
                      " Описание курса: " + row["Описание курса"] + 
                      " Скидка на курс: " +  row["Скидка на курс"] + 
                      " Вероятность интереса клиента: " + str(row["Вероятность интереса клиента"]) + "%" + 
                      " Цена курса: " + str(row["Цена курса"]) + " рублей"
                      for _, row in df_target_renamed.iterrows()])
    return courses

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
    ACCESS_TOKEN = response.json()["access_token"]
    return ACCESS_TOKEN

def getting_gigachat_completion(ACCESS_TOKEN: str, 
                                BASE_PROMPT: str, 
                                context: str, 
                                catalog: str,
                                user_id: UUID,
                                USER_PROMPT: str,) -> json:
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + ACCESS_TOKEN 
    }
    
    SYSTEM_PROMPT = f"""{BASE_PROMPT}
                    Контекст диалога: {context} 
                    Каталог курсов: {catalog} 
                    Уникальный номер клиента: {user_id}"""
    data = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT}
        ],
        "top_p": 0.0
    }
    response = requests.post(url=url, headers=headers, data=json.dumps(data), verify=False)
    answer = response.json()["choices"][0]["message"]["content"]
    return answer
