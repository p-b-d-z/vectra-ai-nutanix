# Vectra AI
## Nutanix Sensor Install

`ntnx-create-network-function-provider.py` will perform step 5 through 7 of the Vectra AI vSensor installation guide.
`ntnx-cluster-update-sensor.py` will perform step 8 of the Vectra AI vSensor installation.
`ntnx-cluster-update-network.py` will perform step 9 of the Vectra AI vSensor installation.

### Usage - Steps 5-7
Run the first Python script. If you wish to test connectivity first, use the optional `--test` argument. Both scripts support this argument.

#### Linux
```bash
export PC_IP="prism"
export PC_USERNAME="admin"
export PC_PASSWORD="##REPLACE##"
python3 ntnx-create-network-function-provider.py --test
```

#### Windows
```powershell
$env:PC_IP = "prism"
$env:PC_USERNAME = "admin"
$env:PC_PASSWORD = "##REPLACE##"
python3 ntnx-create-network-function-provider.py --test
```

```console
Connecting to prism as admin...
Located cluster: prod (0005330b-d6c7-1193-0000-00000000c1da)
Located cluster: uat (0005465d-1a12-3e95-0000-000000010ac4)
Located cluster: dev (000531f3-621b-dc20-0000-00000000a3ed)
Located cluster: prism (dcc6e0fa-e6f0-42ed-b337-763287281a79)
```

After testing, remove the argument and run again.
```console
$ python3 ntnx-create-network-function-provider.py

Connecting to prism as admin...
Created network function provider category
Assigned value vectra_ai to network function provider
Verified provider categories: [{'value': 'vectra_ai', 'description': '', 'system_defined': False}]
Successfully verified that provider value "vectra_ai" exists
Creating chain for cluster: prod (000583ae-b278-3412-224a-6805ca999194)
Created network function chain: 1effa8be-cf3e-4671-9302-88c8dd2fcb14
Creating chain for cluster: uat (000583a8-ed27-2b0d-5e13-6805ca999510)
Created network function chain: c0c47ccb-3799-440c-a3f4-1cefe8d5c802
Creating chain for cluster: dev (000583af-04ba-61c7-3d33-6805ca998eec)
Created network function chain: dadcc2a1-df30-4bbc-8f3d-1344b668719d
Creating chain for cluster: prism (a288bd93-db1d-4314-861e-524a750c6be4)
Created network function chain: dc8c8efd-6939-430c-afbc-d42e002dfe1c
```

### Intermission
Perform step 8.1 to update vSensor settings using `acli`.

### Usage - Step 8

Run the next command. Use `--test` to validate the script can locate the vSensor.
```console
$ python3 ntnx-cluster-update-sensor.py --vm-name vSensor --test

Connecting to prism as admin...
Looking for VM with name: template
Found VM: vSensor (UUID: bf380ff7-4c3f-40b6-ad43-5a799b5d8cd8)
```

After testing, remove the argument and run again.
```console
python3 ntnx-cluster-update-sensor.py --vm-name vSensor

Connecting to prism as admin...
Looking for VM with name: pn-vectra-sensor4
Found VM: pn-vectra-sensor4 (UUID: 4b14fa0e-2ed8-479e-88d5-cf29658f13b9)
Updating vSensor VM with provider value vectra_ai...
Update completed successfully
```

If you run it again, it should confirm that the category already exists.
```console
python3 ntnx-cluster-update-sensor.py --vm-name vSensor

Connecting to prism as admin...
Looking for VM with name: vSensor
Found VM: vSensor (UUID: 4b14fa0e-2ed8-479e-88d5-cf29658f13b9)
Updating vSensor VM with provider value vectra_ai...
Network function provider category already exists for VM 4b14fa0e-2ed8-479e-88d5-cf29658f13b9
Update completed successfully
```

### Usage - Step 9

Run the next command. Use `--test` to validate the scrript can locate the chain and networks to tap.
```console
$ python3 ntnx-cluster-update-network.py --vlan-id 100 --test

Connecting to prism as admin...
Looking for vectra_tap network function chains...

Found vectra_tap chains in 1 cluster(s):

Cluster: prod
  Chain UUID: c0c47ccb-3799-440c-a3f4-1cefe8d5c802
  Created: 2025-03-04T02:35:30Z

Looking for networks with VLAN ID: 100

Found 1 network(s) with VLAN ID 100:

Network: Servers
  UUID: 48f02a74-5290-4e31-9f81-c38342d33411
  Cluster: prod
  Has chain reference: False
  Matching chain UUID: c0c47ccb-3799-440c-a3f4-1cefe8d5c802
```

After testing, remove the argument and run again.
```console
python3 ntnx-cluster-update-network.py --vlan-id 100

Connecting to prism as admin...
Looking for vectra_tap network function chains...
Found vectra_tap chains in 1 clusters:

Cluster: prod
  Chain UUID: c0c47ccb-3799-440c-a3f4-1cefe8d5c802
  Created: 2025-03-04T02:35:30Z

Looking for networks with VLAN ID: 107

Found 1 network(s) with VLAN ID 107 in matching clusters

Processing network: Servers
  UUID: 48f02a74-5290-4e31-9f81-c38342d33411
  Cluster: prod
  Chain UUID: c0c47ccb-3799-440c-a3f4-1cefe8d5c802
Updating network Servers with network function chain reference...
Successfully updated network Servers
```
