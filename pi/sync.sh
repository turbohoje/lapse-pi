#!/bin/bash

#if on a virgin pi, 
#$ ssh-keygin
#$ ssh-copy-id -i ~/.ssh/mykey user@host

rsync -avz --no-o --no-g /home/turbohoje/lapse-pi/archive turbohoje@10.22.14.2:/home/turbohoje/lapse-pi/ --remove-source-files
