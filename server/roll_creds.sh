#!/bin/bash


date > roll_date.txt

rm creds.storage
./up.py --noauth_local_webserver

