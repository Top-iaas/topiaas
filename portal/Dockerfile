FROM python:3.8-alpine


# Packages required for psycopg2
RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev curl
WORKDIR /app

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

RUN pip3 install -r requirements.txt 
ENV PYTHONIOENCODING=UTF-8
# RUN pip3 install sqlalchemy_utils flask_dance flask_caching python-gitlab

RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
RUN install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

COPY . . 

#RUN python3 manage.py recreate_db && python3 manage.py setup_dev && python3 manage.py add_fake_data

# ENTRYPOINT ["python3", "-u" ,"manage.py", "runserver"]
ENTRYPOINT ["sh", "portal-entrypoint.sh"]
