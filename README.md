# Vectra AI
## Nutanix Sensor Install

`ntnx-create-network-function-provider.py` will perform step 5 of the Verca AI vSensor installation guide.

### Usage
Run the Python script to perform all tasks in step 5 through 7. If you wish to test connectivity first, use the optional `--test` argument.

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
python3 ntnx-create-network-function-provider.py
```