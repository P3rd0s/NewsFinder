FROM python:3.9.16-slim-bullseye

WORKDIR /usr/src/app/NewsFinder

COPY requirements.txt /usr/src/app/NewsFinder
RUN pip install -r /usr/src/app/NewsFinder/requirements.txt && \
    apt-get update && \
    apt-get install -y locales && \
    sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales

ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
ENV REDIS=REDIS

COPY . /usr/src/app/NewsFinder

CMD ["python3", "-m", "NewsFinder.__main__"]