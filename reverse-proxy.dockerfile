FROM quay.io/centos/centos:stream8

LABEL name="DCI Analytics" version="0.0.1"
LABEL maintainer="DCI Team <distributed-ci@redhat.com>"

ENV LANG en_US.UTF-8

RUN yum -y install httpd

RUN echo "reverse proxy" > /var/www/html/index.html

EXPOSE 80

COPY apache-reverse-proxy.conf /etc/httpd/conf.d/apache-reverse-proxy.conf

ENTRYPOINT ["/usr/sbin/httpd"]

CMD ["-D", "FOREGROUND"]
