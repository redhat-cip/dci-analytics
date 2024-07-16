FROM registry.access.redhat.com/ubi8/ubi-minimal

LABEL name="DCI Analytics" version="0.0.1"
LABEL maintainer="DCI Team <distributed-ci@redhat.com>"

ENV LANG en_US.UTF-8

RUN mkdir /opt/dci-control-server
RUN mkdir /opt/dci-analytics
COPY . /opt/dci-analytics/
WORKDIR /opt/dci-analytics

RUN microdnf update && \
    microdnf -y install python3-pip python3-wheel git && \
    microdnf -y install python3-devel gcc-c++ gcc && \
    pip3 install --no-cache-dir -U pip && \
    pip3 install --no-cache-dir -U tox && \
    pip3 install --no-cache-dir -r requirements.txt && \
    microdnf -y remove python3-devel gcc-c++ gcc && \
    microdnf -y clean all

ENV PYTHONPATH /opt/dci-analytics:/opt/dci-control-server
EXPOSE 2345

CMD ["gunicorn", "wsgi:application", "--reload", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "debug", "--bind", "0.0.0.0:2345"]
