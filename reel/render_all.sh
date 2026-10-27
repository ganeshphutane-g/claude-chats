#!/bin/bash
# Render the whole reel in 4 parallel processes (each has its own page file).
cd "$(dirname "$0")"
for k in 0 1 2 3; do a=$((k*279)); b=$(( (k+1)*279 )); [ $k -eq 3 ] && b=1116
  nohup python3 scenes.py render $a $b 2 > work/logs/r$k.log 2>&1 &
done
