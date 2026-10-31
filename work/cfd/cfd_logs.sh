#!/bin/bash
# Show the tail of a case's logs inside WSL.  Usage: cfd_logs.sh <case name> [log name] [lines]
D=$HOME/sparkshift_cfd/$1
LOG=${2:-}
N=${3:-40}
if [ -z "$LOG" ]; then
    ls -la "$D"
    for f in "$D"/log.*; do echo "===== $f"; tail -n 8 "$f"; done
else
    tail -n "$N" "$D/$LOG"
fi
