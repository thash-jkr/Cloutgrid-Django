FROM python:3.12-alpine

WORKDIR /app

RUN apk update && apk add --no-cache \
  gcc \
  musl-dev \
  libpq-dev \
  postgresql-dev \
  python3-dev \
  jpeg-dev \
  zlib-dev \
  build-base

COPY requirements.txt ./

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD [ "python", "manage.py", "runserver", "0.0.0.0:8000" ]
