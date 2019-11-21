FROM python:alpine3.8

COPY requirements.txt /src/requirements.txt
RUN pip3 install -r /src/requirements.txt
RUN rm /src/requirements.txt