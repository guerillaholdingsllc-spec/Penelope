#!/bin/bash
# Usage: flock_run.sh <lockfile> <script>
LOCK="/tmp/$(basename $1).lock"
exec flock -n $LOCK /root/penelope_env/bin/python3 $1 $2 $3
