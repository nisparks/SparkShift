#!/bin/bash
cd $HOME/sparkshift_cfd
while ! tail -1 released_bambu/log.run | grep -q done; do sleep 20; done
bash $HOME/sparkshift_cfd/launch.sh all - none r41lip_bambu_rough3 > after_released.log 2>&1
