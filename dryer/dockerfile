FROM python:3
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN apt-get update -y
RUN apt-get install net-tools
RUN apt-get install -y apt-utils
RUN apt-get install -y wireless-tools
RUN apt-get install -y wpasupplicant
RUN echo "ctrl_interface=/run/wpa_supplicant \nupdate_config=1" > /etc/wpa_supplicant/wpa_supplicant.conf 
RUN wpa_supplicant -B -c /etc/wpa_supplicant/wpa_supplicant.conf -i cat /proc/net/wireless | perl -ne '/(\w+):/ && print $1'
WORKDIR /home/pi
COPY . /home/pi