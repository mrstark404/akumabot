FROM python:3.12

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

CMD ["python3", "forwarder.py"]
