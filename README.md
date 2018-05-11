# RedDrum-Aggregator  
A python based Redfish service that implements a rack-level Redfish Aggregator of multiple monolythic servers.
Developed to run on an Open Source Top-of-Rack Switch

## About ***RedDrum-Aggregator***

***RedDrum-Aggregator*** is a python app that leverages the RedDrum-Frontend and implements a single point of management Redfish Service aggregator for an entire rack of monolythic servers connected via a management network.
Generally the service runs as a container in the rack Top-of-rack (TOR) Open Linux switch

As a RedDrum Redfish Service implementation: 
* The ***Frontend*** is implemented by RedDrum-Frontend and the package name is **reddrum_frontend**
  * see RedDrum-Redfish-Project/RedDrum-Frontend/README.md and RedDrum-Frontend/reddrum_frontend/README.txt for details

* The ***Backend***  is implemented as a package from this  repo (RedDrum-OpenBMC) -- named **reddrum_openbmc**

* The ***Httpd Config*** is implemented with Apache2 and configured by running setup scripts from RedDrum-Httpd-Configs/OpenBMC-Apache2-ReverseProxy

* The ***RedDrum-Aggregator/RedDrumObmcMain.py*** startup script (also in scripts dir) implements the calls to the frontend
and backend to start-up the service.

## RedDrum-Aggregator Feature Level
The RedDRum-OpenBMC service strives to implement a feature level compatible with the OCP Base Server Profile
* Mandatory OCP Base Server Profile features are all implemented
* Some Recommended features are implemented
* a few features beyond the recommended level may be implemented


## About the ***RedDrum Redfish Project***
The ***RedDrum Redfish Project*** includes several github repos for implementing python Redfish servers.
* RedDrum-Frontend  -- the Redfish Service Frontend that implements the Redfish protocol and common service APIs
* RedDrum-Httpd-Configs -- docs and setup scripts to integrate RedDrum with common httpd servers eg Apache and NGNX
* RedDrum-OpenBMC -- a "high-fidelity" simulator built on RedDrum with several feature profiles and server configs
* RedDrum-OpenBMC -- a RedDrum Redfish service integrated with the OpenBMC platform

## Architecture 
SEE: github.com/RedDrum-Redfish-Project/RedDrum-Frontend/README.md for description of the architecture
RedDrum Redfish Service Architecture breaks the Redfish service into three parts:
* A standard httpd service
* The RedDrum-Frontend -- the implementation independent frontend code is implemented leveraging RedDrum-Frontend 
* RedDrum Backend -- The backend implementation-depended interfaces to the real hardware resources
  * The full Backend code for the RedDrum-OpenBMC is included in this repo in package reddrum_openbmc
* The `redDrumObmcMain.py` Startup Script -- used to start the service.  It uses APIs to the Frontend and Backend to initialize Resource, initiate HW resource discovery, and Startup the Frontend Flask app.
  * the RedDrumObmcMain.py script is in this repo for the OpenBMC service

## Conformance Testing
Re-running of SPMF conformance tests is currently in progress.
* List of DMTF/SPMF Conformance tools being used:
  * Mockup-Creator
  * Service-Validator
  * JsonSchema-Response-Validator
  * Conformance-Check
  * (new) Ocp Base Server Profile Tester
* RedDrum-specific tests (not yet open sourced)
  * RedDrum-URI-Tester -- tests against all supported URIs for specific simulator profiles
  * RedDrum-Stress-Tester -- runs 1000s of simultaneous requests in parallel
---
---
# HOWTO Create and Install a RedDrum Redfish Image on a real OpenBMC #
* 
* 
* 


---
---
## How to Install the RedDrum-OpenBMC on Centos7.1+-- to test with BackendStubs enabled for Linux Testing
#### Manual Install from git clone
* Install on Centos7.1 or later Linux system
* Install and configure the Apache httpd 

```
     yum install httpd
     cd  <your_path_to_Directory_Holding_RedDrumOpenBMC_Code>
     mkdir RedDrumSim
     git clone https://github.com RedDrum-Redfish-Project/RedDrum-Httpd-Configs RedDrum-Httpd-Configs
     cd RedDrum-Httpd-Configs/Apache-ReverseProxy
     ./subSystem_config.sh # creates a httpd.conf file in etc/httpd and creates self-signed ssl certificates
```

* Install the RedDrum-Frontend code

```
     cd  <your_path_to_Directory_Holding_RedDrumOpenBMC_Code>
     git clone http://github.com/RedDrum-Redfish-Project/RedDrum-Frontend  RedDrum-Frontend
```

* Install the RedDrum-OpenBMC code

```
     cd  <your_path_to_Directory_Holding_RedDrumOpenBMC_Code>
     git clone http://github.com/RedDrum-Redfish-Project/RedDrum-OpenBMC  RedDrum-OpenBMC  
```

#### Install using `pip install` from github (currently testing)
* ***currently verifying that installing directly from github using pip install***

#### Install using `pip install` from pypi (not working yet)


### How to Start  the RedDrum-OpenBMC

```
     cd  <your_path_to_Directory_Holding_RedDrumOpenBMC_Code>/RedDrum-OpenBMC/scripts
     ./runRedDrumStubs       # to run with Backend Stubs enables so that the Dbus calls are stubbed out
     ./redRedDrum            # to run on a real OpenBMC BMC where real Dbus calls are used to get HW info
```

### How to Clear Data Caches
The RedDrum Frontend keeps resource data for non-volatile resource models cached in files, so if you add/delete users, change passwords, set AssetTags, etc, the changes will persist stopping and re-starting the simulator
* To clear all data caches to defaults and also clear python caches, run:
  * NOTE that IF YOU CHANGE Simulation Data, you must clear the caches for the changes to appear.

```
     cd  <your_path_to_Directory_Holding_RedDrumOpenBMC_Code>/RedDrum-OpenBMC/scripts
     ./clearCaches
```

---
