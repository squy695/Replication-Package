"""Runtime configuration for Squanler.

Three layers, later ones win:

1. the defaults in ``Config.DEFAULTS`` below,
2. a YAML file -- ``config.yaml`` next to this file, or ``$SQUANLER_CONFIG``,
3. environment variables (``SQUANLER_*``, ``PROMETHEUS_URL``, ``KUBECONFIG``),
   which is what the Docker entry point uses.

Every attribute name is identical to the old hand-edited ``Config.py``, so
existing code keeps working; only ``AOL`` and ``no_patch`` are new.
"""
import os
import time

try:
    import yaml
except ImportError:                      # PyYAML ships with the kubernetes client
    yaml = None


def getNowTime():
    return int(round(time.time()))


def _env(name, default=None):
    value = os.environ.get(name)
    return default if value is None or value == '' else value


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def _as_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_list(value, default=None):
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [item.strip() for item in str(value).split(',') if item.strip()]


class Config:

    DEFAULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')

    DEFAULTS = {
        # cluster / application
        'namespace': 'hipster',
        'ingress_namespace': 'istio-system',
        'ingress': 'istio-ingressgateway',
        'cycles': ['2..', '302', '5..'],
        'redict_chain': [['/setCurrency && POST', '/ && GET']],
        # Squanler parameters
        'SLO': 500,
        'AOL': 1.0,
        'scale_interval': 30,
        'duration': 3600,
        'step': 5,
        'request': 150,
        'min_pod': 1,
        'max_pod': 100,
        'no_patch': [],
        # Prometheus
        'prometheus_url': '',
        'prom_range_url': '',
        'prom_no_range_url': '',
        # Label matchers identifying the metrics of the entry point. Left empty,
        # it derives from ingress/ingress_namespace, which is what the paper's
        # cluster exposed; other scrapers label the same series differently
        # (e.g. Istio's addon Prometheus has `app` but no `namespace`), so this
        # is configurable: prom_match: {app: istio-ingressgateway}
        'prom_match': {},
        # Kubernetes access
        'kubeconfig': '',
        'dry_run': False,
        # CCpR matrix
        'svcs': [
            'frontend', 'adservice', 'cartservice', 'checkoutservice',
            'currencyservice', 'emailservice', 'paymentservice',
            'productcatalogservice', 'recommendationservice', 'shippingservice',
        ],
        'interfaces': {},
    }

    def __init__(self, config_file=None):
        self.config_file = None
        for key, value in self.DEFAULTS.items():
            setattr(self, key, value)

        self._load_yaml(_env('SQUANLER_CONFIG') or config_file or self.DEFAULT_FILE)
        ccpr = _env('SQUANLER_CCPR')
        if ccpr:
            self._load_yaml(ccpr, only=('interfaces', 'svcs'))
        self._apply_env()
        self._normalize()

    # -- loading -----------------------------------------------------------
    def _load_yaml(self, path, only=None):
        if not path or not os.path.exists(path):
            if path and not only:
                print("config: %s not found, using defaults and environment" % path)
            return
        if yaml is None:
            raise RuntimeError("PyYAML is required to read %s" % path)
        with open(path, 'r', encoding='utf-8') as handle:
            data = yaml.safe_load(handle) or {}
        for key, value in data.items():
            if only is not None and key not in only:
                continue
            setattr(self, key, value)
        if only is None:
            self.config_file = path

    def _apply_env(self):
        pairs = [
            ('SQUANLER_NAMESPACE', 'namespace', str),
            ('SQUANLER_INGRESS_NAMESPACE', 'ingress_namespace', str),
            ('SQUANLER_INGRESS', 'ingress', str),
            ('SQUANLER_CYCLES', 'cycles', _as_list),
            ('SQUANLER_SLO', 'SLO', _as_int),
            ('SQUANLER_AOL', 'AOL', _as_float),
            ('SQUANLER_INTERVAL', 'scale_interval', _as_int),
            ('SQUANLER_DURATION', 'duration', _as_int),
            ('SQUANLER_STEP', 'step', _as_int),
            ('SQUANLER_CPU_REQUEST', 'request', _as_int),
            ('SQUANLER_MIN_POD', 'min_pod', _as_int),
            ('SQUANLER_MAX_POD', 'max_pod', _as_int),
            ('SQUANLER_NO_PATCH', 'no_patch', _as_list),
            ('SQUANLER_SVCS', 'svcs', _as_list),
            ('SQUANLER_DRY_RUN', 'dry_run', _as_bool),
            ('KUBECONFIG', 'kubeconfig', str),
        ]
        for env_name, attribute, cast in pairs:
            value = _env(env_name)
            if value is not None:
                setattr(self, attribute, cast(value))

        url = _env('PROMETHEUS_URL')
        if url:
            self.prometheus_url = url

    # -- derived values ----------------------------------------------------
    def _normalize(self):
        base = (self.prometheus_url or '').rstrip('/')
        if base:
            if not self.prom_range_url:
                self.prom_range_url = base + '/api/v1/query_range'
            if not self.prom_no_range_url:
                self.prom_no_range_url = base + '/api/v1/query'

        self.AOL = _as_float(self.AOL, 1.0)
        self.SLO = _as_int(self.SLO, 500)
        self.step = _as_int(self.step, 5)
        self.duration = _as_int(self.duration, 3600)
        self.scale_interval = _as_int(self.scale_interval, 30)
        self.request = _as_int(self.request, 150)
        self.min_pod = _as_int(self.min_pod, 1)
        self.max_pod = _as_int(self.max_pod, 100)
        self.dry_run = _as_bool(self.dry_run)
        self.no_patch = _as_list(self.no_patch, []) or []
        self.svcs = _as_list(self.svcs, []) or []
        self.cycles = _as_list(self.cycles, ['2..', '302', '5..'])
        self.kubeconfig = self.kubeconfig or ''

        self.interfaces = {
            str(api): [list(row), _as_int(slo, self.SLO)]
            for api, (row, slo) in (self.interfaces or {}).items()
        }

        # Prometheus label matchers for the entry point's metrics.
        match = _env('SQUANLER_PROM_MATCH')
        if match:
            self.prom_match = {
                key.strip(): value.strip()
                for key, _, value in (item.partition('=') for item in match.split(','))
                if key.strip()
            }
        self.prom_match = {
            str(key): str(value) for key, value in (self.prom_match or {}).items()
        }
        if not self.prom_match:
            # Default to what artifact/deploy/deploy.sh installs: the Istio addon
            # Prometheus exposes `app` on the gateway's metrics but no `namespace`.
            # Add {namespace: <ns>} if your Prometheus does label the namespace.
            self.prom_match = {'app': self.ingress}

        self.start = getNowTime()
        self.end = self.start + self.duration

    def describe(self):
        """One-paragraph summary, useful at startup and in --dry-run mode."""
        return (
            "Squanler config: %s\n"
            "  namespace=%s ingress=%s/%s\n"
            "  APIS=%s\n"
            "  SLO=%s ms  AOL=%s s  interval=%s s  duration=%s s  cpu-request=%s m\n"
            "  pods in [%s, %s]  no_patch=%s  dry_run=%s\n"
            "  prometheus=%s\n"
            "  kubeconfig=%s"
            % (self.config_file or '<defaults+env>', self.namespace, self.ingress_namespace,
               self.ingress, list(self.interfaces.keys()), self.SLO, self.AOL,
               self.scale_interval, self.duration, self.request, self.min_pod,
               self.max_pod, self.no_patch, self.dry_run,
               self.prom_no_range_url or '<unset>', self.kubeconfig or '<in-cluster>')
        )
