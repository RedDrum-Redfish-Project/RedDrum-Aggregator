
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
        #PHASE-0a: get some configs from appregatorConfig.py
        rdr.logMsg("INFO","....discovery: running phase-0. Getting Aggregator config from aggregatorConfig.py")
        rdr.logMsg("INFO","....discovery: running phase-0a. Getting isRackSim from aggregatorConfig.py")
        isSimulator=self.rfaCfg.isRackSim
        rdr.backend.isSimulator=isSimulator
        if isSimulator is not True and isSimulator is not False:
            rdr.logMsg("ERROR","....discovery: phase-0. invalid aggregator.Config parameter: isRackSim -- not True or False  ")
            rdr.logMsg("CRITICAL","...... aborting discovery and startup")
            return(11)

        #PHASE-0b: get pduReseatScript
        rdr.logMsg("INFO","....discovery: running phase-0b. Getting pduReseatScript from aggregatorConfig.py")
        rdr.backend.backendPduReseatWrapperFilePath=os.path.join( self.rdr.backend.backendDiscoveryFilePaths, "pduReseatWrapper.sh" )
        rdr.backend.backendPduScriptsDirPath=os.path.join( self.rdr.backend.backendDiscoveryFilePaths, "PDU_SCRIPTS" )
        # verify that App is valid
        pduReseatScriptApp=self.rfaCfg.pduReseatScriptApp
        if pduReseatScriptApp is None or pduReseatScriptApp=="":
            rdr.backend.backendPduReseatScriptApp="bash"
        else:
            rdr.backend.backendPduReseatScriptApp=pduReseatScriptApp
        # verify that the ReseatScrip exists 
        pduReseatScript=self.rfaCfg.pduReseatScript
        rdr.backend.backendPduReseatScriptPath=os.path.join( self.rdr.backend.backendDiscoveryFilePaths, "PDU_SCRIPTS", pduReseatScript )
        if not os.path.isfile(rdr.backend.backendPduReseatScriptPath):
            rdr.logMsg("ERROR","....discovery: phase-0b. Cant find pduReseatScript: {}".format(rdr.backend.backendPduReseatScriptPath))
            rdr.logMsg("CRITICAL","...... aborting discovery and startup")
            return(12)
        rdr.logMsg("INFO",
                "........using pduReseat app: {} and script: {}".format(rdr.backend.backendPduReseatScriptApp, 
                             rdr.backend.backendPduReseatScriptPath))

        #PHASE-0c: get credentialsIdFile
        rdr.logMsg("INFO","....discovery: running phase-0c. Getting bmcCredentialsFile from aggregatorConfig.py")
        bmcCredentialsFile=self.rfaCfg.bmcCredentialsFile
        bmcCredentialsFilePath=os.path.join( self.rdr.backend.backendDiscoveryFilePaths, "CREDENTIALS", bmcCredentialsFile)
        if not os.path.isfile(bmcCredentialsFilePath):
            rdr.logMsg("ERROR","....discovery: phase-0c. Cant find bmcCredentialsFile: {}".format(bmcCredentialsFile))
            rdr.logMsg("CRITICAL","...... aborting discovery and startup")
            return(13)
        else:
            self.rdr.backend.credentialsDb = json.loads( open( bmcCredentialsFilePath, "r").read() )
        rdr.logMsg("INFO",
                "........using bmcCredentials json file: {}".format(bmcCredentialsFile))

        #PHASE-0d: get rackservers discovery file
        rdr.logMsg("INFO","....discovery: running phase-0d. Getting rackServers Discovery File from aggregatorConfig.py")
        rdr.logMsg("INFO",
                "........using discovery json file: {}".format(self.rfaCfg.discoverRackServersFrom))
        discoveryFile=self.rfaCfg.discoverRackServersFrom
        rackServersFilePath=os.path.join(self.rdr.backend.backendDiscoveryFilePaths, "DISCOVERY", discoveryFile)
        if not os.path.isfile(rackServersFilePath):
            rdr.logMsg("ERROR","....discovery: phase-0d. Cant find server discovery file: {}".format(discoveryFile))
            rdr.logMsg("CRITICAL","...... aborting discovery and startup")
            return(14)
        else:
            rackServersDiscoveryDict = json.loads( open( rackServersFilePath, "r").read() )


        #PHASE-1:  discover the rack level Resources
        rdr.logMsg("INFO","....discovery: running phase-1.  adding Rack-Level Resources")

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


        #PHASE-1e:  resync rackserver discovery file 
        rdr.logMsg("INFO","....discovery: running phase-1e.  updating rack server discovery")
        # add update phase if required later


        #PHASE-1f:  add rack servers to Systems, Chassis, and Managers DBs
        rdr.logMsg("INFO","....discovery: running phase-1f.  getting LLDP database of attached servers")
        if rackServersDiscoveryDict is not None and "RackServers" in rackServersDiscoveryDict:
            requiredDiscoveryProps = ["Id","IPv4Address","PduSocketId", "CredentialsId" ]
            for svr in rackServersDiscoveryDict["RackServers"]:
                svrId=None
                svrNetloc=None
                svrPduSockId=None
                svrCredsId=None

                badEntry=False
                for prop in requiredDiscoveryProps:
                    if prop not in svr:
                        badEntry=True
                        break
                if badEntry is True:
                    rdr.logMsg("ERROR",
                    "........error getting discovery properties (svrId, netloc, pduSocket, CredentialsId from rackServersDiscoveryDict")
                    rdr.logMsg("ERROR","............skipping server and continuing...")
                    continue  # next server 

                # if here, we know that all of the required properties are in the entry
                # extract the Id and create a netloc for each server
                svrId = svr["Id"]
                svrNetloc = svr["IPv4Address"]
                svrPduSockId = svr["PduSocketId"]
                svrCredsId = svr["CredentialsId"]

                # verify that the credentialsId is valid
                if svrCredsId not in self.rdr.backend.credentialsDb:
                    rdr.logMsg("ERROR",
                    "........The credentiasId in the discovery file is not a valid credentialsId in the credentials file")
                    rdr.logMsg("ERROR","............skipping server and continuing...")
                    continue  # next server 

                # create a Chassis Entry for the rack server
                chasId, svrChasEntry = self.rfaResAdds.addRfaRackServerChassis(svrId, svrNetloc, svrPduSockId, svrCredsId)
                if chasId is not None:
                    self.chassisDict[chasId] = svrChasEntry 
                    if "BaseNavigationProperties" in svrChasEntry:
                        chasLinks = svrChasEntry["BaseNavigationProperties"]
                        if "Thermal" in chasLinks:
                            self.temperatureSensorsDict[chasId]={}
                            self.fansDict[chasId]={}
                        if "Power" in chasLinks:
                            self.powerSuppliesDict[chasId]={}
                            self.voltageSensorsDict[chasId]={}
                            self.powerControlDict[chasId]={}

                # create a Systems Entry for the rack server
                sysId, svrSystemEntry = self.rfaResAdds.addRfaRackServerSystem(svrId, svrNetloc, svrCredsId)
                if sysId is not None:
                    self.systemsDict[sysId] = svrSystemEntry 

                # create a Manager Entry for the rack server's BMC
                mgrId, svrManagerEntry = self.rfaResAdds.addRfaRackServerManager(svrId, svrNetloc, svrCredsId)
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
            if "IsRackServerManager" not in self.managersDict[mgrId]:
                continue
            if self.managersDict[mgrId]["IsRackServerManager"] is not True:
                continue

            rdr.logMsg("INFO","....... adding server Id:{}".format(mgrId))
            # create a transport to the manager
            if "Netloc" not in self.managersDict[mgrId]:
                rdr.logMsg("ERROR","..........Error-no netloc in managersDict  ")
                continue
            if "CredentialsId" not in self.managersDict[mgrId]:
                rdr.logMsg("ERROR","..........Error-no credentialsId in managersDict  ")
                continue

            netloc=self.managersDict[mgrId]["Netloc"]
            credentialsId=self.managersDict[mgrId]["CredentialsId"]
            credentialsInfo = self.rdr.backend.credentialsDb[credentialsId] # we earlier verified that all credIds are valid

            rdr.logMsg("INFO","...........adding server Id:{}, netloc:{}".format(mgrId,netloc))
            rft = BmcRedfishTransport(rhost=netloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug, 
                                      credentialsInfo=credentialsInfo)
            waitTimeSave=rft.waitTime

            # Defensive: make sure this Id exists also for Chassis and Managers
            if mgrId not in self.chassisDict or mgrId not in self.systemsDict:
                rdr.logMsg("ERROR","..........the Id {} is not valid in chassisDict or systemsDict".format(mgrId))
                continue

            # read the service root
            rft.waitTime=5
            rc,r,j,svcRoot = rft.rfSendRecvRequest("GET", "/redfish/v1")
            rft.waitTime=waitTimeSave
            if rc==6:
                rdr.logMsg("ERROR","..........error getting service root for id: {}. rc: {} RETRY".format(mgrId,rc))
                rc,r,j,svcRoot = rft.rfSendRecvRequest("GET", "/redfish/v1")
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
                        # xg9999 may want to handle multiple managers
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
                        rdr.logMsg("ERROR","............ GET Chassis Collection failed for uri {}".format(chasCollUri))
                    else:
                        # extract url to the chassis and save it
                        if ("Members" in d):
                            if (len(d["Members"]) == 1) and ("@odata.id" in d["Members"][0]):
                                chasUrl = d["Members"][0]["@odata.id"]
                                self.chassisDict[chasId]["ChasUrl"] = chasUrl
                                self.chassisDict[chasId]["BaseUrl"]= rootUri
                                rdr.logMsg("INFO","............ added chassis: {}, Url: {}".format(chasId,chasUrl))
                            else: 
                                # get manager entry to find the chassis it manages
                                # mgrUrl is still valid
                                rdr.logMsg("INFO","............ getting mgr entry to find chassisId..")
                                rc,r,j,dmgr = rft.rfSendRecvRequest( "GET", mgrUrl ) 
                                print("EEEEEEEEEEEEEEEEEEEEEEEEE")
                                if rc is not 0:
                                    rdr.logMsg("ERROR","............ GET Manager failed for uri {}".format(mgrUrl))
                                else:
                                    if "Links" in dmgr and "ManagerForChassis" in dmgr["Links"]:
                                        print("EEEEEEEEEEEEEEEEEEEEEEEEE")
                                        mgrForChas=dmgr["Links"]["ManagerForChassis"]
                                        if len(mgrForChas)==1 and "@odata.id" in mgrForChas[0]:
                                            print("EEEEEEEEEEEEEEEEEEEEEEEEE")
                                            chasUrl = mgrForChas[0]["@odata.id"]
                                            self.chassisDict[chasId]["ChasUrl"] = chasUrl
                                            self.chassisDict[chasId]["BaseUrl"]= rootUri
                                            rdr.logMsg("INFO","............ added chassis: {}, Url: {}".format(chasId,chasUrl))
                                        else:
                                            rdr.logMsg("ERROR","A............ no Chassis Member found for {}".format(chasId))
                                    else:
                                        print("BBBBBBBBBBBBBBBBBBBBBBB")
                                        if "Model" in dmgr and dmgr["Model"]=="OpenBmc":
                                            print("Assuming chasId=R1000_Chassis EEEEEEEEEEEEEEEEEEEEEEEEE")
                                            chasUrl = "/redfish/v1/Chassis/R1000_Chassis"
                                            self.chassisDict[chasId]["ChasUrl"] = chasUrl
                                            self.chassisDict[chasId]["BaseUrl"]= rootUri
                                            rdr.logMsg("INFO","............ added chassis: {}, Url: {}".format(chasId,chasUrl))
                                        else:
                                            rdr.logMsg("ERROR","B............ no Chassis Member found for {}".format(chasId))
                else:
                    rdr.logMsg("ERROR","............ no Chassis property in service root for svr Id {}".format(chasId))

                # get server Systems Collection and parse to get URI
                if "Systems" in svcRoot and "@odata.id" in svcRoot["Systems"]:
                    sysId = mgrId
                    sysCollUri = svcRoot["Systems"]["@odata.id"]     # url to collection of Systems
                    rc,r,j,d = rft.rfSendRecvRequest( "GET", sysCollUri ) 
                    if rc is not 0:
                        rdr.logMsg("ERROR","............ GET Systems Collection failed for uri {}".format(sysCollUri))
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

