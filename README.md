# IPMI Exporter
Prometheus [IPMI Exporter](https://github.com/prometheus-community/ipmi_exporter) for IPMI metrics

Supported bases: Ubuntu 22.04, 24.04, and 26.04 on amd64. Ubuntu 20.04 is no longer supported.

## Quickstart

Deploy the `prometheus-ipmi-exporter` charm and relate it to the units you want
to export the metrics:

```bash
$ juju deploy prometheus-ipmi-exporter ipmi-exporter
$ juju relate prometheus-ipmi-exporter tiny-bash
```

The charm can register it's scrape target with Prometheus via relation to the
[Prometheus charm](https://charmhub.io/prometheus2):

```bash
$ juju deploy prometheus
$ juju relate prometheus-ipmi-exporter prometheus
```

The charm supports [cos-lite](https://charmhub.io/topics/canonical-observability-stack/editions/lite) 
```bash
$ juju relate prometheus-ipmi-exporter grafana-agent
```

## Preferred metrics relation

The preferred relation for new integrations is `metrics-endpoint` with interface
`prometheus_scrape`.

This path preserves Juju topology labels through the standard provider library
and works directly with `alloy-vm:metrics-endpoint`. Use it when metrics will
be forwarded onward to a remote write backend such as `mimir-vm`.

```bash
$ juju deploy prometheus-ipmi-exporter
$ juju deploy alloy-vm --config enable-syslogreceivers=true
$ juju integrate prometheus-ipmi-exporter:metrics-endpoint alloy-vm:metrics-endpoint
$ juju integrate alloy-vm:send-remote-write mimir-vm:receive-remote-write
```

Compatibility note:

- `prometheus` remains available for older Prometheus-specific deployments
- `metrics-endpoint` is the preferred relation when you want Juju topology preserved end to end

## Developing

Building requires Charmcraft 4.3 or newer and LXD. Dependencies are defined in
`pyproject.toml` and locked in `uv.lock`. We supply a `Makefile` with a target to
build the charm for all supported bases:

```bash
$ make charm
```

To build only for Ubuntu 26.04:

```bash
charmcraft pack --platform ubuntu@26.04:amd64
```

The Grafana Agent library is vendored from
[canonical/grafana-agent-operator, library patch 28](https://github.com/canonical/grafana-agent-operator/blob/de375d4e8498cae360d1011ce76d7c0ecfc1be3b/lib/charms/grafana_agent/v0/cos_agent.py),
which supports Pydantic 2 for Python 3.14 compatibility.

## Testing
Run `uv tool run --with tox-uv tox -e unit` for unit tests and `make lint` for
linting. CI runs unit tests on Python 3.10, 3.12, and 3.14, matching the supported
Ubuntu bases. The legacy integration suite still references the node exporter
charm and needs updating before it can validate IPMI exporter deployments.

## Contact

**We want to hear from you!**

Email us @ [info@dwellir.com](mailto:info@dwellir.com)

## Bugs

In the case things aren't working as expected, please
[file a bug](https://github.com/dwellir-public/#/issues).

## License

The charm is maintained under the MIT license. See `LICENSE` file in this
directory for full preamble.

Copyright &copy; Dwellir AB 2024

## Attributions 

Omnivector Solutions which this charm largely builds on.

Also to https://github.com/pdf/zfs_exporter


