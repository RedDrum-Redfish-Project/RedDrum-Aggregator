# RedDrum-Aggregator  
A python based Redfish service that implements a rack-level Redfish Aggregator of multiple monolythic servers.
Developed to run on a linux host--server or IOT appliance or an Open Source Linux-basedTop-of-Rack Switch

## About ***RedDrum-Aggregator***

***RedDrum-Aggregator*** is a python app that leverages the RedDrum-Frontend and implements a single point of management Redfish Service aggregator for an entire rack of monolythic servers connected via a management network.
Generally the service runs as a container in the rack Top-of-rack (TOR) Open Linux switch.
However, it can run on any Linux host that runs Python3.4 or later and could be a separate monolythic server, or an IOT gateway.

As a RedDrum Redfish Service implementation: 
* The ***Frontend*** is implemented by RedDrum-Frontend and the package name is **reddrum_frontend**
  * see RedDrum-Redfish-Project/RedDrum-Frontend/README.md and RedDrum-Frontend/reddrum_frontend/README.txt for details
  * note that the latest Aggregator backend requires using **"v2.0"** or later (the master branch) of RedDrum-Frontend

* The ***Backend***  is implemented as a package from this  repo (RedDrum-OpenBMC) -- named **reddrum_openbmc**

* The ***Httpd Config*** is implemented with Apache2 and configured by running setup scripts from RedDrum-Httpd-Configs/OpenBMC-Apache2-ReverseProxy

* The ***RedDrum-Aggregator/RedDrumAggregatorMain.py*** startup script (also in scripts dir) implements the calls to the frontend
and backend to start-up the service.

## About the ***RedDrum Redfish Project***
The ***RedDrum Redfish Project*** includes several github repos for implementing python Redfish servers.
* RedDrum-Frontend  -- the Redfish Service Frontend that implements the Redfish protocol and common service APIs
* RedDrum-Httpd-Configs -- docs and setup scripts to integrate RedDrum with common httpd servers eg Apache and NGNX
* RedDrum-Simulator -- a "high-fidelity" simulator built on RedDrum with several feature profiles and server configs
* RedDrum-OpenBMC -- a RedDrum Redfish service integrated with the OpenBMC platform
* RedDrum-Aggregator -- a RedDrum Redfish service that transparently integrates multiple monolythics into one Redfish Service

## Architecture 
SEE: github.com/RedDrum-Redfish-Project/RedDrum-Frontend/README.md for description of the architecture
RedDrum Redfish Service Architecture breaks the Redfish service into three parts:
* A standard httpd service
* The RedDrum-Frontend -- the implementation independent frontend code is implemented leveraging RedDrum-Frontend 
* RedDrum Backend -- The backend implementation-depended interfaces to the real hardware resources
  * The full Backend code for the RedDrum-Aggregator is included in this repo in package reddrum_aggregator
* The `redDrumAggregatorMain.py` Startup Script -- used to start the service.  It uses APIs to the Frontend and Backend to initialize Resource, initiate HW resource discovery, and Startup the Frontend Flask app.
  * Some BASH scripts in `RedDrum-Aggregator/scripts` can be used to start the aggregator with various options to clear cache or run in local mode where cache data is not stored at /var.   See section below "Starting RedDrum-Aggregator"


## The Current **v2** RedDrum-**Aggregator** Features
* **NOTE: The aggregator must be paired with the "V2" branch of RedDrum-Frontend (which is the master branch)**

* This "v2.0" Aggregator is now a "near Transparent" aggregator:
  * The members array for the main resource "Collections" (Systems, Chassis, Managers) are saved
        after discovery so that the GET "/redfish/v1/<Collection>" response is fast
        The response of the collections is built from this discovered and saved/cached data

  * The responses for resources below the collections is not cached however.
        So any GET, Patch, Post/Delete that targets a resource below the main collections results in a
        transparent request to the aggregated server, and the response from the server is then
        "processed" [or 'localized'] such that any URI links returned by the aggregated BMC has been modified
        so that they main collection IDs are unique across the entire aggregation

