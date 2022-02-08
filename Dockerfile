FROM quay.io/centos/centos:stream8

LABEL name="DCI Analytics" version="0.0.1"
LABEL maintainer="DCI Team <distributed-ci@redhat.com>"

ENV LANG en_US.UTF-8

RUN mkdir /opt/dci-analytics
ADD . /opt/dci-analytics/
WORKDIR /opt/dci-analytics

COPY requirements.txt /tmp/requirements.txt
RUN yum -y install git \
    python3-devel python3-pip python3-setuptools && \
    yum clean all && \
    pip3 install --no-cache-dir -U pip && \
    pip3 install --no-cache-dir -U tox && \
    pip3 install --no-cache-dir -r /tmp/requirements.txt && \
    # workaroud to fix ModuleNotFoundError: No module named 'urllib3.packages.six'
    pip3 uninstall -y urllib3 && \
    pip3 install urllib3

ENV PYTHONPATH /opt/dci-analytics
EXPOSE 2345

CMD ["python3", "/opt/dci-analytics/bin/run-api-server"]
