#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import cmk.gui.bi as bi
import cmk.gui.watolib as watolib
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato import (
    IndividualOrStoredPassword,
    RulespecGroup,
    monitoring_macro_help,
    rulespec_group_registry,
    rulespec_registry,
    HostRulespec,
)
from cmk.gui.valuespec import (
    ID,
    Age,
    Alternative,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DropdownChoice,
    FixedValue,
    Float,
    HTTPUrl,
    Integer,
    ListChoice,
    ListOf,
    ListOfStrings,
    MonitoringState,
    Password,
    RegExp,
    RegExpUnicode,
    TextAscii,
    TextUnicode,
    Transform,
    Tuple,
)
from cmk.gui.plugins.wato.utils import (
    PasswordFromStore,)
from cmk.utils import aws_constants


@rulespec_group_registry.register
class RulespecGroupDatasourcePrograms(RulespecGroup):
    @property
    def name(self):
        return "datasource_programs"

    @property
    def title(self):
        return _("Datasource Programs")

    @property
    def help(self):
        return _("Specialized agents, e.g. check via SSH, ESX vSphere, SAP R/3")


def _valuespec_datasource_programs():
    return TextAscii(
        title=_("Individual program call instead of agent access"),
        help=_("For agent based checks Check_MK allows you to specify an alternative "
               "program that should be called by Check_MK instead of connecting the agent "
               "via TCP. That program must output the agent's data on standard output in "
               "the same format the agent would do. This is for example useful for monitoring "
               "via SSH.") + monitoring_macro_help() +
        _("This option can only be used with the permission \"Can add or modify executables\"."),
        label=_("Command line to execute"),
        empty_text=_("Access Check_MK Agent via TCP"),
        size=80,
        attrencode=True,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="datasource_programs",
        valuespec=_valuespec_datasource_programs,
    ))


def _valuespec_special_agents_ddn_s2a():
    return Dictionary(
        elements=[
            ("username", TextAscii(title=_(u"Username"), allow_empty=False)),
            ("password", Password(title=_(u"Password"), allow_empty=False)),
            ("port", Integer(title=_(u"Port"), default_value=8008)),
        ],
        optional_keys=["port"],
        title=_(u"DDN S2A"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:ddn_s2a",
        valuespec=_valuespec_special_agents_ddn_s2a,
    ))


def _special_agents_kubernetes_transform(value):
    if 'infos' not in value:
        value['infos'] = ['nodes']
    if 'no-cert-check' not in value:
        value['no-cert-check'] = False
    return value


def _valuespec_special_agents_kubernetes():
    return Transform(
        Dictionary(
            elements=[
                ("token", IndividualOrStoredPassword(
                    title=_("Token"),
                    allow_empty=False,
                )),
                ("no-cert-check",
                 Alternative(title=_("SSL certificate verification"),
                             elements=[
                                 FixedValue(False, title=_("Verify the certificate"), totext=""),
                                 FixedValue(True,
                                            title=_("Ignore certificate errors (unsecure)"),
                                            totext=""),
                             ],
                             default_value=False)),
                ("infos",
                 ListChoice(choices=[
                     ("nodes", _("Nodes")),
                     ("services", _("Services")),
                     ("ingresses", _("Ingresses")),
                     ("deployments", _("Deployments")),
                     ("pods", _("Pods")),
                     ("endpoints", _("Endpoints")),
                     ("daemon_sets", _("Daemon sets")),
                     ("stateful_sets", _("Stateful sets")),
                     ("jobs", _("Job")),
                 ],
                            default_value=[
                                "nodes",
                                "endpoints",
                                "ingresses",
                            ],
                            allow_empty=False,
                            title=_("Retrieve information about..."))),
                ("port",
                 Integer(title=_(u"Port"),
                         help=_("If no port is given a default value of 443 will be used."),
                         default_value=443)),
                ("url-prefix",
                 HTTPUrl(title=_("Custom URL prefix"),
                         help=_("Defines the scheme (either HTTP or HTTPS) and host part "
                                "of Kubernetes API calls like e.g. \"https://example.com\". "
                                "If no prefix is specified HTTPS together with the IP of "
                                "the host will be used."),
                         allow_empty=False)),
                ("path-prefix",
                 TextAscii(
                     title=_("Custom path prefix"),
                     help=_(
                         "Specifies a URL path prefix which is prepended to the path in calls "
                         "to the Kubernetes API. This is e.g. useful if Rancher is used to "
                         "manage Kubernetes clusters. If no prefix is given \"/\" will be used."),
                     allow_empty=False)),
            ],
            optional_keys=["port", "url-prefix", "path-prefix"],
            title=_(u"Kubernetes"),
            help=_(
                "This rule selects the Kubenetes special agent for an existing Checkmk host. "
                "If you want to monitor multiple Kubernetes clusters "
                "we strongly recommend to set up "
                "<a href=\"wato.py?mode=edit_ruleset&varname=piggyback_translation\">Piggyback translation rules</a> "
                "to avoid name collisions. Otherwise e.g. Pods with the same name in "
                "different Kubernetes clusters cannot be distinguished."),
        ),
        forth=_special_agents_kubernetes_transform,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:kubernetes",
        valuespec=_valuespec_special_agents_kubernetes,
    ))


def _factory_default_special_agents_vsphere():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_vsphere():
    return Transform(valuespec=Dictionary(
        elements=[
            ("user", TextAscii(
                title=_("vSphere User name"),
                allow_empty=False,
            )),
            ("secret", IndividualOrStoredPassword(
                title=_("vSphere secret"),
                allow_empty=False,
            )),
            ("direct",
             DropdownChoice(
                 title=_("Type of query"),
                 choices=[
                     (True, _("Queried host is a host system")),
                     ("hostsystem_agent",
                      _("Queried host is a host system with Check_MK Agent installed")),
                     (False, _("Queried host is the vCenter")),
                     ("agent", _("Queried host is the vCenter with Check_MK Agent installed")),
                 ],
                 default_value=True,
             )),
            ("tcp_port",
             Integer(
                 title=_("TCP Port number"),
                 help=_("Port number for HTTPS connection to vSphere"),
                 default_value=443,
                 minvalue=1,
                 maxvalue=65535,
             )),
            ("ssl",
             Alternative(
                 title=_("SSL certificate checking"),
                 elements=[
                     FixedValue(False, title=_("Deactivated"), totext=""),
                     FixedValue(True, title=_("Use hostname"), totext=""),
                     TextAscii(
                         title=_("Use other hostname"),
                         help=
                         _("The IP of the other hostname needs to be the same IP as the host address"
                          ))
                 ],
                 default_value=False)),
            ("timeout",
             Integer(
                 title=_("Connect Timeout"),
                 help=_(
                     "The network timeout in seconds when communicating with vSphere or "
                     "to the Check_MK Agent. The default is 60 seconds. Please note that this "
                     "is not a total timeout but is applied to each individual network transation."
                 ),
                 default_value=60,
                 minvalue=1,
                 unit=_("seconds"),
             )),
            ("use_pysphere",
             Checkbox(
                 title=_("Compatibility mode"),
                 label=_("Support ESX 4.1 (using slower PySphere implementation)"),
                 true_label=_("Support 4.1"),
                 false_label=_("fast"),
                 help=_("The current very performant implementation of the ESX special agent "
                        "does not support older ESX versions than 5.0. Please use the slow "
                        "compatibility mode for those old hosts."),
             )),
            ("infos",
             Transform(
                 ListChoice(
                     choices=[
                         ("hostsystem", _("Host Systems")),
                         ("virtualmachine", _("Virtual Machines")),
                         ("datastore", _("Datastores")),
                         ("counters", _("Performance Counters")),
                         ("licenses", _("License Usage")),
                     ],
                     default_value=["hostsystem", "virtualmachine", "datastore", "counters"],
                     allow_empty=False,
                 ),
                 forth=lambda v: [x.replace("storage", "datastore") for x in v],
                 title=_("Retrieve information about..."),
             )),
            ("skip_placeholder_vms",
             Checkbox(
                 title=_("Placeholder VMs"),
                 label=_("Do no monitor placeholder VMs"),
                 default_value=True,
                 true_label=_("ignore"),
                 false_label=_("monitor"),
                 help=
                 _("Placeholder VMs are created by the Site Recovery Manager(SRM) and act as backup "
                   "virtual machines in case the default vm is unable to start. This option tells the "
                   "vsphere agent to exclude placeholder vms in its output."),
             )),
            ("host_pwr_display",
             DropdownChoice(
                 title=_("Display ESX Host power state on"),
                 choices=[
                     (None, _("The queried ESX system (vCenter / Host)")),
                     ("esxhost", _("The ESX Host")),
                     ("vm", _("The Virtual Machine")),
                 ],
                 default_value=None,
             )),
            ("vm_pwr_display",
             DropdownChoice(
                 title=_("Display VM power state <i>additionally</i> on"),
                 help=_("The power state can be displayed additionally either "
                        "on the ESX host or the VM. This will result in services "
                        "for <i>both</i> the queried system and the ESX host / VM. "
                        "By disabling the unwanted services it is then possible "
                        "to configure where the services are displayed."),
                 choices=[
                     (None, _("The queried ESX system (vCenter / Host)")),
                     ("esxhost", _("The ESX Host")),
                     ("vm", _("The Virtual Machine")),
                 ],
                 default_value=None,
             )),
            ("snapshot_display",
             DropdownChoice(
                 title=_("<i>Additionally</i> display snapshots on"),
                 help=_("The created snapshots can be displayed additionally either "
                        "on the ESX host or the vCenter. This will result in services "
                        "for <i>both</i> the queried system and the ESX host / vCenter. "
                        "By disabling the unwanted services it is then possible "
                        "to configure where the services are displayed."),
                 choices=[
                     (None, _("The Virtual Machine")),
                     ("esxhost", _("The ESX Host")),
                     ("vCenter", _("The queried ESX system (vCenter / Host)")),
                 ],
                 default_value=None,
             )),
            ("vm_piggyname",
             DropdownChoice(
                 title=_("Piggyback name of virtual machines"),
                 choices=[
                     ("alias", _("Use the name specified in the ESX system")),
                     ("hostname",
                      _("Use the VMs hostname if set, otherwise fall back to ESX name")),
                 ],
                 default_value="alias",
             )),
            ("spaces",
             DropdownChoice(
                 title=_("Spaces in hostnames"),
                 choices=[
                     ("cut", _("Cut everything after first space")),
                     ("underscore", _("Replace with underscores")),
                 ],
                 default_value="underscore",
             )),
        ],
        optional_keys=[
            "tcp_port",
            "timeout",
            "vm_pwr_display",
            "host_pwr_display",
            "snapshot_display",
            "vm_piggyname",
        ],
    ),
                     title=_("Check state of VMWare ESX via vSphere"),
                     help=_(
                         "This rule selects the vSphere agent instead of the normal Check_MK Agent "
                         "and allows monitoring of VMWare ESX via the vSphere API. You can configure "
                         "your connection settings here."),
                     forth=lambda a: dict([("skip_placeholder_vms", True), ("ssl", False),
                                           ("use_pysphere", False),
                                           ("spaces", "underscore")] + a.items()))


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_vsphere(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:vsphere",
        valuespec=_valuespec_special_agents_vsphere,
    ))