* The benefit of the "near Transparent" aggregation:
  *  All of the Oem data and APIs supported by an aggregated server are automatically supported.
       Even Oem Post actions get automatically supported.
  *  The aggregator does not have to change as new properties are features are added for a BMC

* Redfish Resources that v2.0 Aggregator Backend supports true aggregation of:
  * All APIs under the /Chassis collection,
  * All APIs under the /Managers collection,
  * All APIs under the /Systems  collection
  * The Link header URIs that point to locally stored [possibly Oem or Modified] schemas on aggregated BMCs
    but links inside a locally stored schema file that is relative to the BMC's IP is not being localized
        (but internal links that are relative to the file they are in are OK, or links to external sites are ok)

* Future Features -- not yet supported by the v2 Aggregator:
  * Fully localizing links inside locally stored schema files returned by a BMC that are relative to the BMC's IP
  * TaskService/Tasks collection  (although a task Uri returned by server in Location header will work correctly)
  * UpdateService APIs
  * EventService/Events aggregation and subscribing to events coming from aggregated servers
  * JsonSchemas and Registries Collection support for locally stored or Oem schemas used by aggregated servers
  * $metadata and Odata service doc responses that contain all resource supported by all aggregated servers


* Header Support:
  * The Aggregator Frontend provides the Request Header processing.
  * The Aggregator Backend provides general Response Header processing eg Server, Odata-Version, etc
  * The Backend uses BMC responses but filters some headers (eg Content-Type) to insure conformance with the spec
  * If the Link header returned by an aggregated BMCs points to a local schema store on the BMC, the
     link header is processed [or localized] such that if a client does a GET to the link, it would be
     proxied to the bmc and the locally stored schema on that BMC would return the data


* Local Aggregator Resources Created by the Backend:
  * The RedDrum-Aggregator implements the following resource in backend-code:
     (these can be configured to be included or not in the aggregatorConfig.py file
     1) -- The Aggregator Manager  -- the external manager that runs the aggregator service
     2) -- The [Rack Enclosure] Chassis -- the overall enclosure of aggregated servers
     3) -- The Aggregation Management Switch -- switch that connects the Aggregation Manager to all of the BMCs
     4) -- The optional Aggregation Manager Host -- the chassis that contains the aggregation manager service if it is not
          running inside the management switch
  * These "local resource" are implemented in separate code Classis in the backend
  * Properties eg AssetTag are stored in persistent files by the Aggregation Manager

### RedDrum-**Frontend** Provides the following features for the Aggregator
* ServiceRoot Implementation -- that contains the main resource collections
* AccountService implementation
  * The privilege mapping is done consistently by the frontend for all aggregated servers
  * All authentication and authorization is consistently done by the Frontend
* SessionService implementation
  * Redfish Session Auth is implemented totally in the frontend
* Redfish ServiceRoot level APIs
  * EventService -- some service-level processing will remain in frontend, but backend support is required
  * TaskService  -- some service-level processing will remain in frontend, but backend support is required
  * UpdateService-- some service-level processing will remain in frontend, but backend support is required
* schema collections
  * `/redfish/v1/$Metadata`
  * `/redfish/v1/odata`


## RedDrum-Aggregator Required **"v2"** version of RedDrum-Frontend



## Conformance Testing
Re-running of SPMF conformance tests is currently in progress.
* List of DMTF/SPMF Conformance tools being used:
  * Mockup-Creator
  * Service-Validator  -- some issues being worked
  * JsonSchema-Response-Validator
  * Conformance-Check
  * (new) Ocp Base Server Profile Tester
* RedDrum-specific tests (not yet open sourced)
  * RedDrum-URI-Tester -- tests against all supported URIs for specific simulator profiles
  * RedDrum-Stress-Tester -- runs 1000s of simultaneous requests in parallel

