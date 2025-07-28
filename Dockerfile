FROM python:3.14.0rc1-slim

RUN apt-get update && apt-get install --no-install-recommends -y \
	libcairo2 \
	fonts-noto

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD [ "python", "server.py" ]
