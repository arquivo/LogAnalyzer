#! /bin/bash
PROGNAME=$0

usage() {
  cat << EOF >&2
Usage: $PROGNAME <year> <month>

 <year>: The year we want to get stats on
 <month>: Two-digit representation of the month we want to get stats on

This script will check every apache log file inside /data/logs/arquivo.pt_apache
for <year>/<month>, and get monthly stats for each service. It starts by
extracting every daily log and concatenate it in a file named <year>-<month>.log,
however if a file with this is already present it will skip the extraction and
aggregation process. It will also create a *.clients.*.log file for each service
which lists every distinct IP address that made a request to that service.

This process may take a long time so it is highly recommended to run this script
inside a screen.

Example: (do this inside a screen!)
$PROGNAME 2022 03

Will display the following monthly metrics:
  Requests - Total requests made to the endpoint
  Filtered Requests - Total requests made to the endpoint, excluding internal
                      requests and requests made by monitoring services such as
                      icinga.
  Clients - Number of distinct clients that made the requests (without filtering)

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

if  [ $# -ne 2 ]; then
  usage;
fi

YEAR=$1
MONTH=$2

LOGFILE="$YEAR-$MONTH.log"

if [ -f "$LOGFILE" ]; then
    >&2 echo "$LOGFILE already exists, skipping log extraction and aggregation"
    >&2 echo ""
else
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
      echo ""
    fi

    mkdir "tmp_$YEAR_$MONTH"

    >&2 echo "Extracting logs..."
    find /data/logs/arquivo.pt_apache/ -type f -name "logfile.$YEAR-$MONTH*.tar.gz" | xargs -I {} tar -xzf {} --directory "./tmp_$YEAR_$MONTH"

    >&2 echo "Aggregating logs..."
    find "./tmp_$YEAR_$MONTH" -type f -name "logfile*"| xargs cat > "$YEAR-$MONTH.log"

    >&2 echo "Cleaning up..."
    rm -rf "./tmp_$YEAR_$MONTH"

    >&2 echo "Done!"
    >&2 echo ""
fi

#IPs to filter out:
OWN_IP='127\.0\.0\.1|^10\.|^172\.1[6-9]\.|^172\.2[0-9]\.|^172\.3[1-2]\.|^192\.1681.' #Our own network IPs
ICINGA_IP='193\.136\.7\.12|2001:690:a00:2029::12' #IP from icinga.fccn.pt (metrics)
LOKI_CERT_IP='193\.136\.2\.10|2001:690:1fff:1600::10' #IP from loki.cert.rcts.pt (certificates)
SIRENS_IP='193\.136\.7\.2|2001:690:a00:2029:804::2' #IP from sirens.fccn.pt (alarms)

FILTER="$OWN_IP|$ICINGA_IP|$LOKI_CERT_IP|$SIRENS_IP"

#echo "$FILTER"

echo -e "Service: \t Requests: \t Filtered: \t Clients:"

#Arquivo.pt API
APT_ALL_REQUESTS=$(grep -a 'GET /textsearch' $LOGFILE | wc -l)
APT_FIL_REQUESTS=$(grep -a 'GET /textsearch' $LOGFILE | cut -d ' ' -f 1 | grep -vEa "$FILTER" | wc -l)
grep -a 'GET /textsearch' $LOGFILE | cut -d ' ' -f 1 | sort | uniq > "$YEAR-$MONTH.clients.apt.log"
APT_CLIENTS=$( cat "$YEAR-$MONTH.clients.apt.log" | wc -l)

echo -e "Arquivo.pt API \t $APT_ALL_REQUESTS \t $APT_FIL_REQUESTS \t $APT_CLIENTS"

#Image Search API
IM_ALL_REQUESTS=$(grep -a 'GET /imagesearch' $LOGFILE | wc -l)
IM_FIL_REQUESTS=$(grep -a 'GET /imagesearch' $LOGFILE | cut -d ' ' -f 1 | grep -vEa "$FILTER" | wc -l)
grep -a 'GET /imagesearch' $LOGFILE | cut -d ' ' -f 1 | sort | uniq > "$YEAR-$MONTH.clients.im.log"
IM_CLIENTS=$( cat "$YEAR-$MONTH.clients.im.log" | wc -l)

echo -e "ImageSearch API\t $IM_ALL_REQUESTS \t $IM_FIL_REQUESTS \t $IM_CLIENTS"

#CDX Server API
CDX_ALL_REQUESTS=$(grep -a 'GET /wayback/cdx' $LOGFILE | wc -l)
CDX_FIL_REQUESTS=$(grep -a 'GET /wayback/cdx' $LOGFILE | cut -d ' ' -f 1 | grep -vEa "$FILTER" | wc -l)
grep -a 'GET /wayback/cdx' $LOGFILE | cut -d ' ' -f 1 | sort | uniq > "$YEAR-$MONTH.clients.cdx.log"
CDX_CLIENTS=$( cat "$YEAR-$MONTH.clients.cdx.log" | wc -l)

echo -e "CDX API\t $CDX_ALL_REQUESTS \t $CDX_FIL_REQUESTS \t $CDX_CLIENTS"

#Memento API
MEM_ALL_REQUESTS=$(grep -a 'GET /wayback/timemap' $LOGFILE | wc -l)
MEM_FIL_REQUESTS=$(grep -a 'GET /wayback/timemap' $LOGFILE | cut -d ' ' -f 1 | grep -vEa "$FILTER" | wc -l)
grep -a 'GET /wayback/timemap' $LOGFILE | cut -d ' ' -f 1 | sort | uniq > "$YEAR-$MONTH.clients.mem.log"
MEM_CLIENTS=$( cat "$YEAR-$MONTH.clients.mem.log" | wc -l)

echo -e "Memento API\t $MEM_ALL_REQUESTS \t $MEM_FIL_REQUESTS \t $MEM_CLIENTS"

#ArchivePageNow
#SPN_REQUESTS=$(grep -aE 'POST /services/savepagenow' $LOGFILE | grep 'success=true' | wc -l)
#grep -aE 'POST /services/savepagenow' $LOGFILE | grep -v 'success=true' | grep -vE '^193\.136' | cut -d ' ' -f 1 | sort | uniq > "$YEAR-$MONTH.                                                                                             clients.spn.log"
#SPN_CLIENTS=$(cat "$YEAR-$MONTH.clients.spn.log" | wc -l)
SPN_ALL_REQUESTS=$(grep -aE 'GET /services/(save|archive)pagenow' $LOGFILE | wc -l)
SPN_FIL_REQUESTS=$(grep -aE 'GET /services/(save|archive)pagenow' $LOGFILE | cut -d ' ' -f 1 | grep -vEa "$FILTER" | wc -l)
grep -a 'GET /services/savepagenow' $LOGFILE | cut -d ' ' -f 1 | sort | uniq > "$YEAR-$MONTH.clients.spn.log"
SPN_CLIENTS=$( cat "$YEAR-$MONTH.clients.spn.log" | wc -l)

echo -e "SavePageNow entry \t $SPN_ALL_REQUESTS \t $SPN_FIL_REQUESTS \t $SPN_CLIENTS"

#ArchivePageNow Recording
SPNR_ALL_REQUESTS=$(grep -a 'GET /save/now/record' $LOGFILE | wc -l)
SPNR_FIL_REQUESTS=$(grep -a 'GET /save/now/record' $LOGFILE | cut -d ' ' -f 1 | grep -vEa "$FILTER" | wc -l)
grep -a 'GET /save/now/record' $LOGFILE | cut -d ' ' -f 1 | sort | uniq > "$YEAR-$MONTH.clients.spnr.log"
SPNR_CLIENTS=$( cat "$YEAR-$MONTH.clients.spnr.log" | wc -l)

echo -e "SavePageNow record \t $SPNR_ALL_REQUESTS \t $SPNR_FIL_REQUESTS \t $SPNR_CLIENTS"

#CompletePage
CP_ALL_REQUESTS=$(grep -a 'GET /services/complete' $LOGFILE | wc -l)
CP_FIL_REQUESTS=$(grep -a 'GET /services/complete' $LOGFILE | cut -d ' ' -f 1 | grep -vEa "$FILTER" | wc -l)
grep -a 'GET /services/complete' $LOGFILE | cut -d ' ' -f 1 | sort | uniq > "$YEAR-$MONTH.clients.cp.log"
CP_CLIENTS=$( cat "$YEAR-$MONTH.clients.cp.log" | wc -l)

echo -e "CompletePage \t $CP_ALL_REQUESTS \t $CP_FIL_REQUESTS \t $CP_CLIENTS"

#Arquivo404
A404_ALL_REQUESTS=$(grep -a 'GET /arquivo404server' $LOGFILE | wc -l)
A404_FIL_REQUESTS=$(grep -a 'GET /arquivo404server' $LOGFILE | cut -d ' ' -f 1 | grep -vEa "$FILTER" | wc -l)
grep -a 'GET /arquivo404server' $LOGFILE | cut -d ' ' -f 1 | sort | uniq > "$YEAR-$MONTH.clients.a404.log"
A404_CLIENTS=$( cat "$YEAR-$MONTH.clients.a404.log" | wc -l)

echo -e "Arquivo404 \t $A404_ALL_REQUESTS \t $A404_FIL_REQUESTS \t $A404_CLIENTS"