---

## How to Install the RedDrum-Aggregator on a Centos7.1+ or Linux host 
#### Manual Install from git clone
* Install and configure the Apache httpd 

```
     yum install httpd
     cd  <your_path_to_Directory_Holding_RedDrum_Code>
     mkdir RedDrumSim
     git clone https://github.com RedDrum-Redfish-Project/RedDrum-Httpd-Configs RedDrum-Httpd-Configs
     cd RedDrum-Httpd-Configs/Apache-ReverseProxy
     ./subSystem_config.sh # creates a httpd.conf file in etc/httpd and creates self-signed ssl certificates
```

* Get the RedDrum-Frontend code from Github and install it into site packages with pip

```
     cd  <your_path_to_Directory_Holding_RedDrum_Code>
     git clone http://github.com/RedDrum-Redfish-Project/RedDrum-Frontend  RedDrum-Frontend # gets latest v2 Frontend
     pip install ./RedDrum-Frontend 
     # or if you want to edit Frontend code and not have to pip uninstall and reinstall each time, link current dir using -e
     #   pip install -e ./RedDrum-Frontend if you want to edit Frontend code later
```

* Install the RedDrum-Aggregator code

```
     cd  <your_path_to_Directory_Holding_RedDrum_Code>
     git clone http://github.com/RedDrum-Redfish-Project/RedDrum-Aggregator  RedDrum-Aggregator  
```


### Starting  the RedDrum-Aggregator

```
     # To start the aggregator and put data caches at /var/www/rf/db/ #which requires root access
     cd  <your_path_to_Directory_Holding_RedDrum_Code>/RedDrum-Aggregator
     su root  # make sure you are root
     python3 redDrumAggregatorMain.py

     # To start in "local" mode as non-root and store all the data caches at <your_path_to_Dir_Holding_RedDrum_Code>/var/www/rf/db/ 
     cd  <your_path_to_Directory_Holding_RedDrum_Code>/RedDrum-Aggregator
     ./redRedDrum            # to run on a real OpenBMC BMC where real Dbus calls are used to get HW info
     python3 redDrumAggregatorMain.py -L

```

### How to Clear Data Caches
The RedDrum Frontend keeps resource data for users, passwords, Uuid etc, in a data cache 
Likewise, the Aggregator backend stores local resource settings eg AssetTag in a data cache
* To clear all data caches to defaults and also clear python caches, run:

```
     cd  <your_path_to_Directory_Holding_RedDrum_Code>/RedDrum-Aggregator/scripts
     ./clearCaches
     # or manually clear the caches with:
        rm -R -f /var/www/rf   # if cache data is stored at /var
        rm -R -f ./isLocalData # if runnin in Local -L mode
        rm -r -f ./reddrum_aggregator/__pycache__  # to remove python cache

     # see also some bash scripts at ./scripts that handle some of the cache clearing for dev:
     #   ./scripts/runRedDrum  -- clear all python and data caches and start the service with caches at /var/www/rf/db/
     #   ./scripts/runRedDrumLocal -- clear all python and data caches and run the service with caches at ./isLocalData/var/www/rf/db/
     #   ./scripts/runRedDrumLocalSave -- starts service with caches at ./isLocalData/var/www/rf/db/ but DOES NOT clear caches on start
```

### Starting  the RedDrum-Aggregator
Several RedDrum configuration variables can be set in the "RedDrum.conf" file.
The path to the RedDrum.conf file uses follows the logic below:
```
    If there is a RedDrum.conf at /etc/RedDrum.conf, 
        then the services uses that.
    Else if there a a RedDrum.conf at /<your_path_to_Directory_Holding_RedDrum_Code>/RedDrum-Aggregator/RedDrum.conf
        then the services uses that.
    Else
        the service will use the default RedDrum.conf that is in the RedDrum-Frontend top-level directory 

```

---
