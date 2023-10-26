# log-analysis

The repository is divided into three parts:
- Python script to process the logs (Apache Common Log Format and Apache Log4j) and aggregate the information --> Generate_General_Logs.py;
- Python script to load the data and generate graphics --> Data_Analitics.py;
- Shell scripts to analyse apache logs to get basic metrics for different services like APIs, SavePageNow, CompletePage or Arquivo404.
## Python Scripts
```
python Generate_General_Logs.py
```

```
python Data_Analitics.py
```

## Shell Scripts
All shell scripts have inbuilt instructions on how to use them if the required parameters are not present. The instructions also provide information on what they do and how they work:
```
$ ./check-yearly-logs.sh
Usage: ./check-yearly-logs.sh <year>

 <year>: The year we want to make sure has all logs

This script will check that there are as many daily logs as there are days in
every month in <year>. It checks the /data/logs/arquivo.pt_apache directory.

Example:
./check-yearly-logs.sh 2022
```

### Examples on how to run each of them:

Check that all logs for 2023 are present:
```
./check-yearly-logs.sh 2023
```

Get stats for 2023: (do this inside a screen!)
```
./get-yearly-stats.sh 2023 | tee 2023.stats
```

Get stats for April 2023: (do this inside a screen!) 
```
./get-monthly-stats.sh 2023 04
```

## Additional Information
This repository contains external datasets (util folder) and papers that may be useful for future analysis.

Due to the large volume of information, these folders are stored internally (Paris\AWP\Maintenance and Operations\Log Analysis Metrics).

If you would like to access the information, please send an email:

contacto@arquivo.pt
