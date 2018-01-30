#!/bin/bash
cd /home/date/centeragent
mkdir temp
export PYTHONPATH=./temp
/usr/bin/python setup.py build develop --install-dir ./temp
cp ./temp/CenterAgent.egg-link /home/date/.config/deluge/plugins
rm -fr ./temp
