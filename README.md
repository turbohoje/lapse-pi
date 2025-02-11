# lapse-pi

![installed camera](img/lapse_piV1.jpg)

code for grabbing a timelapse with a pi
# installation
* passwd
* `raspi-config`
  * enable ssh
  * expand fs
  * enable camera
  * fix timezone/locale
* `apt-get update`
* `apt-get upgrade`
* `apt-get install -y apache2 git`vim
* modify /boot/config.txt to have `disable_camera_led=1` 
* `git clone <this repo>`
  
* check host IP
* setup key exchange
* ssh-keygen
* ssh-copy-id -i ~/.ssh/mykey user@host
* crontab config (below)
* /var/www/html rm index, ln -s /home/pi/lapse-pi/archive archive

* `vm.min_free_kbytes = 32768` in /etc/sysctl.conf
* `smsc95xx.turbo_mode=N` /boot/cmdline.txt 
* `rpi-update`


# connectvity hacks
in case you dont have direct access to the host
use the 'haus' server to host connections.
correc ufw for opening a port e.g. 8222
in /etc/ssh/sshd_config 
* GatewayPorts yes

on the installed pi
* ssh -R \*.8222:localhost:22 user@hausaddress.com -N

then you can shell to the haus and get forwarded to the pi behind the firewall

#Crontab
```
* * * * * UN=admin PW=notreal /home/turbohoje/lapse-pi/pi/cron.sh
0 * * * * /bin/timeout -s2 3599 /home/turbohoje/lapse-pi/pi/sync.sh
59 * * * * find ~/lapse-pi/archive/0/ -type d -empty -print -delete 
```
