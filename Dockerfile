FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y nodejs npm
WORKDIR /code

# ✅ Step 1: copy requirements early
COPY requirements.txt /code/

# ✅ Step 2: install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# ✅ Step 3: copy remaining project files

COPY . /code/



# ✅ Step 4: run server
CMD gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3
