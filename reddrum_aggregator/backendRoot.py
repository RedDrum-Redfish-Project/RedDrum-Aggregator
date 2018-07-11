
# Copyright Notice:
#    Copyright 2018 Dell, Inc. All rights reserved.
#    License: BSD License.  For full license text see link: https://github.com/RedDrum-Redfish-Project/RedDrum-OpenBMC/LICENSE.txt

# Backend root class for OpenBMC
import os
import json
import inspect
from .chassisBackend   import RdChassisBackend
from .managersBackend  import RdManagersBackend
from .systemsBackend   import RdSystemsBackend

from .startupResourceDiscovery   import RdStartupResourceDiscovery
from .oemFrontendUtils  import DellESI_FrontendOemUtils


class RdBackendRoot():
    def __init__(self,rdr):
        # initialize data
        self.backendStatus=0
        self.discoveryState = 0
        self.rdr = rdr
        self.oemUtils=DellESI_FrontendOemUtils(rdr)
        #   valid rdBeIdConstructionRule values are:  "Monolythic", "Dss9000", "Aggregator"
        self.rdBeIdConstructionRule="Aggregator"
        self.includeRackScaleOemProperties=True
        self.isSimulator=False
        self.pduApiScript=None
        self.credentialsDb={ "BMC0": {"User": "root", "Password": "redfish", "BmcType": "Generic"  } }

        # create backend sub-classes
        self.createSubObjects(rdr)

        # run startup tasks
        self.startup(rdr)

    def createSubObjects(self,rdr):
        #create subObjects that implement backend APIs
        self.chassis=RdChassisBackend(rdr)
        self.managers=RdManagersBackend(rdr)
        self.systems=RdSystemsBackend(rdr)
        self.backendStatus=1
        return(0)


    def startup(self,rdr):
        # set the data paths for RedDrum-Aggregator 
        rdSvcPath=os.getcwd()

        rdr.baseDataPath=os.path.join(rdr.frontEndPkgPath,"Data")
        print("DEBUG: baseDataPath: {}".format(rdr.baseDataPath))

        # FIX final paths for RedDrum-Aggregator /var and /etc...
        rdr.varDataPath=os.path.join("/var", "www", "rf")
        print("DEBUG: varDataPath: {}".format(rdr.varDataPath))

        # if we have a RedDrum.conf file in etc/ use it. otherwise use the default
        #rdr.RedDrumConfPath=os.path.join(rdSvcPath, "RedDrum.conf" )
        redDrumConfPathEtc=os.path.join("/etc",  "RedDrum.conf" )
        redDrumConfPathFrontend=os.path.join(rdr.frontEndPkgPath, "RedDrum.conf")
        if os.path.isfile(redDrumConfPathEtc):
            rdr.RedDrumConfPath=redDrumConfPathEtc
        else:
            rdr.RedDrumConfPath=redDrumConfPathFrontend
        print("DEBUG: RedDrumConfPath: {}".format(rdr.RedDrumConfPath))

        # set path to schemas -- not used now
        rdr.schemasPath = os.path.join(rdSvcPath, "schemas") #not used now

        # set path to bash scripts to run to get data from Linux
        self.backendScriptsPath = os.path.dirname( inspect.getfile(RdBackendRoot))
        print("DEBUG: backendScriptsPath: {}".format(self.backendScriptsPath))

        # set path to backend data files for static rack server discovery and static test lldp output file
        self.backendDiscoveryFilePaths = self.backendScriptsPath 

        # set the path to the bmc credentials file
        #   - note that discovery will try to load a credentials dict from file: bmcCredentials.json at this path
        #   - if the file does not exist, no credentials will be loaded
        #rdr.bmcCredentialsPath=os.path.join("/etc","opt","dell","redfish-aggregator","Credentials","bmcuser",".passwd")
        rdr.bmcCredentialsPath = os.path.dirname( inspect.getfile(RdBackendRoot))

        # note that syslog logging is enabled on RedDrum-Aggregator by default unless -L (isLocal) option was specified
        # turn-on console messages "also" however
        rdr.printLogMsgs=True

        # RedDrum-Aggregator uses dynamic discovery and no persistent cache database files
        # rdr.rdProfile may point to different configs supported during dynamic discovery
        rdr.useCachedDiscoveryDb=False
        rdr.useStaticResourceDiscovery=False

        self.backendStatus=2
        return(0)


    # runStartupDiscovery is called from RedDrumMain once both the backend and frontend resources have been initialized
    #   it will discover resources and then kick-off any hardware monitors in separate threads
    def runStartupDiscovery(self, rdr):
        # For RedDrum-Aggregator, Discovery calls a customizable discovery based on the rdr.rdProfile setting
        rdr.logMsg("INFO"," ....Launching Startup Discovery based on Config Profile: {}".format(rdr.rdProfile))

        discvr=RdStartupResourceDiscovery(rdr)

        # Do Phase-1 Discovery -- add Managers, Chassis, and Systems Resources
        rc=discvr.discoverResourcesPhase1(rdr)
        if( rc != 0):
            self.discoveryState = 1001 # failed trying to discover resources
            rdr.logMsg("ERROR"," ..ERROR: Resource Discovery Phase-1 Failed rc={}. Aborting discovery".format(rc))
            return(rc)

        self.discoveryState = 1
        rdr.logMsg("INFO"," ....Resource Discovery Phase-1 Complete. Starting Phase-2 Discovery")

        # Do Phase-2 Discovery -- start HwMonitors if running any in background
        # phase2 discovery just returns 0 if there are no monitors running
        rc=discvr.discoverResourcesPhase2(rdr)
        if( rc != 0):
            self.discoveryState = 1002 # failed trying to discover resources
            rdr.logMsg("ERROR"," ..ERROR: Resource Discovery Phase-2 Failed rc={}. Aborting discovery".format(rc))
            return(rc)

        rdr.logMsg("INFO"," ....Resource Discovery Phase-2 Complete. ")

        return(rc)




    # Backend APIs  
    # POST to Backend
    def postBackendApi(self, request, apiId, rdata):
        # handle backend auth based on headers in request
        # handle specific post request based on apiId and rdata
        rc=0
        statusCode=204
        return(rc,statusCode,"","",{})

    # GET from  Backend
    def getBackendApi(self, request, apiId):
        # handle backend auth based on headers in request
        # handle specific post request based on apiId and rdata
        rc=0
        resp={}
        jsonResp=(json.dumps(resp,indent=4))
        statusCode=200
        return(rc,statusCode,"",jsonResp,{})




