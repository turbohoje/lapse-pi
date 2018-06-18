#!/bin/bash

#if on a virgin pi, 
#$ ssh-keygin
#$ ssh-copy-id -i ~/.ssh/mykey user@host

rsync -avz --no-o --no-g /home/pi/lapse-pi/archive turbohoje@207.224.48.249:/mnt/terra/media/marmot
