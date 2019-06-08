import os
import time
import json
import logging
from datetime import datetime, timedelta
from selenium import webdriver
from airflow import DAG
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.slack_operator import SlackAPIPostOperator
from airflow.operators.latest_only_operator import LatestOnlyOperator


default_args = {
    'owner': 'Meng Lee',
    'start_date': datetime(2100, 1, 1, 0, 0),
    'retries': 2,
    'retry_delay': timedelta(minutes=1)
}

comic_page_template = 'https://www.cartoonmad.com/comic/{}.html'


def process_metadata(mode, **context):

    file_dir = os.path.dirname(__file__)
    metadata_path = os.path.join(file_dir, '../data/comic.json')
    if mode == 'read':
        with open(metadata_path, 'r') as fp:
            metadata = json.load(fp)
            print("Read History loaded: {}".format(metadata))
            return metadata
    elif mode == 'write':
        print("Saving latest comic information..")
        _, all_comic_info = context['task_instance'].xcom_pull(task_ids='check_comic_info')

        # update to latest chapter
        for comic_id, comic_info in dict(all_comic_info).items():
            all_comic_info[comic_id]['previous_chapter_num'] = comic_info['latest_chapter_num']

        with open(metadata_path, 'w') as fp:
            json.dump(all_comic_info, fp, indent=2, ensure_ascii=False)


def check_comic_info(**context):
    metadata = context['task_instance'].xcom_pull(task_ids='get_read_history')
    driver = webdriver.Chrome()
    driver.get('https://www.cartoonmad.com/')
    print("Arrived top page.")

    all_comic_info = metadata
    anything_new = False
    for comic_id, comic_info in dict(all_comic_info).items():
        comic_name = comic_info['name']
        print("Fetching {}'s chapter list..".format(comic_name))
        driver.get(comic_page_template.format(comic_id))

        # get the latest chapter number
        links = driver.find_elements_by_partial_link_text('第')
        latest_chapter_num = [int(s) for s in links[-1].text.split() if s.isdigit()][0]
        previous_chapter_num = comic_info['previous_chapter_num']

        all_comic_info[comic_id]['latest_chapter_num'] = latest_chapter_num
        all_comic_info[comic_id]['new_chapter_available'] = latest_chapter_num > previous_chapter_num
        if all_comic_info[comic_id]['new_chapter_available']:
            anything_new = True
            print("There are new chapter for {}(latest: {})".format(comic_name, latest_chapter_num))

    if not anything_new:
        print("Nothing new now, prepare to end the workflow.")

    driver.quit()

    return anything_new, all_comic_info


def decide_what_to_do(**context):
    anything_new, all_comic_info = context['task_instance'].xcom_pull(task_ids='check_comic_info')

    print("跟紀錄比較，有沒有新連載？")
    if anything_new:
        return 'yes_generate_notification'
    else:
        return 'no_do_nothing'


def get_token():
    file_dir = os.path.dirname(__file__)
    token_path = os.path.join(file_dir, '../data/credentials/slack.json')
    with open(token_path, 'r') as fp:
        token = json.load(fp)['token']
        return token


def generate_message(**context):
    _, all_comic_info = context['task_instance'].xcom_pull(task_ids='check_comic_info')

    message = ''
    for comic_id, comic_info in all_comic_info.items():
        if comic_info['new_chapter_available']:
            name = comic_info['name']
            latest = comic_info['latest_chapter_num']
            prev = comic_info['previous_chapter_num']
            message += '{} 最新一話： {} 話（上次讀到：{} 話）\n'.format(name, latest, prev)
            message += comic_page_template.format(comic_id) + '\n\n'

    file_dir = os.path.dirname(__file__)
    message_path = os.path.join(file_dir, '../data/message.txt')
    with open(message_path, 'w') as fp:
        fp.write(message)


def get_message_text():
    file_dir = os.path.dirname(__file__)
    message_path = os.path.join(file_dir, '../data/message.txt')
    with open(message_path, 'r') as fp:
        message = fp.read()

    return message


with DAG('comic_app_v3', default_args=default_args, schedule_interval= '@daily') as dag:

    # define tasks
    latest_only = LatestOnlyOperator(task_id='latest_only')

    get_read_history = PythonOperator(
        task_id='get_read_history',
        python_callable=process_metadata,
        op_args=['read'],
        provide_context=True
    )

    check_comic_info = PythonOperator(
        task_id='check_comic_info',
        python_callable=check_comic_info,
        provide_context=True
    )

    decide_what_to_do = BranchPythonOperator(
        task_id='new_comic_available',
        python_callable=decide_what_to_do,
        provide_context=True
    )

    update_read_history = PythonOperator(
        task_id='update_read_history',
        python_callable=process_metadata,
        op_args=['write'],
        provide_context=True
    )

    generate_notification = PythonOperator(
        task_id='yes_generate_notification',
        python_callable=generate_message,
        provide_context=True
    )

    send_notification = SlackAPIPostOperator(
        task_id='send_notification',
        token=get_token(),
        channel='#comic-notification',
        text=get_message_text(),
        icon_url='http://airbnb.io/img/projects/airflow3.png'
    )

    do_nothing = DummyOperator(task_id='no_do_nothing')

    # define workflow
    latest_only >> get_read_history
    get_read_history >> check_comic_info >> decide_what_to_do
    decide_what_to_do >> generate_notification
    decide_what_to_do >> do_nothing
    generate_notification >> send_notification >> update_read_history
