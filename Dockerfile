FROM python:3.12-slim

WORKDIR /backend

COPY ./requirements.txt /backend/requirements.txt

RUN pip install -r /backend/requirements.txt

COPY ./ /backend/

