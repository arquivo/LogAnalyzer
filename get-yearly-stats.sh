#! /bin/bash
PROGNAME=$0

usage() {
  cat << EOF >&2
Usage: $PROGNAME <year>

 <year>: The year we want to get stats on

This script will check every apache log file inside /data/logs/arquivo.pt_apache 
for the year <year>, and get monthly stats for each service. Requires the script
get-monthlt-stats.sh to be present on the same folder as this script was called
from.

This process may take a long time so it is highly recommended to run this script
inside a screen, and to output the results to a file.

Example: (do this inside a screen!)
$PROGNAME 2022 | tee 2022.stats

Will display the following monthly metrics:
  Requests - Total requests made to the endpoint
  Filtered Requests - Total requests made to the endpoint, excluding internal
                      requests and requests made by monitoring services such as
                      icinga.
  Clients - Number of distinct clients that made the requests (without filtering)

After analysing each month, will also calculate the number distinct clients for
the entire year.

The services being measured are the following:
  Arquivo.pt API:     GET requests to /textsearch
  ImageSearch API:    GET requests to /imagesearch
  CDX Server API:     GET requests to /wayback/cdx
  Memento API:        GET requests to /wayback/timemap
  SavePageNow entry:  GET requests to /services/savepagenow
  SavePageNow record: GET requests to /save/now/record
  CompletePage:       GET requests to /services/complete-page
  Arquivo404:         GET requests to /arquivo404server


EOF
  exit 1
}

if  [ $# -ne 1 ]; then
  usage;
fi

YEAR=$1

mkdir "tmp_$YEAR"
cd "tmp_$YEAR"
rm -f ./*.log

declare -a MONTHS=("01" "02" "03" "04" "05" "06" "07" "08" "09" "10" "11" "12")

for MONTH in "${MONTHS[@]}"
do
  echo "------ $YEAR / $MONTH ------" 
  LOGFILE="$YEAR-$MONTH.log"
  ../get-monthly-stats.sh $YEAR $MONTH
  rm -f "$LOGFILE" #We delete the file to ensure we have enough disk space
  echo ""
done

echo "------ Total Distinct Clients in $YEAR: ------"
echo -e "Arquivo.pt API         $(cat ./*.clients.apt.log | sort | uniq | wc -l)"
echo -e "ImageSearch API        $(cat ./*.clients.im.log | sort | uniq | wc -l)"
echo -e "CDX API                $(cat ./*.clients.cdx.log | sort | uniq | wc -l)"
echo -e "Memento API            $(cat ./*.clients.mem.log | sort | uniq | wc -l)"
echo -e "ArchivePageNow entry   $(cat ./*.clients.spn.log | sort | uniq | wc -l)"
echo -e "ArchivePageNow record  $(cat ./*.clients.spnr.log | sort | uniq | wc -l)"
echo -e "CompletePage           $(cat ./*.clients.cp.log | sort | uniq | wc -l)"
echo -e "Arquivo404             $(cat ./*.clients.a404.log | sort | uniq | wc -l)"

rm -f ./*.log
cd ..
rm -rf "tmp_$YEAR"