def _valuespec_special_agents_hp_msa():
    return Dictionary(
        elements=[
            ("username", TextAscii(
                title=_("Username"),
                allow_empty=False,
            )),
            ("password", Password(
                title=_("Password"),
                allow_empty=False,
            )),
        ],
        optional_keys=False,
        title=_("Check HP MSA via Web Interface"),
        help=_("This rule selects the Agent HP MSA instead of the normal Check_MK Agent "
               "which collects the data through the HP MSA web interface"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:hp_msa",
        valuespec=_valuespec_special_agents_hp_msa,
    ))


def _special_agents_ipmi_sensors_vs_ipmi_common_elements():
    return [
        ("username", TextAscii(
            title=_("Username"),
            allow_empty=False,
        )),
        ("password", Password(
            title=_("Password"),
            allow_empty=False,
        )),
        ("privilege_lvl",
         TextAscii(
             title=_("Privilege Level"),
             help=_("Possible are 'user', 'operator', 'admin'"),
             allow_empty=False,
         )),
    ]


def _special_agents_ipmi_sensors_transform_ipmi_sensors(params):
    if isinstance(params, dict):
        return ("freeipmi", params)
    return params


def _special_agents_ipmi_sensors_vs_freeipmi():
    return Dictionary(
        elements=_special_agents_ipmi_sensors_vs_ipmi_common_elements() + [
            ("ipmi_driver", TextAscii(title=_("IPMI driver"))),
            ("driver_type", TextAscii(title=_("IPMI driver type"))),
            ("BMC_key", TextAscii(title=_("BMC key"))),
            ("quiet_cache", Checkbox(title=_("Quiet cache"), label=_("Enable"))),
            ("sdr_cache_recreate", Checkbox(title=_("SDR cache recreate"), label=_("Enable"))),
            ("interpret_oem_data", Checkbox(title=_("OEM data interpretation"), label=_("Enable"))),
            ("output_sensor_state", Checkbox(title=_("Sensor state"), label=_("Enable"))),
            ("output_sensor_thresholds", Checkbox(title=_("Sensor threshold"), label=_("Enable"))),
            ("ignore_not_available_sensors",
             Checkbox(title=_("Suppress not available sensors"), label=_("Enable"))),
        ],
        optional_keys=[
            "ipmi_driver",
            "driver_type",
            "quiet_cache",
            "sdr_cache_recreate",
            "interpret_oem_data",
            "output_sensor_state",
            "output_sensor_thresholds",
            "ignore_not_available_sensors",
            "BMC_key",
        ],
    )


def _special_agents_ipmi_sensors_vs_ipmitool():
    return Dictionary(
        elements=_special_agents_ipmi_sensors_vs_ipmi_common_elements(),
        optional_keys=[],
    )


def _valuespec_special_agents_ipmi_sensors():
    return Transform(
        CascadingDropdown(
            choices=[
                ("freeipmi", _("Use FreeIPMI"), _special_agents_ipmi_sensors_vs_freeipmi()),
                ("ipmitool", _("Use IPMItool"), _special_agents_ipmi_sensors_vs_ipmitool()),
            ],
            title=_("Check IPMI Sensors via Freeipmi or IPMItool"),
            help=_("This rule selects the Agent IPMI Sensors instead of the normal Check_MK Agent "
                   "which collects the data through the FreeIPMI resp. IPMItool command"),
        ),
        forth=_special_agents_ipmi_sensors_transform_ipmi_sensors,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:ipmi_sensors",
        valuespec=_valuespec_special_agents_ipmi_sensors,
    ))


def _valuespec_special_agents_netapp():
    return Transform(Dictionary(
        elements=[
            ("username", TextAscii(
                title=_("Username"),
                allow_empty=False,
            )),
            ("password", Password(
                title=_("Password"),
                allow_empty=False,
            )),
            ("skip_elements",
             ListChoice(
                 choices=[
                     ("ctr_volumes", _("Do not query volume performance counters")),
                 ],
                 title=_("Performance improvements"),
                 help=_(
                     "Here you can configure whether the performance counters should get queried. "
                     "This can save quite a lot of CPU load on larger systems."),
             )),
        ],
        title=_("Check NetApp via WebAPI"),
        help=_(
            "This rule set selects the NetApp special agent instead of the normal Check_MK Agent "
            "and allows monitoring via the NetApp Web API. To access the data the "
            "user requires permissions to several API classes. They are shown when you call the agent with "
            "<tt>agent_netapp --help</tt>. The agent itself is located in the site directory under "
            "<tt>~/share/check_mk/agents/special</tt>."),
        optional_keys=False,
    ),
                     forth=lambda x: dict([("skip_elements", [])] + x.items()))


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:netapp",
        valuespec=_valuespec_special_agents_netapp,
    ))


def _special_agents_activemq_transform_activemq(value):
    if not isinstance(value, tuple):
        return value
    new_value = {}
    new_value["servername"] = value[0]
    new_value["port"] = value[1]
    new_value["use_piggyback"] = "piggybag" in value[2]  # piggybag...
    return new_value


def _factory_default_special_agents_activemq():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_activemq():
    return Transform(
        Dictionary(elements=[
            ("servername", TextAscii(
                title=_("Server Name"),
                allow_empty=False,
            )), ("port", Integer(title=_("Port Number"), default_value=8161)),
            ("use_piggyback", Checkbox(title=_("Use Piggyback"), label=_("Enable"))),
            ("basicauth",
             Tuple(title=_("BasicAuth settings (optional)"),
                   elements=[TextAscii(title=_("Username")),
                             Password(title=_("Password"))]))
        ],
                   optional_keys=["basicauth"]),
        title=_("Apache ActiveMQ queues"),
        forth=_special_agents_activemq_transform_activemq,
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_activemq(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:activemq",
        valuespec=_valuespec_special_agents_activemq,
    ))


