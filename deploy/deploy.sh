#!/usr/bin/env bash

# deploy用
# systemd service
sudo cp bot.service /etc/systemd/system/clubroom_bot.service 

# udev rule 
sudo cp 99-arduino-dfu.rules /etc/udev/rules.d/ 
