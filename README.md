# vmware-discovery
Openstack Cloud Platform to register for the Virtual Machine for vmware driver


## This driver include:
- instance-discovery 
- portgroup-discovery
- template-discovery


## Installing
```
cd vmware-discovery
python setup.py install
```

## Configure
 - vmware-discovery.conf


## Running
`/usr/bin/vmware-discovery --config-file /etc/vmware-discovery.conf`


## Running once
```
sync_instance.py --config-file /etc/vmware-discovery.conf
sync_portgroup.py --config-file /etc/vmware-discovery.conf
sync_template.py --config-file /etc/vmware-discovery.conf
```

## Configure Service
- init.d/vmware-discovery
- systemd/openstack-vmware-discovery.service