def _factory_default_special_agents_emcvnx():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_emcvnx():
    return Dictionary(
        title=_("Check state of EMC VNX storage systems"),
        help=_("This rule selects the EMC VNX agent instead of the normal Check_MK Agent "
               "and allows monitoring of EMC VNX storage systems by calling naviseccli "
               "commandline tool locally on the monitoring system. Make sure it is installed "
               "and working. You can configure your connection settings here."),
        elements=[
            ("user",
             TextAscii(
                 title=_("EMC VNX admin user name"),
                 allow_empty=True,
                 help=_(
                     "If you leave user name and password empty, the special agent tries to "
                     "authenticate against the EMC VNX device by Security Files. "
                     "These need to be created manually before using. Therefor run as "
                     "instance user (if using OMD) or Nagios user (if not using OMD) "
                     "a command like "
                     "<tt>naviseccli -AddUserSecurity -scope 0 -password PASSWORD -user USER</tt> "
                     "This creates <tt>SecuredCLISecurityFile.xml</tt> and "
                     "<tt>SecuredCLIXMLEncrypted.key</tt> in the home directory of the user "
                     "and these files are used then."),
             )),
            ("password", Password(
                title=_("EMC VNX admin user password"),
                allow_empty=True,
            )),
            ("infos",
             Transform(
                 ListChoice(
                     choices=[
                         ("disks", _("Disks")),
                         ("hba", _("iSCSI HBAs")),
                         ("hwstatus", _("Hardware status")),
                         ("raidgroups", _("RAID groups")),
                         ("agent", _("Model and revsion")),
                         ("sp_util", _("Storage processor utilization")),
                         ("writecache", _("Write cache state")),
                         ("mirrorview", _("Mirror views")),
                         ("storage_pools", _("Storage pools")),
                     ],
                     default_value=[
                         "disks",
                         "hba",
                         "hwstatus",
                     ],
                     allow_empty=False,
                 ),
                 title=_("Retrieve information about..."),
             )),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_emcvnx(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:emcvnx",
        valuespec=_valuespec_special_agents_emcvnx,
    ))


def _factory_default_special_agents_ibmsvc():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_ibmsvc():
    return Dictionary(
        title=_("Check state of IBM SVC / V7000 storage systems"),
        help=_(
            "This rule set selects the <tt>ibmsvc</tt> agent instead of the normal Check_MK Agent "
            "and allows monitoring of IBM SVC / V7000 storage systems by calling "
            "ls* commands there over SSH. "
            "Make sure you have SSH key authentication enabled for your monitoring user. "
            "That means: The user your monitoring is running under on the monitoring "
            "system must be able to ssh to the storage system as the user you gave below "
            "without password."),
        elements=[
            ("user",
             TextAscii(
                 title=_("IBM SVC / V7000 user name"),
                 allow_empty=True,
                 help=_("User name on the storage system. Read only permissions are sufficient."),
             )),
            ("accept-any-hostkey",
             Checkbox(
                 title=_("Accept any SSH Host Key"),
                 label=_("Accept any SSH Host Key"),
                 default_value=False,
                 help=_(
                     "Accepts any SSH Host Key presented by the storage device. "
                     "Please note: This might be a security issue because man-in-the-middle "
                     "attacks are not recognized! Better solution would be to add the "
                     "SSH Host Key of the monitored storage devices to the .ssh/known_hosts "
                     "file for the user your monitoring is running under (on OMD: the site user)"))
            ),
            ("infos",
             Transform(
                 ListChoice(
                     choices=[
                         ("lshost", _("Hosts Connected")),
                         ("lslicense", _("Licensing Status")),
                         ("lsmdisk", _("MDisks")),
                         ("lsmdiskgrp", _("MDisksGrps")),
                         ("lsnode", _("IO Groups")),
                         ("lsnodestats", _("Node Stats")),
                         ("lssystem", _("System Info")),
                         ("lssystemstats", _("System Stats")),
                         ("lseventlog", _("Event Log")),
                         ("lsportfc", _("FC Ports")),
                         ("lsportsas", _("SAS Ports")),
                         ("lsenclosure", _("Enclosures")),
                         ("lsenclosurestats", _("Enclosure Stats")),
                         ("lsarray", _("RAID Arrays")),
                         ("disks", _("Physical Disks")),
                     ],
                     default_value=[
                         "lshost", "lslicense", "lsmdisk", "lsmdiskgrp", "lsnode", "lsnodestats",
                         "lssystem", "lssystemstats", "lsportfc", "lsenclosure", "lsenclosurestats",
                         "lsarray", "disks"
                     ],
                     allow_empty=False,
                 ),
                 title=_("Retrieve information about..."),
             )),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_ibmsvc(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:ibmsvc",
        valuespec=_valuespec_special_agents_ibmsvc,
    ))


def _factory_default_special_agents_random():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_random():
    return FixedValue(
        {},
        title=_("Create random monitoring data"),
        help=_("By configuring this rule for a host - instead of the normal "
               "Check_MK agent random monitoring data will be created."),
        totext=_("Create random monitoring data"),
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_random(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:random",
        valuespec=_valuespec_special_agents_random,
    ))


def _factory_default_special_agents_acme_sbc():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_acme_sbc():
    return FixedValue(
        {},
        title=_("Check ACME Session Border Controller"),
        help=_("This rule activates an agent which connects "
               "to an ACME Session Border Controller (SBC). This agent uses SSH, so "
               "you have to exchange an SSH key to make a passwordless connect possible."),
        totext=_("Connect to ACME SBC"),
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_acme_sbc(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:acme_sbc",
        valuespec=_valuespec_special_agents_acme_sbc,
    ))


def _factory_default_special_agents_fritzbox():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_fritzbox():
    return Dictionary(
        title=_("Check state of Fritz!Box Devices"),
        help=_("This rule selects the Fritz!Box agent, which uses UPNP to gather information "
               "about configuration and connection status information."),
        elements=[
            ("timeout",
             Integer(
                 title=_("Connect Timeout"),
                 help=_("The network timeout in seconds when communicating via UPNP. "
                        "The default is 10 seconds. Please note that this "
                        "is not a total timeout, instead it is applied to each API call."),
                 default_value=10,
                 minvalue=1,
                 unit=_("seconds"),
             )),
        ],
        optional_keys=["timeout"],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_fritzbox(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:fritzbox",
        valuespec=_valuespec_special_agents_fritzbox,
    ))


def _factory_default_special_agents_innovaphone():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_innovaphone():
    return Tuple(
        title=_("Innovaphone Gateways"),
        help=_("Please specify the user and password needed to access the xml interface"),
        elements=[
            TextAscii(title=_("Username")),
            Password(title=_("Password")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_innovaphone(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:innovaphone",
        valuespec=_valuespec_special_agents_innovaphone,
    ))


def _factory_default_special_agents_hivemanager():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_hivemanager():
    return Tuple(title=_("Aerohive HiveManager"),
                 help=_("Activate monitoring of host via a HTTP connect to the HiveManager"),
                 elements=[
                     TextAscii(title=_("Username")),
                     Password(title=_("Password")),
                 ])


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_hivemanager(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:hivemanager",
        valuespec=_valuespec_special_agents_hivemanager,
    ))


def _factory_default_special_agents_hivemanager_ng():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_hivemanager_ng():
    return Dictionary(
        title=_("Aerohive HiveManager NG"),
        help=_("Activate monitoring of the HiveManagerNG cloud."),
        elements=[
            ("url",
             HTTPUrl(
                 title=_("URL to HiveManagerNG, e.g. https://cloud.aerohive.com"),
                 allow_empty=False,
             )),
            ("vhm_id", TextAscii(
                title=_("Numerical ID of the VHM, e.g. 102"),
                allow_empty=False,
            )),
            ("api_token", TextAscii(
                title=_("API Access Token"),
                size=64,
                allow_empty=False,
            )),
            ("client_id", TextAscii(
                title=_("Client ID"),
                allow_empty=False,
            )),
            ("client_secret", Password(
                title=_("Client secret"),
                allow_empty=False,
            )),
            ("redirect_url", HTTPUrl(
                title=_("Redirect URL (has to be https)"),
                allow_empty=False,
            )),
        ],
        optional_keys=None,
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_hivemanager_ng(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:hivemanager_ng",
        valuespec=_valuespec_special_agents_hivemanager_ng,
    ))


def _factory_default_special_agents_allnet_ip_sensoric():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_allnet_ip_sensoric():
    return Dictionary(
        title=_("Check state of ALLNET IP Sensoric Devices"),
        help=_("This rule selects the ALLNET IP Sensoric agent, which fetches "
               "/xml/sensordata.xml from the device by HTTP and extracts the "
               "needed monitoring information from this file."),
        elements=[
            ("timeout",
             Integer(
                 title=_("Connect Timeout"),
                 help=_("The network timeout in seconds when communicating via HTTP. "
                        "The default is 10 seconds."),
                 default_value=10,
                 minvalue=1,
                 unit=_("seconds"),
             )),
        ],
        optional_keys=["timeout"],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_allnet_ip_sensoric(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:allnet_ip_sensoric",
        valuespec=_valuespec_special_agents_allnet_ip_sensoric,
    ))


def _valuespec_special_agents_ucs_bladecenter():
    return Dictionary(
        title=_("Check state of UCS Bladecenter"),
        help=_("This rule selects the UCS Bladecenter agent instead of the normal Check_MK Agent "
               "which collects the data through the UCS Bladecenter Web API"),
        elements=[
            ("username", TextAscii(
                title=_("Username"),
                allow_empty=False,
            )),
            ("password", Password(
                title=_("Password"),
                allow_empty=False,
            )),
            ("no_cert_check",
             FixedValue(
                 True,
                 title=_("Disable SSL certificate validation"),
                 totext=_("SSL certificate validation is disabled"),
             )),
        ],
        optional_keys=['no_cert_check'],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:ucs_bladecenter",
        valuespec=_valuespec_special_agents_ucs_bladecenter,
    ))


def _special_agents_siemens_plc_validate_siemens_plc_values(value, varprefix):
    valuetypes = {}
    for index, (_db_number, _address, _datatype, valuetype, ident) in enumerate(value):
        valuetypes.setdefault(valuetype, [])
        if ident in valuetypes[valuetype]:
            raise MKUserError("%s_%d_%d" % (varprefix, index + 1, 4),
                              _("The ident of a value needs to be unique per valuetype."))
        valuetypes[valuetype].append(ident)


def _special_agents_siemens_plc_siemens_plc_value():
    return [
        Transform(
            CascadingDropdown(
                title=_("The Area"),
                choices=[
                    ("db", _("Datenbaustein"),
                     Integer(
                         title="<nobr>%s</nobr>" % _("DB Number"),
                         minvalue=1,
                     )),
                    ("input", _("Input")),
                    ("output", _("Output")),
                    ("merker", _("Merker")),
                    ("timer", _("Timer")),
                    ("counter", _("Counter")),
                ],
                orientation="horizontal",
                sorted=True,
            ),
            # Transform old Integer() value spec to new cascading dropdown value
            forth=lambda x: isinstance(x, int) and ("db", x) or x,
        ),
        Float(
            title=_("Address"),
            display_format="%.1f",
            help=_("Addresses are specified with a dot notation, where number "
                   "before the dot specify the byte to fetch and the number after the "
                   "dot specifies the bit to fetch. The number of the bit is always "
                   "between 0 and 7."),
        ),
        CascadingDropdown(
            title=_("Datatype"),
            choices=[
                ("dint", _("Double Integer (DINT)")),
                ("real", _("Real Number (REAL)")),
                ("bit", _("Single Bit (BOOL)")),
                ("str", _("String (STR)"), Integer(
                    minvalue=1,
                    title=_("Size"),
                    unit=_("Bytes"),
                )),
                ("raw", _("Raw Bytes (HEXSTR)"),
                 Integer(
                     minvalue=1,
                     title=_("Size"),
                     unit=_("Bytes"),
                 )),
            ],
            orientation="horizontal",
            sorted=True,
        ),
        DropdownChoice(
            title=_("Type of the value"),
            choices=[
                (None, _("Unclassified")),
                ("temp", _("Temperature")),
                ("hours_operation", _("Hours of operation")),
                ("hours_since_service", _("Hours since service")),
                ("hours", _("Hours")),
                ("seconds_operation", _("Seconds of operation")),
                ("seconds_since_service", _("Seconds since service")),
                ("seconds", _("Seconds")),
                ("counter", _("Increasing counter")),
                ("flag", _("State flag (on/off)")),
                ("text", _("Text")),
            ],
            sorted=True,
        ),
        ID(
            title=_("Ident of the value"),
            help=_(" An identifier of your choice. This identifier "
                   "is used by the Check_MK checks to access "
                   "and identify the single values. The identifier "
                   "needs to be unique within a group of VALUETYPES."),
        ),
    ]


def _factory_default_special_agents_siemens_plc():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_siemens_plc():
    return Dictionary(
        elements=[
            ("devices",
             ListOf(
                 Dictionary(
                     elements=[
                         ('host_name',
                          TextAscii(
                              title=_('Name of the PLC'),
                              allow_empty=False,
                              help=_(
                                  'Specify the logical name, e.g. the hostname, of the PLC. This name '
                                  'is used to name the resulting services.'))),
                         ('host_address',
                          TextAscii(
                              title=_('Network Address'),
                              allow_empty=False,
                              help=
                              _('Specify the hostname or IP address of the PLC to communicate with.'
                               ))),
                         ("rack", Integer(
                             title=_("Number of the Rack"),
                             minvalue=0,
                         )),
                         ("slot", Integer(
                             title=_("Number of the Slot"),
                             minvalue=0,
                         )),
                         ("tcp_port",
                          Integer(
                              title=_("TCP Port number"),
                              help=_("Port number for communicating with the PLC"),
                              default_value=102,
                              minvalue=1,
                              maxvalue=65535,
                          )),
                         ("timeout",
                          Integer(
                              title=_("Connect Timeout"),
                              help=_(
                                  "The connect timeout in seconds when establishing a connection "
                                  "with the PLC."),
                              default_value=60,
                              minvalue=1,
                              unit=_("seconds"),
                          )),
                         ("values",
                          ListOf(
                              Tuple(
                                  elements=_special_agents_siemens_plc_siemens_plc_value(),
                                  orientation="horizontal",
                              ),
                              title=_("Values to fetch from this device"),
                              validate=_special_agents_siemens_plc_validate_siemens_plc_values,
                              magic='@;@',
                          )),
                     ],
                     optional_keys=["timeout"],
                 ),
                 title=_("Devices to fetch information from"),
             )),
            ("values",
             ListOf(
                 Tuple(
                     elements=_special_agents_siemens_plc_siemens_plc_value(),
                     orientation="horizontal",
                 ),
                 title=_("Values to fetch from all devices"),
                 validate=_special_agents_siemens_plc_validate_siemens_plc_values,
             )),
        ],
        optional_keys=["timeout"],
        title=_("Siemens PLC (SPS)"),
        help=_("This rule selects the Siemens PLC agent instead of the normal Check_MK Agent "
               "and allows monitoring of Siemens PLC using the Snap7 API. You can configure "
               "your connection settings and values to fetch here."),
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_siemens_plc(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:siemens_plc",
        valuespec=_valuespec_special_agents_siemens_plc,
    ))


def _valuespec_special_agents_ruckus_spot():
    return Dictionary(
        elements=[
            ("address",
             Alternative(
                 title=_("Server Address"),
                 help=_("Here you can set a manual address if the server differs from the host"),
                 elements=[
                     FixedValue(
                         True,
                         title=_("Use host address"),
                         totext="",
                     ),
                     TextAscii(title=_("Enter address"),)
                 ],
                 default_value=True)),
            ("port", Integer(
                title=_("Port"),
                default_value=8443,
            )),
            ("venueid", TextAscii(
                title=_("Venue ID"),
                allow_empty=False,
            )),
            ("api_key", TextAscii(
                title=_("API key"),
                allow_empty=False,
                size=70,
            )),
            ("cmk_agent",
             Dictionary(
                 title=_("Also contact Check_MK agent"),
                 help=_("With this setting, the special agent will also contact the "
                        "Check_MK agent on the same system at the specified port."),
                 elements=[
                     ("port", Integer(
                         title=_("Port"),
                         default_value=6556,
                     )),
                 ],
                 optional_keys=[],
             )),
        ],
        title=_("Agent for Ruckus Spot"),
        help=_("This rule selects the Agent Ruckus Spot agent instead of the normal Check_MK Agent "
               "which collects the data through the Ruckus Spot web interface"),
        optional_keys=["cmk_agent"])


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:ruckus_spot",
        valuespec=_valuespec_special_agents_ruckus_spot,
    ))


