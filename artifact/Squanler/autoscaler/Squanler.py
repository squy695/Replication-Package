import time
import numpy as np
import pandas as pd
import schedule
from util.KubernetesClient import KubernetesClient
from util.PrometheusClient import PrometheusClient
import Config
import math
import os

class Squanler:
    def __init__(self, config: Config):
        self.config = config
        self.k8s_util = KubernetesClient(config)
        self.prom_util = PrometheusClient(config)
        self.scale_interval = config.scale_interval

        self.AOL = 2.6

    def scale(self):
        # Fetch current workload metrics from Prometheus using AOL
        workloads = self.prom_util.get_workload(self.AOL)
        # Initialize resource allocation vector for all services
        Allocation = [0 for svc in self.config.svcs]
        
        for interface, workload in workloads.items():
            CCpR_i = self.config.interfaces[interface][0]
            SLO = self.config.interfaces[interface][1]

            # Calculate required RPS based on workload and SLO constraints
            _RPS = workload / (self.AOL + SLO / 1000)

            # Distribute workload across service components using CCpR matrix
            for j in range(len(CCpR_i)):
                Allocation[j] += CCpR_i[j] * _RPS

        # Apply scaling decisions to Kubernetes cluster
        for i in range(len(self.config.svcs)):
            count = math.ceil(Allocation[i] / self.config.request)
            self.k8s_util.patch_scale(self.config.svcs[i], count)
    
    def start(self):
        print("Squanler goes...")
        
        self.scale()
        schedule.every(self.scale_interval).seconds.do(self.scale)

        time_start = time.time()
        while True:
            time_c = time.time() - time_start
            if time_c > self.config.duration:
                schedule.clear()
                break
            schedule.run_pending()
            
        print("Squanler stops...")
