FROM    python:2.7-alpine
COPY    . /yourworld
WORKDIR /yourworld
RUN     pip install -r requirements.txt
RUN     python manage.py syncdb --noinput
CMD     python manage.py runserver 0.0.0.0:8000
