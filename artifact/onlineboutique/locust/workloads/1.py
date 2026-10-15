from cProfile import run
import csv
import os
import random
import locust.stats
from locust import HttpUser, between, task, LoadTestShape, events
import time

locust.stats.CSV_STATS_INTERVAL_SEC = 5
locust.stats.CSV_STATS_FLUSH_INTERVAL_SEC = 5

products = [
'0PUK6V6EV0',
'1YMWWN1N4O',
'2ZYFJ3GM2N',
'66VCHSJNUP',
'6E92ZMYYFZ',
'9SIQT8TOJO',
'L9ECAV7KIM',
'LS4PSXUNUM',
'OLJCESPC7Z']


class WebsiteUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @task
    def index(self):
        headers = {"Connection": "close"}
        self.client.get("/", headers=headers)



def _wave(filename):
    """One entry per second: how many users the workload wave asks for.

    Read with the standard library on purpose -- the stock locust image ships no
    pandas, and installing one would need network access when the pod starts.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wiki', filename)
    with open(path, newline='') as handle:
        return [float(row['count']) for row in csv.DictReader(handle)]


class DynamicStress(LoadTestShape):
    """Replay the wave shipped next to this script (see Settings in the paper)."""
    wave_list = _wave('1.csv')
    time_limit = len(wave_list)      # one row per second

    def tick(self):
        run_time = round(self.get_run_time())
        index = int(run_time)

        if run_time < self.time_limit:
            user_count = self.wave_list[index]
            return (round(user_count), 5)
        else:
            return None
        
