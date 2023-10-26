#! /bin/bash
PROGNAME=$0

usage() {
  cat << EOF >&2
Usage: $PROGNAME <year>

 <year>: The year we want to make sure has all logs

This script will check that there are as many daily logs as there are days in
every month in <year>. It checks the /data/logs/arquivo.pt_apache directory.

Example:
$PROGNAME 2022

EOF
  exit 1
}

if  [ $# -ne 1 ]; then
  usage;
fi

YEAR=$1

declare -a MONTHS=("01" "02" "03" "04" "05" "06" "07" "08" "09" "10" "11" "12")

for MONTH in "${MONTHS[@]}"
do
  echo "------ $YEAR / $MONTH ------" 
  DAYS_IN_MONTH=31
  if [ "$MONTH" = "02" ]; then
    DAYS_IN_MONTH=28
  fi
  if [ "$MONTH" = "04" ] || [ "$MONTH" = "06" ] || [ "$MONTH" = "09" ] || [ "$MONTH" = "11" ]; then
    DAYS_IN_MONTH=30
  fi
  DAYS_IN_LOGS=$(find /data/logs/arquivo.pt_apache/ -type f -name "logfile.$YEAR-$MONTH*.tar.gz" | wc -l)
  if [ "$DAYS_IN_MONTH" -gt "$DAYS_IN_LOGS" ]; then
    echo "WARNING - Missing log files for $YEAR/$MONTH : Only found $DAYS_IN_LOGS logfiles."
  else
    echo "OK"
  fi
  echo ""

done
