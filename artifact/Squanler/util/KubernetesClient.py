import os
from kubernetes import client, config
import Config
from subprocess import PIPE, run
import re
import argparse
import json

class KubernetesClient():
    def __init__(self, project_config: Config):
        self.config = project_config
        self.namespace = project_config.namespace
        config.kube_config.load_kube_config(config_file='admin.conf')
        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()
        self.custom_api = client.CustomObjectsApi()

    def patch_scale(self, svc, count):
        if svc in self.config.no_patch:
            return
        count = min(self.config.max_pod, max(self.config.min_pod, int(count)))
        body = {'spec': {'replicas': count}}
        self.apps_api.patch_namespaced_deployment_scale(svc, self.namespace, body)