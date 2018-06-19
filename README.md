# lapse-pi
code for grabbing a timelapse with a pi
# installation
* passwd
* raspi-config -> enable ssh
* raspi-config -> expand fs
* apt-get update
* apt-get install apache2 git
* git clone <this repo>
  
* check host IP
* setup key exchange
* ssh-keygen
* ssh-copy-id -i ~/.ssh/mykey user@host
* crontab  * * * * * /home/pi/lapse-pi/pi/cron.sh
* crontab  * * * * * /home/pi/lapse-pi/pi/sync.sh
* /var/www/html rm index, ln -s /home/pi/lapse-pi/archive archive
