FROM python:3.7.2-alpine3.8
RUN pip3 install pipenv --no-cache-dir

WORKDIR /bacprop

COPY Pipfile.lock Pipfile ./

RUN pipenv install --system --deploy --ignore-pipfile \
    && pip3 uninstall -y pipenv

COPY bacprop bacprop

ENTRYPOINT [ "python", "-m", "bacprop" ]
