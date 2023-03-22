FROM python:3.11-buster

RUN useradd -u 1000 discord
RUN mkdir /home/discord
RUN chown -R discord /home/discord

RUN apt update && apt install -y ffmpeg

USER discord


WORKDIR /home/discord

COPY *.py ./
COPY requirements.txt ./

RUN pip3.11 install -r requirements.txt

CMD ["python3", "ToneBoy.py"]