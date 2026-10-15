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

        # p90 is asked for as one number per API (over every status class counted),
        # not per class: the latency a request sees is a property of the API, and a
        # per-class percentile could not be recombined by weighting afterwards.
        counted = '|'.join(self.config.cycles)
        self.last_p90 = {}

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

            # p90 of the same requests: 90% of them were faster than this
            P90_sql = (
                f"histogram_quantile(0.90, sum(rate(istio_request_duration_milliseconds_bucket{{{selector} request_operation='{i}', response_code=~'{counted}'}}[{interval}])) by (le))"
            )
            responses_P90 = self.execute_prom(self.prom_no_range_url, P90_sql)
            p90 = 0
            if responses_P90:
                value = float(responses_P90[0]['value'][1])
                p90 = 0 if np.isnan(value) else value
            self.last_p90[i] = p90

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

        # Kept for the decision block: every control step prints, next to the
        # allocation, what latency each API is currently seeing.
        # Shape: {api: {status class: [RPS, AIL (ms)]}} (+ p90 in last_p90).
        self.last_res = res

        return res_workload