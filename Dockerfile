FROM quay.io/centos/centos:stream8

LABEL name="DCI Analytics" version="0.0.1"
LABEL maintainer="DCI Team <distributed-ci@redhat.com>"

ENV LANG en_US.UTF-8

RUN mkdir /opt/dci-control-server
RUN mkdir /opt/dci-analytics
ADD . /opt/dci-analytics/
WORKDIR /opt/dci-analytics

COPY requirements.txt /tmp/requirements.txt
RUN yum -y install git \
    python3-devel python3-pip python3-setuptools gcc && \
    yum clean all && \
    pip3 install --no-cache-dir -U pip && \
    pip3 install --no-cache-dir -U tox && \
    pip3 install --no-cache-dir -r /tmp/requirements.txt && \
    # workaroud to fix ModuleNotFoundError: No module named 'urllib3.packages.six'
    pip3 uninstall -y urllib3 && \
    pip3 install urllib3

ENV PYTHONPATH /opt/dci-analytics:/opt/dci-control-server
EXPOSE 2345

CMD ["gunicorn", "wsgi:application", "--reload", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "debug", "--bind", "0.0.0.0:2345"]
