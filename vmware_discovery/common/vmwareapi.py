# coding=utf-8

"""
A connection to the VMware vCenter platform.
"""

from oslo_log import log as logging
from oslo_vmware import api
from oslo_vmware import vim
from oslo_config import cfg
from vmware_discovery.common import config

CONF = config.CONF
LOG = logging.getLogger(__name__)

vmwareapi_opts = [
    cfg.StrOpt('host_ip',
               help='Hostname or IP address for connection to VMware '
                    'vCenter host.'),
    cfg.PortOpt('host_port',
                default=443,
                help='Port for connection to VMware vCenter host.'),
    cfg.StrOpt('host_username',
               help='Username for connection to VMware vCenter host.'),
    cfg.StrOpt('host_password',
               help='Password for connection to VMware vCenter host.',
               secret=True),
    cfg.StrOpt('ca_file',
               help='Specify a CA bundle file to use in verifying the '
                    'vCenter server certificate.'),
    cfg.BoolOpt('insecure',
                default=False,
                help='If true, the vCenter server certificate is not '
                     'verified. If false, then the default CA truststore is '
                     'used for verification. This option is ignored if '
                     '"ca_file" is set.'),
    cfg.StrOpt('cluster_name',
               help='Name of a VMware Cluster ComputeResource.'),
    cfg.StrOpt('datastore_regex',
               help='Regex to match the name of a datastore.'),
    cfg.FloatOpt('task_poll_interval',
                 default=0.5,
                 help='The interval used for polling of remote tasks.'),
    cfg.IntOpt('api_retry_count',
               default=10,
               help='The number of times we retry on failures, e.g., '
                    'socket error, etc.'),
    cfg.PortOpt('vnc_port',
                default=5900,
                help='VNC starting port'),
    cfg.IntOpt('vnc_port_total',
               default=10000,
               help='Total number of VNC ports'),
    cfg.BoolOpt('use_linked_clone',
                default=True,
                help='Whether to use linked clone'),
    cfg.StrOpt('wsdl_location',
               help='Optional VIM Service WSDL Location '
                    'e.g http://<server>/vimService.wsdl. '
                    'Optional over-ride to default location for bug '
                    'work-arounds')
]

CONF.register_opts(vmwareapi_opts, 'vmware')


class VMwareAPISession(api.VMwareAPISession):
    """Sets up a session with the VC/ESX host and handles all
    the calls made to the host.
    """
    def __init__(self, host_ip=CONF.vmware.host_ip,
                 host_port=CONF.vmware.host_port,
                 username=CONF.vmware.host_username,
                 password=CONF.vmware.host_password,
                 retry_count=CONF.vmware.api_retry_count,
                 scheme="https",
                 cacert=CONF.vmware.ca_file,
                 insecure=CONF.vmware.insecure):
        super(VMwareAPISession, self).__init__(host=host_ip,
                                               port=host_port,
                                               server_username=username,
                                               server_password=password,
                                               api_retry_count=retry_count,
                                               task_poll_interval=CONF.vmware.task_poll_interval,
                                               scheme=scheme,
                                               create_session=True,
                                               wsdl_loc=CONF.vmware.wsdl_location,
                                               cacert=cacert,
                                               insecure=insecure)

    def _is_vim_object(self, module):
        """Check if the module is a VIM Object instance."""
        return isinstance(module, vim.Vim)

    def _call_method(self, module, method, *args, **kwargs):
        """Calls a method within the module specified with
        args provided.
        """
        if not self._is_vim_object(module):
            return self.invoke_api(module, method, self.vim, *args, **kwargs)
        else:
            return self.invoke_api(module, method, *args, **kwargs)

    def _wait_for_task(self, task_ref):
        """Return a Deferred that will give the result of the given task.
        The task is polled until it completes.
        """
        return self.wait_for_task(task_ref)

# vim: tabstop=4 shiftwidth=4 softtabstop=4