def _factory_default_special_agents_appdynamics():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_appdynamics():
    return Dictionary(
        title=_('AppDynamics via REST API'),
        help=_(
            'This rule allows querying an AppDynamics server for information about Java applications'
            'via the AppDynamics REST API. You can configure your connection settings here.'),
        elements=[
            ('username', TextAscii(
                title=_('AppDynamics login username'),
                allow_empty=False,
            )),
            ('password', Password(
                title=_('AppDynamics login password'),
                allow_empty=False,
            )),
            ('application',
             TextAscii(
                 title=_('AppDynamics application name'),
                 help=
                 _('This is the application name used in the URL. If you enter for example the application '
                   'name <tt>foobar</tt>, this would result in the URL being used to contact the REST API: '
                   '<tt>/controller/rest/applications/foobar/metric-data</tt>'),
                 allow_empty=False,
                 size=40,
             )),
            ('port',
             Integer(
                 title=_('TCP port number'),
                 help=_('Port number that AppDynamics is listening on. The default is 8090.'),
                 default_value=8090,
                 minvalue=1,
                 maxvalue=65535,
             )),
            ('timeout',
             Integer(
                 title=_('Connection timeout'),
                 help=_('The network timeout in seconds when communicating with AppDynamics.'
                        'The default is 30 seconds.'),
                 default_value=30,
                 minvalue=1,
                 unit=_('seconds'),
             )),
        ],
        optional_keys=['port', 'timeout'],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_appdynamics(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:appdynamics",
        valuespec=_valuespec_special_agents_appdynamics,
    ))


