import math
import time

import schedule

import Config
from util.KubernetesClient import KubernetesClient
from util.PrometheusClient import PrometheusClient


class Squanler:
    def __init__(self, config: Config):
        self.config = config
        self.k8s_util = KubernetesClient(config)
        self.prom_util = PrometheusClient(config)
        self.scale_interval = config.scale_interval

        # Average outside latency: a runtime parameter (config.yaml / SQUANLER_AOL).
        self.AOL = config.AOL
        self.round = 0

    def _aol_label(self):
        """The AOL this decision assumes, as the paper writes it: `1s`, `2.6s`."""
        return '%gs' % self.AOL

    def _print_latency(self):
        """What each API is currently seeing, next to the SLO it is given.

        All three figures come from the sample this decision was made on: `mean
        AIL` is the request-weighted average latency of the status classes
        Squanler counts, `p90` the 90th percentile of the same requests, `req/s`
        their throughput. An API with no counted traffic has no latency to show.
        """
        res = getattr(self.prom_util, 'last_res', {}) or {}
        p90s = getattr(self.prom_util, 'last_p90', {}) or {}
        print("  latency each API sees (against its SLO):")
        if not res:
            print("    no metric sample was taken this round")
            return
        print("    %-24s %8s %9s %9s %7s"
              % ('API', 'req/s', 'mean AIL', 'p90', 'SLO'))
        for interface in sorted(res,
                                key=lambda api: -sum(c[0] for c in res[api].values())):
            rps = sum(class_rps for class_rps, _ in res[interface].values())
            weighted = sum(class_rps * class_ail
                           for class_rps, class_ail in res[interface].values())
            ail_str = '%.1f ms' % (weighted / rps) if rps > 0 else '-'
            p90 = p90s.get(interface, 0)
            p90_str = '%.1f ms' % p90 if p90 > 0 else '-'
            print("    %-24s %8.2f %9s %9s %4d ms"
                  % (interface, rps, ail_str, p90_str,
                     self.config.CCpR_matrix[interface][1]))

    def scale(self):
        """One control step: quantify the workload, report it, then act on it."""
        self.round += 1

        # Fetch current metrics from Prometheus and reverse-quantify the workload
        workloads = self.prom_util.get_workload(self.AOL)

        # Resource demand of every service, from the CCpR matrix
        allocation = [0.0 for _ in self.config.svcs]
        rps_targets = {}
        for interface, workload in workloads.items():
            ccp_r = self.config.CCpR_matrix[interface][0]
            slo = self.config.CCpR_matrix[interface][1]
            # Throughput that this workload implies if the SLO is to be met
            rps_targets[interface] = workload / (self.AOL + slo / 1000.0)
            for j in range(len(ccp_r)):
                allocation[j] += ccp_r[j] * rps_targets[interface]

        mode = 'dry-run' if self.config.dry_run else 'live'
        # The AOL is not repeated here: every workload below quotes the one it
        # assumes, so the header would only be a second copy of the same number.
        print("\n=== decision #%d   %s   SLO=%d ms  mode=%s ===" % (
            self.round, time.strftime('%H:%M:%S'), self.config.SLO, mode))

        print(" our represented workload from the metrics:")
        for interface, workload in sorted(workloads.items(),
                                          key=lambda item: -item[1]):
            # The number alone is not the workload: it is the workload *for the
            # AOL assumed*, which is why the AOL is quoted with it -- the same
            # pressure is `52.50 (1s)` or `26.25 (2s)` (the paper's eq. for the
            # workload).
            shown = "%.2f (%s)" % (workload, self._aol_label())
            print("    %-24s workload=%-12s (= %6.2f req/s at the SLO)"
                  % (interface, shown, rps_targets[interface]))

        print("  allocation (service -> instances):")
        for i, svc in enumerate(self.config.svcs):
            cpu = allocation[i]
            count = int(math.ceil(cpu / self.config.request)) if self.config.request else 0
            applied = self.k8s_util.patch_scale(svc, count)
            if applied is None:
                note = '(skipped: no_patch)'
                shown = count
            elif applied != count:
                note = '(clamped to [%d, %d])' % (self.config.min_pod, self.config.max_pod)
                shown = applied
            else:
                note = ''
                shown = applied
            print("    %-24s %8.1f CPU-m / %d m  ->  %3d instance(s)  %s"
                  % (svc, cpu, self.config.request, shown, note))

        # Closing line of every decision block: what the cluster looks like right
        # now, which is what the next decision will be made on.
        self._print_latency()

    def start(self):
        print("Squanler goes...")
        print(self.config.describe())
        print("one control step every %d s for %d s; Ctrl+C stops early"
              % (self.config.scale_interval, self.config.duration))
        if self.config.dry_run:
            print("dry-run: decisions are logged, no deployment is patched")

        try:
            self.scale()
            schedule.every(self.scale_interval).seconds.do(self.scale)

            time_start = time.time()
            while True:
                if time.time() - time_start > self.config.duration:
                    schedule.clear()
                    break
                schedule.run_pending()
                time.sleep(0.2)
        except KeyboardInterrupt:
            schedule.clear()

        print("\nSquanler stops after %d decision(s)." % self.round)
