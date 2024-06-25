#!/usr/bin/env python3
# Copyright 2024 Dwellir AB
# See LICENSE file for licensing details.

"""Prometheus IPMI Exporter Charm."""

import logging
import os
import re
import shlex
import shutil
import subprocess
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib import request
import subprocess as sp
from jinja2 import Environment, FileSystemLoader

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus

from prometheus_ipmi_exporter import Prometheus

# Grafana Agent
from charms.grafana_agent.v0.cos_agent import COSAgentProvider

logger = logging.getLogger(__name__)


class IPMIExporterCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        """Initialize charm."""
        super().__init__(*args)

        self.prometheus = Prometheus(self, "prometheus")

        # Grafana Agent
        self.cos_agent_provider = COSAgentProvider(
            self,
            relation_name="grafana-agent",
            metrics_endpoints=[{"port": 9290, "path": "/metrics"}],
            refresh_events=[self.on.upgrade_charm],
            dashboard_dirs="./src/grafana_dashboards",
            logs_rules_dir="./src/alert_rules/loki",
            metrics_rules_dir="./src/alert_rules/prometheus"
        )

        # juju core hooks
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.stop, self._on_stop)

    @property
    def port(self):
        """Return the port that node-exporter listens to."""
        return self.model.config.get("listen-address").split(":")[1]

    def _on_install(self, event):
        logger.debug("## Installing charm")
        self.unit.status = MaintenanceStatus("Installing ipmi-exporter")
        la = self.config.get('listen-address')
        zev = self.model.config.get("ipmi-exporter-version")
        _install_ipmi_exporter(version=str(zev), listen_address=str(la))
        self._set_charm_version()
        self.unit.status = ActiveStatus("ipmi-exporter installed")

    def _on_upgrade_charm(self, event):
        """Perform upgrade operations."""
        logger.debug("## Upgrading charm")
        self.unit.status = MaintenanceStatus("Upgrading ipmi-exporter")
        self._set_charm_version()

        self.unit.status = ActiveStatus("ipmi-exporter upgraded")

    def _on_config_changed(self, event):
        """Handle configuration updates."""
        logger.debug("## Configuring charm")

        params = dict()
        params["listen_address"] = self.model.config.get("listen-address")

        logger.debug(f"## Configuration options: {params}")
        _render_sysconfig(params)
        subprocess.call(["systemctl", "restart", "ipmi_exporter"])

        self.prometheus.set_host_port()

    def _on_start(self, event):
        logger.debug("## Starting daemon")
        subprocess.call(["systemctl", "start", "ipmi_exporter"])
        self.unit.status = ActiveStatus("ipmi-exporter started")

    def _on_stop(self, event):
        logger.debug("## Stopping daemon")
        subprocess.call(["systemctl", "stop", "ipmi_exporter"])
        subprocess.call(["systemctl", "disable", "ipmi_exporter"])
        _uninstall_ipmi_exporter()

    def _set_charm_version(self):
        """Set the application version for Juju Status."""
        command = ['/usr/bin/ipmi_exporter', '--version']
        output = sp.run(command, capture_output=True, text=True).stdout
        version = re.search(r'([0-9]+.[0-9]+.[0-9]+)', output).group(0)
        self.unit.set_workload_version(version)


def _install_ipmi_exporter(version: str, arch: str = "amd64", listen_address: str = "0.0.0.0:9290"):
    """Download appropriate files and install node-exporter.

    This function downloads the package, extracts it to /usr/bin/, create
    node-exporter user and group, and creates the systemd service unit with listen-address.

    Args:
        version: a string representing the version to install.
        arch: the hardware architecture (e.g. amd64, armv7).
    """

    logger.debug(f"## Installing ipmi_exporter {version}")

    # Download file
    url = f"https://github.com/prometheus-community/ipmi_exporter/releases/download/v{version}/ipmi_exporter-{version}.linux-{arch}.tar.gz"
    logger.debug(f"## Downloading {url}")
    output = Path("/tmp/ipmi-exporter.tar.gz")
    fname, headers = request.urlretrieve(url, output)

    # Extract it
    tar = tarfile.open(output, 'r')
    with TemporaryDirectory(prefix="charmtmp") as tmp_dir:
        logger.debug(f"## Extracting {tar} to {tmp_dir}")
        tar.extractall(path=tmp_dir)

        logger.debug("## Installing ipmi_exporter")
        source = Path(tmp_dir) / f"ipmi_exporter-{version}.linux-{arch}/ipmi_exporter"
        shutil.copy2(source, "/usr/bin/ipmi_exporter")

    # clean up
    output.unlink()

    _install_freeipmi()
    _create_ipmi_exporter_user_group()
    _create_ipmi_exporter_configuration()
    _create_sudoers_file_for_ipmi_exporter()
    _create_systemd_service_unit()
    _render_sysconfig({"listen_address": listen_address})