def _special_agents_jolokia_mk_jolokia_elements():
    return [
        ("port",
         Integer(
             title=_("TCP port for connection"),
             default_value=8080,
             minvalue=1,
             maxvalue=65535,
         )),
        ("login",
         Tuple(title=_("Optional login (if required)"),
               elements=[
                   TextAscii(
                       title=_("User ID for web login (if login required)"),
                       default_value="monitoring",
                   ),
                   Password(title=_("Password for this user")),
                   DropdownChoice(title=_("Login mode"),
                                  choices=[
                                      ("basic", _("HTTP Basic Authentication")),
                                      ("digest", _("HTTP Digest")),
                                  ])
               ])),
        ("suburi",
         TextAscii(
             title=_("relative URI under which Jolokia is visible"),
             default_value="jolokia",
             size=30,
         )),
        ("instance",
         TextUnicode(title=_("Name of the instance in the monitoring"),
                     help=_("If you do not specify a name here, then the TCP port number "
                            "will be used as an instance name."))),
        ("protocol",
         DropdownChoice(title=_("Protocol"), choices=[
             ("http", "HTTP"),
             ("https", "HTTPS"),
         ])),
    ]


def _factory_default_special_agents_jolokia():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_jolokia():
    return Dictionary(
        title=_('Jolokia'),
        help=_('This rule allows querying the Jolokia web API.'),
        elements=_special_agents_jolokia_mk_jolokia_elements(),
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_jolokia(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:jolokia",
        valuespec=_valuespec_special_agents_jolokia,
    ))


def _valuespec_special_agents_tinkerforge():
    return Dictionary(
        title=_("Tinkerforge"),
        elements=[
            ("port",
             Integer(title=_('TCP port number'),
                     help=_('Port number that AppDynamics is listening on. The default is 8090.'),
                     default_value=4223,
                     minvalue=1,
                     maxvalue=65535)),
            ("segment_display_uid",
             TextAscii(
                 title=_("7-segment display uid"),
                 help=_(
                     "This is the uid of the sensor you want to display in the 7-segment display, "
                     "not the uid of the display itself. There is currently no support for "
                     "controling multiple displays."))),
            ("segment_display_brightness",
             Integer(title=_("7-segment display brightness"), minvalue=0, maxvalue=7))
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:tinkerforge",
        valuespec=_valuespec_special_agents_tinkerforge,
    ))


def _valuespec_special_agents_prism():
    return Dictionary(
        title=_("Nutanix Prism"),
        elements=[
            ("port",
             Integer(title=_("TCP port for connection"),
                     default_value=9440,
                     minvalue=1,
                     maxvalue=65535)),
            ("username", TextAscii(title=_("User ID for web login"),)),
            ("password", Password(title=_("Password for this user"))),
        ],
        optional_keys=["port"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:prism",
        valuespec=_valuespec_special_agents_prism,
    ))


def _special_agents_3par_transform_3par_add_verify_cert(v):
    v.setdefault("verify_cert", False)
    return v


def _valuespec_special_agents_3par():
    return Transform(
        Dictionary(
            title=_("Agent 3PAR Configuration"),
            elements=[
                ("user", TextAscii(
                    title=_("Username"),
                    allow_empty=False,
                )),
                ("password", IndividualOrStoredPassword(
                    title=_("Password"),
                    allow_empty=False,
                )),
                ("verify_cert",
                 DropdownChoice(
                     title=_("SSL certificate verification"),
                     choices=[
                         (True, _("Activate")),
                         (False, _("Deactivate")),
                     ],
                 )),
                ("values",
                 ListOfStrings(
                     title=_("Values to fetch"),
                     orientation="horizontal",
                     help=_("Possible values are the following: cpgs, volumes, hosts, capacity, "
                            "system, ports, remotecopy, hostsets, volumesets, vluns, flashcache, "
                            "users, roles, qos.\n"
                            "If you do not specify any value the first seven are used as default."),
                 )),
            ],
            optional_keys=["values"],
        ),
        forth=_special_agents_3par_transform_3par_add_verify_cert,
    )


# verify_cert was added with 1.5.0p1

rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:3par",
        title=lambda: _("Agent 3PAR Configuration"),
        valuespec=_valuespec_special_agents_3par,
    ))


def _valuespec_special_agents_storeonce():
    return Dictionary(
        title=_("Check HPE StoreOnce"),
        help=_("This rule set selects the special agent for HPE StoreOnce Applainces "
               "instead of the normal Check_MK agent and allows monitoring via Web API. "),
        optional_keys=["cert"],
        elements=[
            ("user", TextAscii(title=_("Username"), allow_empty=False)),
            ("password", Password(title=_("Password"), allow_empty=False)),
            ("cert",
             DropdownChoice(title=_("SSL certificate verification"),
                            choices=[
                                (True, _("Activate")),
                                (False, _("Deactivate")),
                            ])),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:storeonce",
        valuespec=_valuespec_special_agents_storeonce,
    ))


def _valuespec_special_agents_salesforce():
    return Dictionary(
        title=_("Check Salesforce"),
        help=_("This rule selects the special agent for Salesforce."),
        elements=[
            ("instances", ListOfStrings(
                title=_("Instances"),
                allow_empty=False,
            )),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        help_func=lambda: _("This rule selects the special agent for Salesforce."),
        name="special_agents:salesforce",
        title=lambda: _("Check Salesforce"),
        valuespec=_valuespec_special_agents_salesforce,
    ))


def _special_agents_azure_azure_explicit_config():
    return ListOf(
        Dictionary(
            elements=[
                ('group_name', TextAscii(
                    title=_('Name of the resource group'),
                    allow_empty=False,
                )),
                ('resources',
                 ListOfStrings(
                     title=_('Explicitly specify resources'),
                     allow_empty=False,
                 )),
            ],
            optional_keys=["resources"],
        ),
        title=_("explicitly specified groups"),
        allow_empty=False,
        add_label=_("Add resource group"),
    )


def _special_agents_azure_azure_tag_based_config():
    return ListOf(
        Tuple(
            orientation="horizontal",
            elements=[
                TextAscii(
                    title=_('The resource tag'),
                    allow_empty=False,
                ),
                CascadingDropdown(
                    orientation="horizontal",
                    choices=[
                        ('exists', _("exists")),
                        ('value', _("is"), TextUnicode(title=_('Tag value'), allow_empty=False)),
                    ],
                ),
            ],
        ),
        title=_('resources matching tag based criteria'),
        allow_empty=False,
        add_label=_("Add resource tag"),
    )


