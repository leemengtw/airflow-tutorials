# airflow-tutorials
A fork branch for setting up local development quickly with AirFlow.


# Installation
```bash 
conda env update
conda activate airflow-tutorial
export AIRFLOW_HOME="$(pwd)"
airflow initdb
```
# Start Airflow web UI
`airflow webserver -p 8080`

# Test AirFlow with CLI
`airflow test comic_app_v1 superman_task 2018-08-18`

For selenium, you need to download the driver manually. I use Firefox and you can find the driver from https://github.com/mozilla/geckodriver/releases/
Use Case:
* Setting up daily scraping job.
* Modify to use telegram channel instead of SlackOperator


https://hooks.slack.com/services/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