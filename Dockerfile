FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
	libcairo2 \
	fonts-noto

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD [ "python", "server.py" ]
