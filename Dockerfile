FROM python:3.7

RUN pip install python-telegram-bot

RUN mkdir /app
ADD . /app
WORKDIR /app

ARG CACHEBUST=1

CMD python /app/bot_test.py