FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y postgresql-client
RUN apt-get update && apt-get install -y ca-certificates && update-ca-certificates
RUN pip install --no-cache-dir --upgrade certifi requests urllib3

EXPOSE 8000

COPY . .

COPY wait_db.sh /wait_db.sh
RUN chmod +x /wait_db.sh
CMD ["/bin/sh", "/wait_db.sh"]