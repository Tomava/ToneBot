FROM python:3.11-buster

#RUN groupadd -r -g 1000 discord
#RUN useradd -u 1000 -g 1000 -m discord
#RUN chown -R discord /app

RUN apt update && apt install -y ffmpeg

# Uncomment if not running rootless Docker
#USER discord

WORKDIR /app

COPY .env ./
COPY *.py ./
COPY requirements.txt ./

RUN pip3.11 install -r requirements.txt

CMD ["python3", "ToneBoy.py"]