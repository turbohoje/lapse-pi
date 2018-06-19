# lapse-pi
code for grabbing a timelapse with a pi
# installation
* passwd
* `raspi-config`
  * enable ssh
  * expand fs
  * enable camera
  * fix timezone/locale
* `apt-get update`
* `apt-get install -y apache2 git`vim
* modify /boot/config.txt to have `disable_camera_led=1` 
* `git clone <this repo>`
  
* check host IP
* setup key exchange
* ssh-keygen
* ssh-copy-id -i ~/.ssh/mykey user@host
* crontab  * * * * * /home/pi/lapse-pi/pi/cron.sh
* crontab  * * * * * /home/pi/lapse-pi/pi/sync.sh
* /var/www/html rm index, ln -s /home/pi/lapse-pi/archive archive

* `vm.min_free_kbytes = 32768` in /etc/sysctl.conf
* `smsc95xx.turbo_mode=N` /boot/cmdline.txt 
