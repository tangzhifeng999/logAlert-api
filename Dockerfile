FROM ubuntu:18.04

USER root

ENV LOG_PATH /var/log/logAlert/log.log

RUN mkdir -p /var/log/logAlert
RUN sed -i 's/http:\/\/archive\.ubuntu\.com\/ubuntu\//http:\/\/mirrors\.aliyun\.com\/ubuntu\//g' /etc/apt/sources.list

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get update
RUN apt-get install tzdata
RUN dpkg-reconfigure --frontend noninteractive tzdata

RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip3 install -i https://mirrors.aliyun.com/pypi/simple gevent gunicorn

COPY ./requirements.txt /
RUN pip3 install -i https://mirrors.aliyun.com/pypi/simple -r requirements.txt

COPY . /src
WORKDIR /src

CMD ["sh", "start.sh"]