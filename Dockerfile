FROM registry.access.redhat.com/ubi8/ubi-minimal

LABEL name="DCI Analytics" version="0.0.1"
LABEL maintainer="DCI Team <distributed-ci@redhat.com>"

ENV LANG en_US.UTF-8

RUN mkdir /opt/dci-control-server
RUN mkdir /opt/dci-analytics
COPY . /opt/dci-analytics/
WORKDIR /opt/dci-analytics


RUN microdnf update && \
  microdnf -y install python3-pip python3-wheel libpq git && \
  rpm -qa | sort > /tmp/rpms_before && \
  microdnf -y install python3-devel make gcc gcc-c++ postgresql-devel diffutils findutils file && \
  rpm -qa | sort > /tmp/rpms_after && \
  pip3 --no-cache-dir install --no-binary=psycopg2 -r requirements.txt && \
  comm -13 /tmp/rpms_before /tmp/rpms_after | xargs microdnf remove && \
  rm /tmp/rpms_before /tmp/rpms_after && \
  microdnf -y clean all


  ENV PYTHONPATH /opt/dci-analytics:/opt/dci-control-server
EXPOSE 2345

CMD ["gunicorn", "wsgi:application", "--reload", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "debug", "--bind", "0.0.0.0:2345"]
