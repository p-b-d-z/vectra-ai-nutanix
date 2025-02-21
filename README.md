# Vectra AI
## Nutanix Sensor Install

`ntnx-create-network-function-provider.py` will perform step 5 through 7 of the Vectra AI vSensor installation guide.
`ntnx-cluster-update-sensor.py` will perform step 8 of the Vectra AI vSensor installation.

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

After testing, remove the argument and run again.
```console
$ python3 ntnx-create-network-function-provider.py

Connecting to prism as admin...
Located cluster: ntnx-cluster-1 (0005330b-d6c7-1193-0000-00000000c1da)
Located cluster: ntnx-cluster-2 (0005465d-1a12-3e95-0000-000000010ac4)
Located cluster: ntnx-cluster-3 (000531f3-621b-dc20-0000-00000000a3ed)
Located cluster: prism (dcc6e0fa-e6f0-42ed-b337-763287281a79)
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
```
