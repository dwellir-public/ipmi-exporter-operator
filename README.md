# IPMI Exporter
Prometheus [IPMI Exporter](https://github.com/prometheus-community/ipmi_exporter) for IPMI metrics

## Quickstart

Deploy the `prometheus-ipmi-exporter` charm and relate it to the units you want
to export the metrics:

```bash
$ juju deploy prometheus-ipmi-exporter
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

## Developing

We supply a `Makefile` with a target to build the charm:

```bash
$ make charm
```

## Testing
Run `tox -e ALL` to run unit + integration tests and verify linting.

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