def _uninstall_ipmi_exporter():
    logger.debug("## Uninstalling ipmi-exporter")

    # remove files and folders
    Path("/usr/bin/ipmi_exporter").unlink()
    Path("/etc/systemd/system/ipmi_exporter.service").unlink()
    Path("/etc/sysconfig/ipmi_exporter").unlink()
    Path("/etc/ipmi_exporter/ipmi_exporter.yaml").unlink()
    shutil.rmtree(Path("/var/lib/ipmi_exporter/"))

    # remove user and group
    user = "ipmi_exporter"
    group = "ipmi_exporter"
    subprocess.call(["userdel", user])
    subprocess.call(["groupdel", group])


def _create_ipmi_exporter_user_group():
    logger.debug("## Creating ipmi_exporter group")
    group = "ipmi_exporter"
    cmd = f"groupadd {group}"
    subprocess.call(shlex.split(cmd))

    logger.debug("## Creating ipmi_exporter user")
    user = "ipmi_exporter"
    cmd = f"useradd --system --no-create-home --gid {group} --shell /usr/sbin/nologin {user}"
    subprocess.call(shlex.split(cmd))


def _create_ipmi_exporter_configuration():
    logger.debug("## Creating ipmi_exporter configuration file")
    charm_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = Path(charm_dir) / "templates"
    config = "ipmi_exporter.yaml"

    config_path = Path("/etc/ipmi_exporter/")
    if not config_path.exists():
        config_path.mkdir()

    shutil.copyfile(template_dir / config, f"/etc/ipmi_exporter/{config}")


def _install_freeipmi():
    logger.debug("## Checking if freeipmi is installed")
    result = subprocess.run(["dpkg", "-l", "freeipmi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if "no packages found" not in result.stdout.decode().lower():
        logger.debug("## Installing freeipmi")
        subprocess.call(["apt-get", "install", "-y", "freeipmi"])
    else:
        logger.debug("## freeipmi already installed")


def _create_sudoers_file_for_ipmi_exporter():
    # Create a sudoers file for ipmi_exporter to allow it to run freeipmi commands
    logger.debug("## Creating sudoers file for ipmi_exporter")
    sudoers = "/etc/sudoers.d/ipmi_exporter"
    with open(sudoers, "w") as f:
        f.write("""ipmi_exporter ALL = NOPASSWD: /usr/sbin/ipmimonitoring,\
                              /usr/sbin/ipmi-sensors,\
                              /usr/sbin/ipmi-dcmi,\
                              /usr/sbin/ipmi-raw,\
                              /usr/sbin/bmc-info,\
                              /usr/sbin/ipmi-chassis,\
                              /usr/sbin/ipmi-sel                
                """)


def _create_systemd_service_unit():
    logger.debug("## Creating systemd service unit for ipmi_exporter")
    charm_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = Path(charm_dir) / "templates"

    service = "ipmi_exporter.service"
    shutil.copyfile(template_dir / service, f"/etc/systemd/system/{service}")

    subprocess.call(["systemctl", "daemon-reload"])
    subprocess.call(["systemctl", "enable", service])


def _render_sysconfig(context: dict) -> None:
    """Render the sysconfig file.

    `context` should contain the following keys:
        listen_address: a string specifiyng the address to listen to, e.g. 0.0.0.0:9134
    """
    logger.debug("## Writing sysconfig file")

    charm_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = Path(charm_dir) / "templates"
    template_file = "ipmi_exporter.tmpl"

    sysconfig = Path("/etc/sysconfig/")
    if not sysconfig.exists():
        sysconfig.mkdir()

    varlib = Path("/var/lib/ipmi_exporter")
    textfile_dir = varlib / "textfile_collector"
    if not textfile_dir.exists():
        textfile_dir.mkdir(parents=True)
    shutil.chown(varlib, user="ipmi_exporter", group="ipmi_exporter")
    shutil.chown(textfile_dir, user="ipmi_exporter", group="ipmi_exporter")

    environment = Environment(loader=FileSystemLoader(template_dir))
    template = environment.get_template(template_file)

    target = sysconfig / "ipmi_exporter"
    if target.exists():
        target.unlink()
    target.write_text(template.render(context))


if __name__ == "__main__":
    main(IPMIExporterCharm)

