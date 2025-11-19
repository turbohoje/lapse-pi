#!/bin/bash

#$ ssh-copy-id -i ~/.ssh/mykey user@host
cd /home/turbohoje/lapse-pi
find ./archive -mtime +4 > manifest.txt
#rsync -avz --no-o --no-g --files-from=manifest.txt turbohoje@10.22.14.3:/var/services/homes/turbohoje/lapse-pi/ # --remove-source-files
rsync  -avz --files-from=manifest.txt ./ turbohoje@10.22.14.3:/var/services/homes/turbohoje/lapse-pi --remove-source-files
