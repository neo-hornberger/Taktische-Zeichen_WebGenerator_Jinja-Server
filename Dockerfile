FROM python:3.12-slim

RUN apt-get update && apt-get install --no-install-recommends -y \
	libcairo2 \
	fonts-noto

WORKDIR /app
COPY pyproject.toml .
RUN pip install -e .

COPY . .

CMD [ "python", "server.py" ]