def _valuespec_special_agents_azure():
    return Dictionary(
        title=_("Microsoft Azure"),
        help=_("To monitor Azure resources add this datasource to <b>one</b> host. "
               "The data will be transported using the piggyback mechanism, so make "
               "sure to create one host for every monitored resource group. You can "
               "learn about the discovered groups in the <i>Azure Agent Info</i> "
               "service of the host owning the datasource program."),
        # element names starting with "--" will be passed do cmd line w/o parsing!
        elements=[
            ("subscription", TextAscii(
                title=_("Subscription ID"),
                allow_empty=False,
                size=45,
            )),
            ("tenant", TextAscii(
                title=_("Tenant ID / Directory ID"),
                allow_empty=False,
                size=45,
            )),
            ("client", TextAscii(
                title=_("Client ID / Application ID"),
                allow_empty=False,
                size=45,
            )),
            ("secret", Password(
                title=_("Client Secret"),
                allow_empty=False,
                size=45,
            )),
            (
                "config",
                Dictionary(
                    title=_("Retrieve information about..."),
                    # Since we introduced this, Microsoft has already reduced the number
                    # of allowed API requests. At the time of this writing (11/2018)
                    # you can find the number here:
                    # https://docs.microsoft.com/de-de/azure/azure-resource-manager/resource-manager-request-limits
                    help=_("By default, all resources associated to the configured tenant ID"
                           " will be monitored.") + " " +
                    _("However, since Microsoft limits API calls to %s per hour"
                      " (%s per minute), you can restrict the monitoring to individual"
                      " resource groups and resources.") % ("12000", "200"),
                    elements=[
                        ('explicit', _special_agents_azure_azure_explicit_config()),
                        ('tag_based', _special_agents_azure_azure_tag_based_config()),
                    ],
                )),
            ("piggyback_vms",
             DropdownChoice(
                 title=_("Map data relating to VMs"),
                 help=_("By default, data relating to a VM is sent to the group host"
                        " corresponding to the resource group of the VM, the same way"
                        " as for any other resource. If the VM is present in your "
                        " monitoring as a separate host, you can choose to send the data"
                        " to the VM itself."),
                 choices=[
                     ("grouphost", _("Map data to group host")),
                     ("self", _("Map data to the VM itself")),
                 ],
             )),
            ("sequential",
             DropdownChoice(
                 title=_("Force agent to run in single thread"),
                 help=_("Check this to turn off multiprocessing."
                        " Recommended for debugging purposes only."),
                 choices=[
                     (False, _("Run agent multithreaded")),
                     (True, _("Run agent in single thread")),
                 ],
             )),
        ],
        optional_keys=["piggyback_vms", "sequential"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:azure",
        valuespec=_valuespec_special_agents_azure,
    ))


class MultisiteBiDatasource(object):
    def get_valuespec(self):
        return Dictionary(
            elements=self._get_dynamic_valuespec_elements(),
            optional_keys=["filter", "options", "assignments"],
        )

    def _get_dynamic_valuespec_elements(self):
        return [
            ("site",
             CascadingDropdown(choices=[
                 ("local", _("Connect to the local site")),
                 ("url", _("Connect to site url"),
                  HTTPUrl(help=_("URL of the remote site, for example https://10.3.1.2/testsite"))),
             ],
                               sorted=False,
                               orientation="horizontal",
                               title=_("Site connection"))),
            ("credentials",
             CascadingDropdown(
                 choices=[("automation", _("Use the credentials of the 'automation' user")),
                          ("configured", _("Use the following credentials"),
                           Tuple(elements=[
                               TextAscii(title=_("Automation Username"), allow_empty=True),
                               Password(title=_("Automation Secret"), allow_empty=True)
                           ],))],
                 help=_(
                     "Here you can configured the credentials to be used. Keep in mind that the <tt>automation</tt> user need "
                     "to exist if you choose this option"),
                 title=_("Login credentials"),
                 default_value="automation")),
            ("filter", self._vs_filters()),
            ("assignments", self._vs_aggregation_assignments()),
            ("options", self._vs_options()),
        ]

    def _vs_aggregation_assignments(self):
        return Dictionary(
            title=_("Aggregation assignment"),
            elements=[
                ("querying_host",
                 FixedValue("querying_host", totext="", title=_("Assign to the querying host"))),
                ("affected_hosts",
                 FixedValue("affected_hosts", totext="", title=_("Assign to the affected hosts"))),
                ("regex",
                 ListOf(
                     Tuple(
                         orientation="horizontal",
                         elements=[
                             RegExpUnicode(
                                 title=_("Regular expression"),
                                 help=_("Must contain at least one subgroup <tt>(...)</tt>"),
                                 mingroups=0,
                                 maxgroups=9,
                                 size=30,
                                 allow_empty=False,
                                 mode=RegExp.prefix,
                                 case_sensitive=False,
                             ),
                             TextUnicode(
                                 title=_("Replacement"),
                                 help=
                                 _("Use <tt>\\1</tt>, <tt>\\2</tt> etc. to replace matched subgroups"
                                  ),
                                 size=30,
                                 allow_empty=False,
                             )
                         ],
                     ),
                     title=_("Assign via regular expressions"),
                     help=
                     _("You can add any number of expressions here which are executed succesively until the first match. "
                       "Please specify a regular expression in the first field. This expression should at "
                       "least contain one subexpression exclosed in brackets - for example <tt>vm_(.*)_prod</tt>. "
                       "In the second field you specify the translated aggregation and can refer to the first matched "
                       "group with <tt>\\1</tt>, the second with <tt>\\2</tt> and so on, for example <tt>\\1.example.org</tt>. "
                       ""),
                     add_label=_("Add expression"),
                     movable=False,
                 )),
            ])

    def _vs_filters(self):
        return Dictionary(elements=[
            ("aggr_name_regex",
             ListOf(RegExp(mode=RegExp.prefix, title=_("Pattern")),
                    title=_("By regular expression"),
                    add_label=_("Add new pattern"),
                    movable=False)),
            ("aggr_groups",
             ListOf(DropdownChoice(choices=bi.aggregation_group_choices),
                    title=_("By aggregation groups"),
                    add_label=_("Add new group"),
                    movable=False)),
        ],
                          title=_("Filter aggregations"))

    def _vs_options(self):
        return Dictionary(
            elements=[
                ("state_scheduled_downtime",
                 MonitoringState(title=_("State, if BI aggregate is in scheduled downtime"))),
                ("state_acknowledged",
                 MonitoringState(title=_("State, if BI aggregate is acknowledged"))),
            ],
            optional_keys=["state_scheduled_downtime", "state_acknowledged"],
            title=_("Additional options"),
        )


def _valuespec_special_agents_bi():
    return ListOf(
        MultisiteBiDatasource().get_valuespec(),
        title=_("Check state of BI Aggregations"),
        help=_(
            "This rule allows you to check multiple BI aggregations from multiple sites at once. "
            "You can also assign aggregations to specific hosts through the piggyback mechanism."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:bi",
        valuespec=_valuespec_special_agents_bi,
    ))


def _validate_aws_tags(value, varprefix):
    used_keys = []
    # KEY:
    # ve_p_services_p_ec2_p_choice_1_IDX_0
    # VALUES:
    # ve_p_services_p_ec2_p_choice_1_IDX_1_IDX
    for idx_tag, (tag_key, tag_values) in enumerate(value):
        tag_field = "%s_%s_0" % (varprefix, idx_tag + 1)
        if tag_key not in used_keys:
            used_keys.append(tag_key)
        else:
            raise MKUserError(tag_field,
                              _("Each tag must be unique and cannot be used multiple times"))
        if tag_key.startswith('aws:'):
            raise MKUserError(tag_field, _("Do not use 'aws:' prefix for the key."))
        if len(tag_key) > 128:
            raise MKUserError(tag_field, _("The maximum key length is 128 characters."))
        if len(tag_values) > 50:
            raise MKUserError(tag_field, _("The maximum number of tags per resource is 50."))

        for idx_values, v in enumerate(tag_values):
            values_field = "%s_%s_1_%s" % (varprefix, idx_tag + 1, idx_values + 1)
            if len(v) > 256:
                raise MKUserError(values_field, _("The maximum value length is 256 characters."))
            if v.startswith('aws:'):
                raise MKUserError(values_field, _("Do not use 'aws:' prefix for the values."))


