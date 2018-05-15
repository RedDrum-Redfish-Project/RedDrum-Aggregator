
# Copyright Notice:
#    Copyright 2018 Dell, Inc. All rights reserved.
#    License: BSD License.  For full license text see link: https://github.com/RedDrum-Redfish-Project/RedDrum-Aggregator/LICENSE.txt

import os
import json
from .aggregatorResourceAdds import RfaResourceAdds
from .lldpParser import RfaLldpApis
from .redfishTransports import BmcRedfishTransport
from .aggregatorConfig import RfaConfig


class RdStartupResourceDiscovery():
    def __init__(self,rdr):
        self.rfaResAdds=RfaResourceAdds(rdr)
        self.rfaLldp=RfaLldpApis()
        self.rdr=rdr
        self.rfaCfg=RfaConfig()  # aggregatorConfig data

        self.debug=False
        #self.debug=True

        # initialize discovery dicts
        self.chassisDict={}
        self.managersDict={}
        self.systemsDict={}
        self.fansDict={}
        self.temperatureSensorsDict={}
        self.powerSuppliesDict={}
        self.voltageSensorsDict={}
        self.powerControlDict={}
        self.mgrNetworkProtocolDict={}
        self.mgrEthernetDict={}

    # --------------------------------------------------

    def discoverResourcesPhase1(self, rdr):
        #PHASE-1a:  discover the rack level enclosure
        rdr.logMsg("INFO","....discovery: running phase-1a.  adding Rack-Level Chassis Enclosure Resource")
        chasId, chasRackEntry = self.rfaResAdds.addRfaRackChassis()
        if chasId is not None:
            self.chassisDict[chasId] = chasRackEntry

        #PHASE-1b:  discover the rack level Mgt Switch chassis
        rdr.logMsg("INFO","....discovery: running phase-1b.  adding Management Switch Chassis resource")
        chasId, chasMgtSwitchEntry = self.rfaResAdds.addRfaMgtSwitchChassis()
        if chasId is not None:
            self.chassisDict[chasId] = chasMgtSwitchEntry 

        #PHASE-1c:  discover the aggregator Manager
        rdr.logMsg("INFO","....discovery: running phase-1c.  adding Redfish Aggregator Manager resource")
        mgrId, mgrAggregatorEntry = self.rfaResAdds.addRfaRedfishAggregatorManager()
        if mgrId is not None:
            self.managersDict[mgrId] = mgrAggregatorEntry 

        #PHASE-1d:  if aggregatorMgr is a separate server chassis from switch, then add it
        if self.rfaCfg.redfishAggregatorIsInsideSwitch is not True:
            rdr.logMsg("INFO","....discovery: running phase-1d.  adding Redfish Aggregator chassis as separate chassis")
            chasId, chasAggregatorHostEntry = self.rfaResAdds.addRfaRedfishAggregatorHostServerChassis()
            if chasId is not None:
                self.chassisDict[chasId] = chasAggregatorHostEntry
        else:
            rdr.logMsg("INFO","....discovery: running phase-1d.  Redfish Aggregator chassis is inside Switch-no addl chassis")


        #PHASE-1e:  discover the list of server IPs from LLDP
        #the output of this phase is that a "rackServersDiscoveryDict" dict is created of form:
        #     { "Environment": "Simulator",
        #     "RackServers": [
        #        { "Id": "svr1", "IPv4Address": "127.0.0.1", "Port": 8001 },
        #        { "Id": "svr2", "IPv4Address": "127.0.0.1", "Port": 8802 }
        #        ] }
        rdr.logMsg("INFO","....discovery: running phase-1e.  discover rack servers in this rack")
        if( self.rfaCfg.discoverRackServersFrom == "LLDP"):
            rdr.logMsg("INFO","........discovering rack servers using LLDP info from Mgt Switch")
            if self.rfaCfg.useTestLldpOutputFile is True:
                rdr.logMsg("INFO","...........using using static LLDP test output file testLldpOutputFile.txt in backend ")
                # read the test LldpOutput file: testLldpOutputFile.txt 
                lldpDiscoveryFilePath=os.path.join(self.rdr.backend.backendDiscoveryFilePaths,"testLldpOutputFile.txt")
                if os.path.isfile(lldpDiscoveryFilePath):
                    # parse the Lldp Output file into a rackServersDiscoveryDict of form shown above
                    rc,rackServersDiscoveryDict = self.rfaLldp.parseLldpShowNeighbors(lldpDiscoveryFilePath)
                    if rc !=0:
                        rdr.logMsg("ERROR","...........Error parsing Lldp Output File")
                else:
                    rdr.logMsg("ERROR","...........Cant find or open Lldp Output File: {}".format(lldpDiscoveryFilePath))
            else:
                # get an LldpOutput file from the MgtSwitch and parse it
                rdr.logMsg("INFO","...........getting LLDP info from Mgt Switch")
                rdr.logMsg("INFO","............ **** currently not supported skipping rack server discovery ***")
        else:
            rdr.logMsg("INFO",
                "........discovering rack servers from static json file: {}".format(self.rfaCfg.discoverRackServersFrom))
            # load the json discovery file into rackServersDiscoveryDict of form shown above.
            # note that "Port" is only used if "Environment"="Simulator"
            rackServersFilename=os.path.join(self.rdr.backend.backendDiscoveryFilePaths, self.rfaCfg.discoverRackServersFrom)
            if os.path.isfile(rackServersFilename):
                rackServersDiscoveryDict = json.loads( open( rackServersFilename, "r").read() )


        #PHASE-1f:  add rack servers to Systems, Chassis, and Managers DBs
        rdr.logMsg("INFO","....discovery: running phase-1f.  getting LLDP database of attached servers")
        if rackServersDiscoveryDict is not None and "RackServers" in rackServersDiscoveryDict:
            environ=None
            isSimulator=False
            if "Environment" in rackServersDiscoveryDict:
                environ = rackServersDiscoveryDict["Environment"]
                if environ == "Simulator":
                    isSimulator=True
                    rdr.backend.isSimulator=True
            for svr in rackServersDiscoveryDict["RackServers"]:
                svrNetloc=None
                svrMac=None
                svrId=None
                #extract the Id and create a netloc for each server
                if "Id" in svr and "IPv4Address" in svr:
                    svrId = svr["Id"]
                    svrIpv4Addr = svr["IPv4Address"]
                    svrNetloc=svrIpv4Addr
                    if "MACAddress" in svr:
                        svrMac = svr["MACAddress"]

                if svrId is None or svrNetloc is None:
                    rdr.logMsg("ERROR",
                    "........error getting server Id and netloc for rackServersDiscoveryDict")
                    rdr.logMsg("ERROR","............skipping server and continuing...")
                    continue  # next server 

                # create a Chassis Entry for the rack server
                chasId, svrChasEntry = self.rfaResAdds.addRfaRackServerChassis(svrId, svrNetloc, svrMac)
                if chasId is not None:
                    self.chassisDict[chasId] = svrChasEntry 

                # create a Systems Entry for the rack server
                sysId, svrSystemEntry = self.rfaResAdds.addRfaRackServerSystem(svrId, svrNetloc, svrMac)
                if sysId is not None:
                    self.systemsDict[sysId] = svrSystemEntry 

                # create a Manager Entry for the rack server's BMC
                mgrId, svrManagerEntry = self.rfaResAdds.addRfaRackServerManager(svrId, svrNetloc, svrMac)
                if mgrId is not None:
                    self.managersDict[mgrId] = svrManagerEntry 
        else:
            # else from if rackServersDiscoveryDict is not None and "RackServers" in rackServersDiscoveryDict:
            rdr.logMsg("CRITICAL",".......no \"RackServers\" array in rackServersDiscoveryDict. fatal")
            return(-9)
        
        # PHASE-1g: update Rack-Level Chassis Contains list to include all of the chassis in the rack
        rdr.logMsg("INFO","....discovery: running phase-1g.  updating Rack-level Chassis Contains list")
        self.rfaResAdds.updateRfaRackChassisContainsList( self.chassisDict ) 

        # PHASE-1h: update Aggregation Manager "Manager For Chassis" list to include all of the chassis it manages
        rdr.logMsg("INFO","....discovery: running phase-1h.  updating Aggregation Manager  \"ManagerForChassis\" list")
        self.rfaResAdds.updateRfaAggrMgrManagersForChassisList( self.chassisDict, self.managersDict ) 

        # PHASE-1i: update Aggregation Manager "Manager For Servers" list to include all of the servers it manages
        rdr.logMsg("INFO","....discovery: running phase-1i.  updating Aggregation Manager \"ManagerForServers\" list")
        self.rfaResAdds.updateRfaAggrMgrManagersForServersList( self.systemsDict, self.managersDict ) 

        # PHASE-1j: sequentially communicate w/ each server BMC and save URIs to chas, sys, and mgr resources
        rdr.logMsg("INFO","....discovery: running phase-1j.  getting detail server info from Server BMCs")
        for mgrId in self.managersDict:
            if "IsRackServer" not in self.managersDict[mgrId]:
                continue
            if self.managersDict[mgrId]["IsRackServer"] is not True:
                continue

            rdr.logMsg("INFO","....... adding server Id:{}".format(mgrId))
            # create a transport to the manager
            if "Netloc" not in self.managersDict[mgrId]:
                rdr.logMsg("ERROR","..........Error-no netloc in managersDict  ")
                continue

            netloc=self.managersDict[mgrId]["Netloc"]
            rdr.logMsg("INFO","...........adding server Id:{}, netloc:{}".format(mgrId,netloc))
            rft = BmcRedfishTransport(rhost=netloc, isSimulator=isSimulator, debug=self.debug, 
                                      credentialsPath=self.rdr.bmcCredentialsPath)
            waitTimeSave=rft.waitTime

            # Defensive: make sure this Id exists also for Chassis and Managers
            if mgrId not in self.chassisDict or mgrId not in self.systemsDict:
                rdr.logMsg("ERROR","..........the Id {} is not valid in chassisDict or systemsDict".format(mgrId))
                continue

            # read the service root
            rft.waitTime=2
            rc,r,j,svcRoot = rft.rfSendRecvRequest("GET", "/redfish/v1")
            rft.waitTime=waitTimeSave
            if rc is not 0:
                rdr.logMsg("ERROR","..........error getting service root for id: {}. rc: {}".format(mgrId,rc))
            else:
                rootUri=r.url
                # get server Managers Collection and parse to get URI
                if "Managers" in svcRoot and "@odata.id" in svcRoot["Managers"]:
                    mgrCollUri = svcRoot["Managers"]["@odata.id"]    # url to collection of Managers
                    rc,r,j,d = rft.rfSendRecvRequest( "GET", mgrCollUri ) 
                    if rc is not 0:
                        rdr.logMsg("ERROR","............ GET Managers Collection failed for uri {}".format(mgrCollUri))
                    else:
                        # extract url to the manager and save it
                        if ("Members" in d) and (len(d["Members"]) == 1) and ("@odata.id" in d["Members"][0]):
                            mgrUrl = d["Members"][0]["@odata.id"]
                            self.managersDict[mgrId]["MgrUrl"] = mgrUrl
                            self.managersDict[mgrId]["BaseUrl"]= rootUri
                            rdr.logMsg("INFO","............ added manager: {}, Url: {}".format(mgrId,mgrUrl))
                        else:
                            rdr.logMsg("ERROR","............ no Manager Member found in Managers Collection for {}".format(mgrId))
                else:
                    rdr.logMsg("ERROR","............ no Managers property in service root for svr Id {}".format(mgrId))

                # get server Chassis Collection and parse to get URI
                if "Chassis" in svcRoot and "@odata.id" in svcRoot["Chassis"]:
                    chasId = mgrId
                    chasCollUri = svcRoot["Chassis"]["@odata.id"]    # url to collection of chassis
                    rc,r,j,d = rft.rfSendRecvRequest( "GET", chasCollUri ) 
                    if rc is not 0:
                        rdr.logMsg("ERROR","............ GET Chassis Collection failed for uri {}".format(chasCollUrl))
                    else:
                        # extract url to the chassis and save it
                        if ("Members" in d) and (len(d["Members"]) == 1) and ("@odata.id" in d["Members"][0]):
                            chasUrl = d["Members"][0]["@odata.id"]
                            self.chassisDict[chasId]["ChasUrl"] = chasUrl
                            self.chassisDict[chasId]["BaseUrl"]= rootUri
                            rdr.logMsg("INFO","............ added chassis: {}, Url: {}".format(chasId,chasUrl))
                        else:
                            rdr.logMsg("ERROR","............ no Chassis Member found in Chassis Collection for {}".format(chasId))
                else:
                    rdr.logMsg("ERROR","............ no Chassis property in service root for svr Id {}".format(chasId))

                # get server Systems Collection and parse to get URI
                if "Systems" in svcRoot and "@odata.id" in svcRoot["Systems"]:
                    sysId = mgrId
                    sysCollUri = svcRoot["Systems"]["@odata.id"]     # url to collection of Systems
                    rc,r,j,d = rft.rfSendRecvRequest( "GET", sysCollUri ) 
                    if rc is not 0:
                        rdr.logMsg("ERROR","............ GET Systems Collection failed for uri {}".format(sysCollUrl))
                    else:
                        # extract url to the system and save it
                        if ("Members" in d) and (len(d["Members"]) == 1) and ("@odata.id" in d["Members"][0]):
                            sysUrl = d["Members"][0]["@odata.id"]
                            self.systemsDict[sysId]["SysUrl"] = sysUrl
                            self.systemsDict[sysId]["BaseUrl"]= rootUri
                            rdr.logMsg("INFO","............ added System: {}, Url: {}".format(sysId,sysUrl))
                        else:
                            rdr.logMsg("ERROR","............ no System Member found in Systems Collection for {}".format(sysId))
                else:
                    rdr.logMsg("ERROR","............ no Systems property in service root for svr Id {}".format(mgrId))




        #PHASE-1k:  
        rdr.logMsg("INFO","....discovery: running phase-1k.   moving resources to the front-end cache databases")
        # now set the front-end databases to what we have discovered here in the backend
        # but note that at this point we are not saving these to the HDD cache
        # initialize the chassis databases

        #   --point the front-end chassis databases at the backend dicts we just generated
        rdr.logMsg("INFO","............discovery: setting chassis databases")
        rdr.root.chassis.chassisDb=self.chassisDict
        rdr.root.chassis.fansDb=self.fansDict
        rdr.root.chassis.tempSensorsDb=self.temperatureSensorsDict
        rdr.root.chassis.powerSuppliesDb=self.powerSuppliesDict
        rdr.root.chassis.voltageSensorsDb=self.voltageSensorsDict
        rdr.root.chassis.powerControlDb=self.powerControlDict

        #   --point the front-end managers databases at the backend dicts we just generated
        rdr.logMsg("INFO","............discovery: setting managers database")
        rdr.root.managers.managersDb=self.managersDict

        #   --point the front-end systems databases at the backend dicts we just generated
        rdr.logMsg("INFO","............discovery: setting systems database")
        rdr.root.systems.systemsDb=self.systemsDict

        #   --create empty Processors, EthernetInterfaces, Memory, and SimpleStorage DBs
        rdr.logMsg("INFO","............discovery: creating empty Proc, Mem, Sto, Eth DBs")
        rdr.root.systems.processorsDb=dict()
        rdr.root.systems.simpleStorageDb=dict()
        rdr.root.systems.ethernetInterfaceDb=dict()
        rdr.root.systems.memoryDb=dict()

        #PHASE-l:  
        rdr.logMsg("INFO","....discovery: running phase-l..   initialize volatile Dicts")

        #   --initialize the Chassis volatileDicts
        rdr.logMsg("INFO","............discovery: initializing Chassis VolatileDicts")
        rdr.root.chassis.initializeChassisVolatileDict(rdr)

        #   --initialize the Managers volatileDicts
        rdr.logMsg("INFO","............discovery: initializing Managers VolatileDicts")
        rdr.root.managers.initializeManagersVolatileDict(rdr)

        #   --initialize the Systems volatileDict
        rdr.logMsg("INFO","........system discovery: initializing Systems VolatileDict")
        rdr.root.systems.initializeSystemsVolatileDict(rdr)

        #PHASE-1m:  
        rdr.logMsg("INFO","....discovery: Phase1 complete")
        return(0)


    # Phase-2 discovery -- runs after Phase-1 discovery if  no errors
    #   Generally this is used to startup hw-monitors on separate threads
    #   For initial Aggregator integration, nothing to do here
    def discoverResourcesPhase2(self, rdr):
        # nothing to do in phasae2
        return(0)


    # --------------------------------------------------
    # --------------------------------------------------
    # --------------------------------------------------
    # --------------------------------------------------
    # --------------------------------------------------
    # --------------------------------------------------

