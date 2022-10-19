A Helm Chart for ETSI MEC Platform developed by ALGORITMI Centre - UMinho

### Create chart
```bash
#In the current directory
helm package .
```
### Usage
```bash
NS=<namespace>
RELEASE=<release>

helm install -n $NS --wait --timeout 10m $RELEASE <chart_name> --debug
