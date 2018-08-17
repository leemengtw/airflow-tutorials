# encoding: utf-8
import time
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator


default_args = {
    'owner': 'Meng Lee',
    'start_date': datetime(2100, 1, 1, 0, 0),
    'schedule_interval': '@daily',
    'email': [],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=1)
}


def fn_app():

    print("取得使用者的閱讀紀錄 ...")
    print("去漫畫網站看有沒有新的章節 ...")
    print("跟紀錄比較，有沒有新連載？")

    new_comic_available = time.time() % 2 > 1
    if new_comic_available:
        print("寄 Slack 通知 ...")
        print("更新閱讀紀錄 ...")
    else:
        print("什麼都不幹，結束 ...")


with DAG('comic_app_v1', default_args=default_args) as dag:
    task = PythonOperator(
        task_id='app',
        python_callable=fn_app
    )
