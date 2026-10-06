import time

def getNowTime():
    return int(round(time.time()))

class Config:
    def __init__(self):
        
        # You can enhance the cycles configuration by adding additional status codes that may be relevant to your application's entry interfaces.
        # For now, we only consider these three status codes
        self.cycles = ['2..', '302', '5..']
        
        # The namespace of your application.
        self.namespace = 'hipster'
        # The namespace of your cluster's entry point (typically istio-ingressgateway).
        self.ingress_namespace = 'istio-system'
        # The name of your cluster's entry point.
        self.ingress = 'istio-ingressgateway'
        
        # The call chain relationships between your application's entry interfaces (parent -> child).
        self.redict_chain = [
            ['/setCurrency && POST', '/ && GET'],
        ]

        # The target end-to-end latency.
        self.SLO = 500
        # The execution interval.
        self.scale_interval = 30
        # The CPU request for the service.
        self.request = 150

        # The services.
        self.svcs = ['frontend','adservice','cartservice','checkoutservice','currencyservice','emailservice','paymentservice','productcatalogservice','recommendationservice','shippingservice']
        
        # CCpR matrices vary across different clusters for the same benchmark.
        # To improve Squanler's control precision for a benchmark in your current cluster, 
        # follow these steps to collect your own CCpR matrix:
        # Example: Collecting CCpR for service 'frontend' on API "/ && GET"
        # 1. Inject workload into API "/ && GET" (corresponding to onlineboutique\locust\1.py).
        # 2. After a stabilization period, query: ('frontend' CPU usage) / ("/ && GET" RPS):
        # sum(rate(container_cpu_usage_seconds_total{namespace="hipster", pod=~".*frontend.*", container!~'POD|istio-proxy'}[90s])) * 1000
        # /
        # sum(rate(istio_request_duration_milliseconds_count{destination_app="frontend", namespace="hipster", request_operation="/ && GET", response_code!~"5.."}[90s]))
        # 3. Fill the resulting average value into self.interfaces['/ && GET'][0] (where index 0 corresponds to 'frontend' in self.svcs).
        self.interfaces = {
            "/ && GET": [[4.58,0.58,0.68,0.15,6.86,0.40,0.16,0.47,0.39,0.21], self.SLO],
            "/product/{id} && GET": [[8.42, 0.47, 1.06, 0.08, 4.35, 0.09, 1.9, 2.8, 2.5, 0.05], self.SLO],
            '/cart && GET': [[7.23, 0.03, 1.23, 0.72, 3.24, 0.11, 1.1, 2.14, 2.14, 0.5], self.SLO],
            '/cart/checkout && POST': [[7.69, 0.05, 3.5, 23.36, 10.66, 2.4, 0.52, 2.8, 8.6, 0.93], self.SLO],
            '/setCurrency && POST': [[9.1, 0.04, 1.87, 1.8, 19.12, 0, 0, 0.89, 3.7, 0], self.SLO],
        }

        # the maximum and minimum allowable instance count.
        self.max_pod = 100
        self.min_pod = 1

        # the duration of the experiment.
        self.duration = 1 * 60 * 60
        self.start = getNowTime()
        self.end = self.start + self.duration
        self.step = 5

        # replace with the address of your Prometheus instance.
        self.prom_range_url = "http://XXX.XXX.XX.XXX:XXXXX//api/v1/query_range"
        self.prom_no_range_url = "http://XXX.XXX.XX.XXX:XXXXX//api/v1/query"