#!/bin/bash
cd $HOME/sparkshift_cfd
while ! grep -q '^Time = 1201$' r41lip_bambu/log.simpleFoam; do sleep 10; done
sleep 5
docker rm -f sfcfd_r41lip_bambu > /dev/null
echo 1200 > r41lip_bambu/times.txt
echo "[$(date +%H:%M:%S)] stopped after the 180 L/min stage" >> r41lip_bambu/log.run
bash $HOME/sparkshift_cfd/launch.sh post - none r41lip_bambu > stop_lip_1200.log 2>&1
