import time
import requests
import Config
from util.KubernetesClient import KubernetesClient
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
        
        self.kube_util = KubernetesClient(config)

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
        res = {i:{c:[0, 0] for c in self.config.cycles} for i in self.config.interfaces.keys()}
        interval = '60s'
        
        for i in self.config.interfaces.keys():
            
            for c in self.config.cycles:
                # Query RPS (requests per second)
                RPS_sql = (
                    f"sum(rate(istio_request_duration_milliseconds_count{{app='{self.config.ingress}', namespace='{self.config.ingress_namespace}', request_operation='{i}', response_code=~'{c}'}}[{interval}]))"
                )
                # Query AIL (average inside latency)
                AIL_sql = (
                    f"sum(rate(istio_request_duration_milliseconds_sum{{app='{self.config.ingress}',namespace='{self.config.ingress_namespace}', request_operation='{i}', response_code=~'{c}'}}[{interval}])) / sum(rate(istio_request_duration_milliseconds_count{{app='{self.config.ingress}', namespace='{self.config.ingress_namespace}', request_operation='{i}', response_code=~'{c}'}}[{interval}]))"
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
            ECCU = 0
            for c in res[i].keys():
                ECCU += res[i][c][0] * (res[i][c][1] / 1000 + AOL)
            res_workload[i] = ECCU
        
        return res_workload