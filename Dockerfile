FROM python:3.9.16-slim-bullseye

WORKDIR /usr/src/app/NewsFinder

COPY requirements.txt /usr/src/app/NewsFinder
RUN apt-get update && \
    apt-get -y install libpq-dev gcc && \
    pip install -r /usr/src/app/NewsFinder/requirements.txt && \
    pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cpu && \
    apt-get install -y locales && \
    sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales

ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
ENV REDIS=REDIS
ENV POSTGRES=POSTGRES
ENV POSTGRES_DB=articlesdb
ENV POSTGRES_TABLE=articles
ENV POSTGRES_USER=iocsfinder
ENV POSTGRES_PASSWORD=strongHeavyPassword4thisdb
ENV MODEL_CONFIG_URL='https://www.dropbox.com/s/y9ajnw755uz3pb2/config.json?dl=1'
ENV MODEL_URL='https://www.dropbox.com/s/9jlc9rwzckptva9/pytorch_model.bin?dl=1'
ENV MODEL_VOCAB_URL='https://www.dropbox.com/s/pzgexbgd5tdzopy/vocab.txt?dl=1'

COPY . /usr/src/app/NewsFinder

CMD ["python3", "-m", "NewsFinder.__main__"]