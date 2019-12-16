FROM python:3.7

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN mkdir /app
ADD . /app
WORKDIR /app

ARG CACHEBUST=1

CMD python /app/bot_test.py