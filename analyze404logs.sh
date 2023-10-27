#!/bin/bash
PROGNAME=$0

usage() {
  cat << EOF >&2
Usage: $PROGNAME <awstats_log_file>

 <awstats_log_file>: The log file for the month we want to analyse. Awstat logs are located in /data/logs/awstats_results/arquivo.pt_apache/

This script will present the relevant metrics for arquivo404 on a particular month based on awstats logs.

EOF
  exit 1
}

if  [ $# -ne 1 ]; then
  usage;
fi

sed -n '/BEGIN_SIDER /,/END_SIDER/p' $1 | grep arquivo404server | cut -d '/' -f 5- | awk '{print $2,$1}' | sort -nrk1 > hits
sed -n '/BEGIN_SIDER /,/END_SIDER/p' $1 | grep -E 'wayback/[0-9]+/' | cut -d / -f 5- | sed 's/^\///' | sort > waybacks
awk -f aggregate_waybacks.awk waybacks > waybacks_aggregated

awk '{print $2}' hits | sed 's/^http\(s\|\):\/\(\/\|\)//' | sed 's/^www\.//' | sed 's/[.[\(*^$+?{|]/\\&/g' | xargs -I {} grep -E '{}/? ' waybacks_aggregated | sort -k1,1 | uniq | sort -rnk2 > waybacks_404

echo ""
echo "Total arquivo404 requests:"
total_hits=$(awk '{sum += $1} END {print sum}' hits)
echo "$total_hits"

echo ""
echo "5 Most requested pages:"
head -n5 hits | awk '{ print $2,":",$1 }'

echo ""
echo "Total arquivo404 requests that resulted in visits to arquivo.pt:"
total_visit=$(awk '{sum += $2} END {print sum}' waybacks_404) 
echo "$total_visit"

echo ""
echo "5 most visited pages:"
cat waybacks_404 | sort -rnk2 | head -n5 | awk '{ print $1,":",$2 }'

echo ""
echo "Visit to requests ratio:"
echo "100 * $total_visit / $total_hits" | bc -l | awk '{printf("%.2f %%\n",$1)}'

rm hits waybacks waybacks_aggregated waybacks_404