def _vs_aws_tags(title):
    return ListOf(Tuple(help=_(
        "How to configure AWS tags please see "
        "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_Tags.html"),
                        orientation="horizontal",
                        elements=[
                            TextAscii(title=_("Key")),
                            ListOfStrings(title=_("Values"), orientation="horizontal")
                        ]),
                  add_label=_("Add new tag"),
                  movable=False,
                  title=title,
                  validate=_validate_aws_tags)


def _vs_element_aws_service_selection():
    return (
        'selection',
        CascadingDropdown(
            title=_("Selection of service instances"),
            help=_("<i>Gather all service instances and restrict by overall tags</i> means that "
                   "if overall tags are stated above then all service instances are filtered "
                   "by these tags. Otherwise all instances are gathered.<br>"
                   "With <i>Use explicit service tags and overwrite overall tags</i> you can "
                   "specify explicit tags for these services. The overall tags are ignored for "
                   "these services.<br>"
                   "<i>Use explicit service names and ignore overall tags</i>: With this selection "
                   "you can state explicit names. The overall tags are ignored for these service."),
            choices=[
                ('all', _("Gather all service instances and restrict by overall AWS tags")),
                ('tags', _("Use explicit AWS service tags and overrule overall AWS tags"),
                 _vs_aws_tags(_("AWS Tags"))),
                ('names', _("Use explicit service names and ignore overall AWS tags"),
                 ListOfStrings()),
            ]))


def _vs_element_aws_limits():
    return ("limits",
            FixedValue(True,
                       help=_("If limits are enabled all instances are fetched regardless of "
                              "possibly configured restriction to names or tags"),
                       title=_("Service limits"),
                       totext=_("Monitor service limits")))


def _valuespec_special_agents_aws():
    return Dictionary(
        title=_('Amazon Web Services (AWS)'),
        elements=[
            ("access_key_id",
             TextAscii(
                 title=_("The access key ID for your AWS account"),
                 allow_empty=False,
                 size=50,
             )),
            ("secret_access_key",
             IndividualOrStoredPassword(
                 title=_("The secret access key for your AWS account"),
                 allow_empty=False,
             )),
            ("assume_role",
             Dictionary(
                 title=_("Assume a different IAM role"),
                 elements=
                 [("role_arn_id",
                   Tuple(
                       title=_("Use STS AssumeRole to assume a different IAM role"),
                       elements=[
                           TextAscii(
                               title=_("The ARN of the IAM role to assume"),
                               size=50,
                               help=_("The Amazon Resource Name (ARN) of the role to assume.")),
                           TextAscii(
                               title=_("External ID (optional)"),
                               size=50,
                               help=
                               _("A unique identifier that might be required when you assume a role in another "
                                 +
                                 "account. If the administrator of the account to which the role belongs provided "
                                 +
                                 "you with an external ID, then provide that value in the External ID parameter. "
                                ))
                       ]))])),
            ("global_services",
             Dictionary(
                 title=_("Global services to monitor"),
                 elements=[("ce",
                            FixedValue(None,
                                       totext=_("Monitor costs and usage"),
                                       title=_("Costs and usage (CE)")))],
             )),
            ("regions",
             ListChoice(
                 title=_("Regions to use"),
                 choices=sorted(aws_constants.AWSRegions, key=lambda x: x[1]),
             )),
            ("services",
             Dictionary(
                 title=_("Services per region to monitor"),
                 elements=[
                     ("ec2",
                      Dictionary(
                          title=_("Elastic Compute Cloud (EC2)"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                          ],
                          optional_keys=["limits"],
                          default_keys=["limits"],
                      )),
                     ("ebs",
                      Dictionary(
                          title=_("Elastic Block Storage (EBS)"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                          ],
                          optional_keys=["limits"],
                          default_keys=["limits"],
                      )),
                     ("s3",
                      Dictionary(
                          title=_("Simple Storage Service (S3)"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                              ("requests",
                               FixedValue(
                                   None,
                                   totext=_("Monitor request metrics"),
                                   title=_("Request metrics"),
                                   help=_("In order to monitor S3 request metrics you have to "
                                          "enable request metric monitoring in the AWS/S3 console. "
                                          "This is a paid feature"))),
                          ],
                          optional_keys=["limits", "requests"],
                          default_keys=["limits"],
                      )),
                     ("glacier",
                      Dictionary(
                          title=_("Amazon S3 Glacier (Glacier)"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                          ],
                          optional_keys=["limits"],
                          default_keys=["limits"],
                      )),
                     ("elb",
                      Dictionary(
                          title=_("Classic Load Balancing (ELB)"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                          ],
                          optional_keys=["limits"],
                          default_keys=["limits"],
                      )),
                     ("elbv2",
                      Dictionary(
                          title=_("Application and Network Load Balancing (ELBv2)"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                          ],
                          optional_keys=["limits"],
                          default_keys=["limits"],
                      )),
                     ("rds",
                      Dictionary(
                          title=_("Relational Database Service (RDS)"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                          ],
                          optional_keys=["limits"],
                          default_keys=["limits"],
                      )),
                     ("cloudwatch",
                      Dictionary(
                          title=_("Cloudwatch"),
                          elements=[
                              ('alarms',
                               CascadingDropdown(title=_("Selection of alarms"),
                                                 choices=[
                                                     ('all', _("Gather all")),
                                                     ('names', _("Use explicit names"),
                                                      ListOfStrings()),
                                                 ])),
                              _vs_element_aws_limits(),
                          ],
                          optional_keys=["alarms", "limits"],
                          default_keys=["alarms", "limits"],
                      )),
                 ],
                 default_keys=["ec2", "ebs", "s3", "glacier", "elb", "elbv2", "rds", "cloudwatch"],
             )),
            ("overall_tags",
             _vs_aws_tags(_("Restrict monitoring services by one of these AWS tags"))),
        ],
        optional_keys=["overall_tags"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:aws",
        title=lambda: _("Amazon Web Services (AWS)"),
        valuespec=_valuespec_special_agents_aws,
    ))


