# solarmon
Read RS485 metrics out of Growatt inverters and store it to Prometheus/InfluxDB do view it in Grafana.   
You can post to Prometheus, InfluxDB or both.  
Tested on  Growat SPH 10000 TL3 BH UP inverter.

Additionally, you can read data from "RS485 over TCP socket" in greenbono_socket.py  
Additionally, you can use your own logic, calculation or anything in automation.py

This project is based on https://github.com/ZeroErrors/solarmon

## How to set up all the things to work:

- Wiring to Growat SPH inverter
- Raspberry Pi
- InfluxDB and Grafana localy
- Phyton and this project
- Prometheus and Grafana as a Cloud service

### Wiring to Growat SPH inverter

Growat user man:  SPH-4-10KTL3-BH-UP-User-Manual.pdf  
Growat RS485 port:  Growatt PV Inverter Modbus RS485 RTU Protocol v120.pdf  
(documets are attached)  

Use some USB/RS485 dongle to connect Raspberry Pi to Growatt inverter.  
Wire the RJ45 connector according to this documentation https://solar-assistant.io/help/growatt/configuration  chapter Growatt SPH range, Option 3.  
Simply: use two-wire cable and use pins 5(A) and 1(B). Connect it to Inverter, socket 485-3.


### Raspberry Pi 
Use software "Raspberry Pi Manager" to prepare and install Debian image to you Raspberry Pi. Click Configuration button to configure Wifi, root password and enable ssh.  

### InfluxDB and Grafana localy
Run Raspberry Pi, connect to it using credential defined above  
```
sudo apt update  
sudo apt upgrade -y  
curl https://repos.influxdata.com/influxdata-archive.key | gpg --dearmor | sudo tee /usr/share/keyrings/influxdb-archive-keyring.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/influxdb-archive-keyring.gpg] https://repos.influxdata.com/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/influxdb.list
sudo apt update
sudo apt install influxdb
sudo systemctl unmask influxdb.service  
sudo systemctl enable influxdb  
sudo systemctl start influxdb.service
influx
```
In your browser go to http://<IPADDRESS>:8086/ and create new database (bucket) named "home", login and password
```
create database home  
use home  
create user grafana with password '<your password>' with all privileges  
grant all privileges on home to grafana  
show users  
exit  
```
and again in bash terminal:
```
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -  
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list  
sudo apt update && sudo apt install -y grafana  
sudo systemctl unmask grafana-server.service  
sudo systemctl start grafana-server  
sudo systemctl enable grafana-server.service  
```

Login to Grafana  (admin:admin) and chage the init password.   
Add datasource of type InfluxDB and configure this parameters:  
section HTTP:  
URL: http://127.0.0.1:8086  

section InfluxDB details:  
Database: home  
User: grafana  
Password: your Influx password from above  
HTTP method: GET  

Import Dashboard Growatt-influx (attached to this project)  

### Phyton and this project
Clone this project to Raspberry Pi and in the project directory edit solarmon.cfg and solarmon.service.  
Execute:
```
pip install -r requirements.txt
sudo cp solarmon.service /lib/systemd/system
sudo systemctl start solarmon
sudo systemctl status solarmon
sudo systemctl enable solarmon
```
or simply run it by ```python3 solarmon.py```


### Prometheus and Grafana as a Cloud service
Sign to grafana.net. Your dashboards will be at https://<your_login>.grafana.net/  
Generate token with role for writing metrics to your Prometheus DB and save this token to solarmon.cfg  

Import Dashboard Growatt-prometheus-cloud (attached to this project).  


