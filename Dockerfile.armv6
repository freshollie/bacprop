FROM arm32v6/python:3.7.2-alpine3.8
RUN pip3 install pipenv

WORKDIR /bacprop

COPY Pipfile.lock Pipfile ./

RUN pipenv install --system --deploy --ignore-pipfile

COPY bacprop bacprop

RUN ls -la

ENTRYPOINT [ "python", "-m", "bacprop"]