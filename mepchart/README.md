# NetEdge-MEP
The NetEdge-MEP is a CNF-based ETSI-MEC compliant MEP.

NetEdge-MEP is part of NetEdge project, for more information on NetEdge, please check https://www.netedge.pt/

The NetEdge-MEP micro-service architecture is composed of:

- MEP Service: provides MEP functionalities for MEPM and MEC Apps, using the Mp1 and Mm5 interfaces.
  - Source-code: https://github.com/UMinho-Netedge/netedge-mep-uminho
  - Mp1 interface documentation: https://forge.etsi.org/rep/mec/gs011-app-enablement-api
  - Mm5 interface docummentation: https://app.swaggerhub.com/apis-docs/vinicf/mepm-api/

- OAuth 2.0 Service:  manages MEC App authorization.
  - Source-code: https://github.com/UMinho-Netedge/oauth-server
  
- DNS Service: provides service discovery by name, to access services produced and registered by MEC Apps. The DNS Service is composed of a DNS API that configures a CoreDNS server.
  - Source-code: https://github.com/UMinho-Netedge/dns_ext

If you use it, please refer to: xxx

# How to install

You should first have a Kubernetes cluster configured and helm v3 installed to run it.
The NetEdge MEP also requires two persistent volumes with at least 1GB each.
The volumes should have storage classes mongodb-class and dns-class.

## Using it as a helm chart repository

### Add as a helm repository
```bash
helm repo add netedge-mep https://uminho-netedge.github.io/NetEdge-MEP/
```
### Installing the chart
```bash
helm install <chart-name> netedge-mep/netedge-mep
```


## Download and generate helm chart
### Create chart
```bash
#In the current directory
helm package .
```
### Usage
```bash
# Without replace
helm install NetEdge-MEP <chart_name>
```

## Using it as a Network Service in ETSI Open Source MANO (OSM)
### Add the helm repository in OSM k8s Repos
```bash
osm repo-add --type helm-chart --description "UMinho NetEdge Repo" netedge-mep https://uminho-netedge.github.io/NetEdge-MEP/
```
### Create the KNF and NS in OSM
Download the files netedge-mep_knf.tar.gz and netedge-mep_ns.tar.gz of this repository and use them to create the packages on OSM
```bash
osm vnfd-create netedge-mep_knf.tar.gz
osm nsd-create netedge-mep_ns.tar.gz
```
### Instantiate MEP as a NS
```bash
osm ns-create --ns_name netedge-mep --nsd_name netedge-mep_ns --vim_account <VIM_NAME|VIM_ID>
```
