FROM debian:bookworm

WORKDIR /app

SHELL ["/bin/bash", "-c"]

RUN apt update && apt upgrade -y
RUN apt install -y python3.11 python3.11-venv

COPY requirements.txt requirements.txt

RUN python3.11 -m venv .venv
RUN source .venv/bin/activate && pip install -r requirements.txt

COPY . .

CMD source .venv/bin/activate && ./start-gunicorn.sh
