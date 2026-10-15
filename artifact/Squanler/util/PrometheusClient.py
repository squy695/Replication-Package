import time
import requests
import Config
import pandas as pd
import numpy as np
import math

class PrometheusClient:
    def __init__(self, config: Config):
        self.config = config
        self.namespace = config.namespace
        self.prom_no_range_url = config.prom_no_range_url
        self.prom_range_url = config.prom_range_url
        self.start = config.start
        self.end = config.end
        self.step = config.step
        self.session = requests.Session()

        # No Kubernetes client here: querying Prometheus must work on its own
        # (e.g. from a laptop that can only reach a port-forwarded Prometheus).
        if not self.prom_no_range_url:
            raise RuntimeError(
                "no Prometheus endpoint configured: set prometheus_url in config.yaml "
                "or pass PROMETHEUS_URL=http://host:port"
            )

    def set_time_range(self, start, end):
        self.start = start
        self.end = end

    def execute_prom(self, prom_url, prom_sql):
        """Executes a PromQL query via HTTP GET."""
        response = self.session.get(
            prom_url,
            params={
                "query": prom_sql,
                "start": self.start,
                "end": self.end,
                "step": self.step,
            },
        )
        return response.json()["data"]["result"]

    def get_workload(self, AOL):
        res = {i:{c:[0, 0] for c in self.config.cycles} for i in self.config.CCpR_matrix.keys()}
        interval = '60s'

        # Label matchers of the entry point's metrics: configurable, because the
        # labels differ between Prometheus setups (see Config.prom_match).
        selector = ','.join(
            "%s='%s'" % (key, value)
            for key, value in sorted(self.config.prom_match.items())
        )
        selector = (selector + ',') if selector else ''

        for i in self.config.CCpR_matrix.keys():

            for c in self.config.cycles:
                # Query RPS (requests per second)
                RPS_sql = (
                    f"sum(rate(istio_request_duration_milliseconds_count{{{selector} request_operation='{i}', response_code=~'{c}'}}[{interval}]))"
                )
                # Query AIL (average inside latency)
                AIL_sql = (
                    f"sum(rate(istio_request_duration_milliseconds_sum{{{selector} request_operation='{i}', response_code=~'{c}'}}[{interval}])) / sum(rate(istio_request_duration_milliseconds_count{{{selector} request_operation='{i}', response_code=~'{c}'}}[{interval}]))"
                )

                responses_RPS = self.execute_prom(self.prom_no_range_url, RPS_sql)
                responses_AIL = self.execute_prom(self.prom_no_range_url, AIL_sql)
                
                if responses_AIL == [] or responses_RPS == []:
                    continue

                RPS = 0
                for item in responses_RPS:
                    RPS += float(item['value'][1])
                    
                AIL = float(responses_AIL[0]['value'][1]) if not np.isnan(float(responses_AIL[0]['value'][1])) else 0
                
                res[i][c] = [RPS, AIL]

        # Handle redirection chains
        for chain in self.config.redict_chain:
            for i in range(len(chain) - 1):
                if i == 0:
                    res[chain[len(chain) - 2 - i]]['302'][1] += res[chain[len(chain) - 1 - i]]['2..'][1]
                else:
                    res[chain[len(chain) - 2 - i]]['302'][1] += res[chain[len(chain) - 1 - i]]['302'][1]
                if i == len(chain) - 2:
                    res[chain[1 + i]]['2..'][0] -= res[chain[i]]['302'][0]
                else:
                    res[chain[1 + i]]['302'][0] -= res[chain[i]]['302'][0]

        # Calculate final workload for each interface
        res_workload = {}
        for i in res.keys():
            workload = 0
            for c in res[i].keys():
                workload += res[i][c][0] * (res[i][c][1] / 1000 + AOL)
            res_workload[i] = workload
        
        return res_workload