#!/bin/bash

#$ ssh-copy-id -i ~/.ssh/mykey user@host
cd /home/turbohoje/lapse-pi
find ./archive -mtime +2 > manifest.txt
#rsync -avz --no-o --no-g --files-from=manifest.txt turbohoje@10.22.14.3:/var/services/homes/turbohoje/lapse-pi/ # --remove-source-files
rsync  -avz --files-from=manifest.txt ./ turbohoje@10.22.14.3:/var/services/homes/turbohoje/lapse-pi --remove-source-files

find /home/turbohoje/lapse-pi/archive/0/ -type d -empty -print -delete 
find /home/turbohoje/lapse-pi/archive/1/ -type d -empty -print -delete 
find /home/turbohoje/lapse-pi/archive/2/ -type d -empty -print -delete 
find /home/turbohoje/lapse-pi/archive/3/ -type d -empty -print -delete 
