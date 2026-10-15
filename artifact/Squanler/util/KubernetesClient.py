import os

from kubernetes import client, config

import Config


class KubernetesClient():
    """Thin wrapper around the Deployment scale sub-resource.

    The kubeconfig is looked up in this order: ``Config.kubeconfig`` (a YAML
    key, or the ``KUBECONFIG`` environment variable, which is also what the
    Docker entry point mounts), then the in-cluster service account. With
    ``dry_run`` enabled nothing is patched -- the decisions are only logged,
    which lets a reviewer run Squanler without touching a cluster.
    """

    def __init__(self, project_config: Config):
        self.config = project_config
        self.namespace = project_config.namespace
        self.dry_run = bool(getattr(project_config, 'dry_run', False))
        self.patched = {}

        kubeconfig = getattr(project_config, 'kubeconfig', '') or os.environ.get('KUBECONFIG', '')
        self.core_api = self.apps_api = self.custom_api = None
        try:
            if kubeconfig and os.path.exists(kubeconfig):
                config.load_kube_config(config_file=kubeconfig)
                self.auth = 'kubeconfig:%s' % kubeconfig
            else:
                config.load_incluster_config()
                self.auth = 'in-cluster service account'
            self.core_api = client.CoreV1Api()
            self.apps_api = client.AppsV1Api()
            self.custom_api = client.CustomObjectsApi()
        except Exception as exc:                     # noqa: BLE001
            # dry-run only needs Prometheus: no cluster credentials required
            if not self.dry_run:
                raise
            self.auth = 'none (dry-run)'
            print("kube client unavailable (%s); dry-run continues" % exc)

    def patch_scale(self, svc, count):
        """Set the replica count of one service.

        Returns the applied count, or None when the service is excluded by
        ``no_patch`` (the caller reports both cases; nothing is printed here).
        """
        if svc in self.config.no_patch:
            return None
        count = min(self.config.max_pod, max(self.config.min_pod, int(count)))
        if not self.dry_run:
            body = {'spec': {'replicas': count}}
            self.apps_api.patch_namespaced_deployment_scale(svc, self.namespace, body)
        self.patched[svc] = count
        return count