def _factory_default_special_agents_vnx_quotas():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_vnx_quotas():
    return Dictionary(
        title=_("Check VNX quotas and filesystems"),
        elements=[
            ("user", TextAscii(title=_("NAS DB user name"))),
            ("password", Password(title=_("Password"))),
            ("nas_db", TextAscii(title=_("NAS DB path"))),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_vnx_quotas(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:vnx_quotas",
        valuespec=_valuespec_special_agents_vnx_quotas,
    ))


def _factory_default_special_agents_elasticsearch():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_elasticsearch():
    return Dictionary(
        optional_keys=["user", "password"],
        title=_("Check state of Elasticsearch"),
        help=_("Requests data about Elasticsearch clusters, nodes and indices."),
        elements=[
            ("hosts",
             ListOfStrings(
                 title=_("Hostnames to query"),
                 help=
                 _("Use this option to set which host should be checked by the special agent. If the "
                   "connection to the first server fails, the next server will be queried (fallback). "
                   "The check will only output data from the first host that sends a response."),
                 size=32,
                 allow_empty=False,
             )),
            ("user", TextAscii(title=_("Username"), size=32, allow_empty=True)),
            ("password", PasswordFromStore(
                title=_("Password of the user"),
                allow_empty=False,
            )),
            (
                "protocol",
                DropdownChoice(title=_("Protocol"),
                               choices=[
                                   ("http", "HTTP"),
                                   ("https", "HTTPS"),
                               ],
                               default_value="https"),
            ),
            ("port",
             Integer(
                 title=_("Port"),
                 help=_(
                     "Use this option to query a port which is different from standard port 9200."),
                 default_value=9200,
             )),
            (
                "infos",
                ListChoice(
                    title=_("Informations to query"),
                    help=_("Defines what information to query. "
                           "Checks for Cluster, Indices and Shard statistics follow soon."),
                    choices=[
                        ("cluster_health", _("Cluster health")),
                        ("nodes", _("Node statistics")),
                        ("stats", _("Cluster, Indices and Shard statistics")),
                    ],
                    default_value=["cluster_health", "nodes", "stats"],
                    allow_empty=False,
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_elasticsearch(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:elasticsearch",
        valuespec=_valuespec_special_agents_elasticsearch,
    ))


def _factory_default_special_agents_splunk():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_splunk():
    return Dictionary(
        title=_("Check state of Splunk"),
        help=_("Requests data from a Splunk instance."),
        optional_keys=["port"],
        elements=[
            ("instance",
             TextAscii(
                 title=_("Splunk instance to query."),
                 help=_("Use this option to set which host should be checked "
                        "by the special agent."),
                 size=32,
                 allow_empty=False,
             )),
            ("user", TextAscii(title=_("Username"), size=32, allow_empty=False)),
            ("password", PasswordFromStore(
                title=_("Password of the user"),
                allow_empty=False,
            )),
            (
                "protocol",
                DropdownChoice(title=_("Protocol"),
                               choices=[
                                   ("http", "HTTP"),
                                   ("https", "HTTPS"),
                               ],
                               default_value="https"),
            ),
            ("port",
             Integer(
                 title=_("Port"),
                 help=_(
                     "Use this option to query a port which is different from standard port 8089."),
                 default_value=8089,
             )),
            ("infos",
             ListChoice(
                 title=_("Informations to query"),
                 help=_("Defines what information to query. You can "
                        "choose to query license state and usage, Splunk "
                        "system messages, Splunk jobs, shown in the job "
                        "menu within Splunk. You can also query for "
                        "component health and fired alerts."),
                 choices=[
                     ("license_state", _("Licence state")),
                     ("license_usage", _("Licence usage")),
                     ("system_msg", _("System messages")),
                     ("jobs", _("Jobs")),
                     ("health", _("Health")),
                     ("alerts", _("Alerts")),
                 ],
                 default_value=[
                     "license_state", "license_usage", "system_msg", "jobs", "health", "alerts"
                 ],
                 allow_empty=False,
             )),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_splunk(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:splunk",
        valuespec=_valuespec_special_agents_splunk,
    ))


def _factory_default_special_agents_jenkins():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_jenkins():
    return Dictionary(
        title=_("Check state of Jenkins jobs and builds"),
        help=_("Requests data from a jenkins instance."),
        optional_keys=["port"],
        elements=[
            ("instance",
             TextAscii(
                 title=_("Jenkins instance to query."),
                 help=_("Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "hostname here, eg. my_jenkins.com."),
                 size=32,
                 allow_empty=False,
             )),
            ("user",
             TextAscii(
                 title=_("Username"),
                 help=_("The username that should be used for accessing the "
                        "jenkins API. Has to have read permissions at least."),
                 size=32,
                 allow_empty=False,
             )),
            ("password",
             PasswordFromStore(
                 help=_("The password or API key of the user."),
                 title=_("Password of the user"),
                 allow_empty=False,
             )),
            (
                "protocol",
                DropdownChoice(title=_("Protocol"),
                               choices=[
                                   ("http", "HTTP"),
                                   ("https", "HTTPS"),
                               ],
                               default_value="https"),
            ),
            ("port",
             Integer(
                 title=_("Port"),
                 help=_(
                     "Use this option to query a port which is different from standard port 8080."),
                 default_value=443,
             )),
            ("sections",
             ListChoice(
                 title=_("Informations to query"),
                 help=_("Defines what information to query. You can choose "
                        "between the instance state, job states, node states "
                        "and the job queue."),
                 choices=[
                     ("instance", _("Instance state")),
                     ("jobs", _("Job state")),
                     ("nodes", _("Node state")),
                     ("queue", _("Queue info")),
                 ],
                 default_value=["instance", "jobs", "nodes", "queue"],
                 allow_empty=False,
             )),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_jenkins(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:jenkins",
        valuespec=_valuespec_special_agents_jenkins,
    ))


def _factory_default_special_agents_zerto():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_zerto():
    return Dictionary(
        elements=[
            ("authentication",
             DropdownChoice(title=_('Authentication method'),
                            choices=[
                                ('windows', _('Windows authentication')),
                                ('vcenter', _('VCenter authentication')),
                            ],
                            help=_("Default is Windows authentication"))),
            ('username', TextAscii(title=_('Username'), allow_empty=False)),
            ('password', TextAscii(
                title=_('Password'),
                allow_empty=False,
            )),
        ],
        title=_("Check state of Zerto"),
        help=_("This rule selects the Zerto special agent for an existing Checkmk host"))


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:zerto",
        valuespec=_valuespec_special_agents_zerto,
    ))


def _factory_default_special_agents_graylog():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_graylog():
    return Dictionary(
        title=_("Check state of Graylog"),
        help=_("Requests node, cluster and indice data from a graylog "
               "instance."),
        optional_keys=["port"],
        elements=[
            ("instance",
             TextAscii(
                 title=_("Graylog instance to query."),
                 help=_("Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "hostname here, eg. my_graylog.com."),
                 size=32,
                 allow_empty=False,
             )),
            ("user",
             TextAscii(
                 title=_("Username"),
                 help=_("The username that should be used for accessing the "
                        "graylog API. Has to have read permissions at least."),
                 size=32,
                 allow_empty=False,
             )),
            ("password", PasswordFromStore(
                title=_("Password of the user"),
                allow_empty=False,
            )),
            ("protocol",
             DropdownChoice(
                 title=_("Protocol"),
                 choices=[
                     ("http", "HTTP"),
                     ("https", "HTTPS"),
                 ],
                 default_value="https",
             )),
            ("port",
             Integer(
                 title=_("Port"),
                 help=_(
                     "Use this option to query a port which is different from standard port 443."),
                 default_value=443,
             )),
            ("since",
             Age(
                 title=_("Time for coverage of failures"),
                 help=_(
                     "Use this option to set the timeframe in which failures should be covered."),
                 default_value=1800,
             )),
            ("sections",
             ListChoice(
                 title=_("Informations to query"),
                 help=_("Defines what information to query. You can choose "
                        "between the alarms, collectors, cluster statistics, "
                        "failures, jvm heap size, message count, nodes and sidecar "
                        "fleet."),
                 choices=[
                     ("alerts", _("Alarms")),
                     ("collectors", _("Collectors")),
                     ("cluster_stats", _("Cluster statistics")),
                     ("cluster_traffic", _("Cluster traffic statistics")),
                     ("failures", _("Failed index operations")),
                     ("jvm", _("JVM heap size")),
                     ("messages", _("Message count")),
                     ("nodes", _("Nodes")),
                     ("sidecars", _("Sidecar fleet")),
                 ],
                 default_value=[
                     "alerts", "collectors", "cluster_stats", "cluster_traffic", "failures", "jvm",
                     "messages", "nodes", "sidecars"
                 ],
                 allow_empty=False,
             )),
            ("display_node_details",
             DropdownChoice(
                 title=_("Display node details on"),
                 help=_("The node details can be displayed either on the "
                        "queried host or the graylog node."),
                 choices=[
                     ("host", _("The queried graylog host")),
                     ("node", _("The graylog node")),
                 ],
                 default_value="host",
             )),
            ("display_sidecar_details",
             DropdownChoice(
                 title=_("Display sidecar details on"),
                 help=_("The sidecar details can be displayed either on the "
                        "queried host or the sidecar host."),
                 choices=[
                     ("host", _("The queried graylog host")),
                     ("sidecar", _("The sidecar host")),
                 ],
                 default_value="host",
             )),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_graylog(),
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:graylog",
        valuespec=_valuespec_special_agents_graylog,
    ))


def _valuespec_special_agents_couchbase():
    return Dictionary(
        title=_("Check state of couchbase servers"),
        help=_("This rule allows to select a couchbase server to monitor as well as "
               "configure buckets for further checks"),
        elements=[
            ("buckets",
             ListOfStrings(title=_("Bucket names"), help=_("Name of the Buckets to monitor."))),
            ("timeout",
             Integer(title=_("Timeout"),
                     default_value=10,
                     help=_("Timeout for requests in seconds."))),
            ("port",
             Integer(title=_("Port"),
                     default_value=8091,
                     help=_("The port that is used for the api call."))),
            ("authentication",
             Tuple(title=_("Authentication"),
                   help=_("The credentials for api calls with authentication."),
                   elements=[
                       TextAscii(title=_("Username"), allow_empty=False),
                       PasswordFromStore(title=_("Password of the user"), allow_empty=False)
                   ])),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=watolib.Rulespec.FACTORY_DEFAULT_UNUSED,
        group=RulespecGroupDatasourcePrograms,
        name="special_agents:couchbase",
        valuespec=_valuespec_special_agents_couchbase,
    ))
