
# Copyright Notice:
#    Copyright 2018 Dell, Inc. All rights reserved.
#    License: BSD License.  For full license text see link: https://github.com/RedDrum-Redfish-Project/RedDrum-Aggregator/LICENSE.txt

import os
import json
#xg99 from .aggregatorResourceAdds import RfaResourceAdds
#xg99 from .lldpParser import RfaLldpApis
from .redfishTransports import BmcRedfishTransport
from .aggregatorConfig import RfaConfig


class RdStartupResourceDiscovery():
    def __init__(self,rdr):
        #self.rfaResAdds=RfaResourceAdds(rdr)
        #self.rfaLldp=RfaLldpApis()
        self.rdr=rdr
        self.rfaCfg=RfaConfig()  # aggregatorConfig data

        self.debug=False
        #self.debug=True

        # initialize discovery dicts
        self.aggrSvcRootDb=rdr.backend.aggrSvcRootDb

        self.chassisDict={} #xg99
        self.managersDict={} #xg99
        self.systemsDict={} #xg99
        self.fansDict={} #xg99
        self.temperatureSensorsDict={} #xg99
        self.powerSuppliesDict={} #xg99
        self.voltageSensorsDict={} #xg99
        self.powerControlDict={} #xg99
        self.mgrNetworkProtocolDict={} #xg99
        self.mgrEthernetDict={} #xg99

    # --------------------------------------------------

    def discoverResourcesPhase1(self, rdr):
        #PHASE-0a: get some configs from appregatorConfig.py
        rdr.logMsg("INFO","..discovery: running phase-0. Getting Aggregator config from aggregatorConfig.py")
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
        rdr.logMsg("INFO","....discovery: running phase-0d. Getting RackServers Discovery File from aggregatorConfig.py")
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
        rdr.logMsg("INFO","..discovery: running phase-1.  adding Local Resources")

        #PHASE-1a:  discover the rack level enclosure
        if self.rfaCfg.includeLocalRackEnclosureChassis is True:
            rdr.logMsg("INFO","....discovery: running phase-1a.  adding Rack-Level Chassis Enclosure Resource")
            rc = rdr.backend.chassis.rack.addRfaRackEnclosureChassisResource()
            if rc is not 0:
                rdr.logMsg("ERROR","........Error adding Rack Level Enclosure Chassis")

        #PHASE-1b:  discover the rack level Mgt Switch chassis
        if self.rfaCfg.includeLocalMgtSwitchChassis is True:
            rdr.logMsg("INFO","....discovery: running phase-1b.  adding Management Switch Chassis resource")
            rc = rdr.backend.chassis.mgtSwitch.addRfaMgtSwitchChassisResource()
            if rc is not 0:
                rdr.logMsg("ERROR","........Error adding Management Swtich Chassis")


        #PHASE-1c:  if aggregator is in a separate "Host" chassis from switch, then add it
        if self.rfaCfg.includeLocalAggregatorHostChassis is True:
            if self.rfaCfg.redfishAggregatorIsInsideSwitch is not True or self.rfaCfg.includeLocalMgtSwitchChassis is not True:
                rdr.logMsg("INFO","....discovery: running phase-1c.  adding Redfish Aggregator Host Chassis ")
                rc = rdr.backend.chassis.aggrHost.addRfaAggregatorHostChassisResource()
                if rc is not 0:
                    rdr.logMsg("ERROR","........Error adding Aggregator Host Chassis")
            else:
                rdr.logMsg("INFO","....discovery: running phase-1c.  Redfish Aggregator is inside Switch--no Host chassis to add")

        #PHASE-1d:  discover the aggregator Manager
        rdr.logMsg("INFO","....discovery: running phase-1d.  adding Redfish Aggregator Manager resource")
        rc = rdr.backend.managers.aggrMgr.addRfaAggregatorManagerResource()
        if rc is not 0:
            rdr.logMsg("ERROR","........Error adding Aggregator Manager")


        #PHASE-1e:  walk discovery Db and add RootService entry for this server to aggrSvcRootDb
        rdr.logMsg("INFO","....discovery: running phase-1e.  discovering RackServers from discovery file")
        rdr.logMsg("INFO","........from discovery file: {}".format(self.rfaCfg.discoverRackServersFrom))
        if rackServersDiscoveryDict is not None and "Comment" in rackServersDiscoveryDict:
            rdr.logMsg("INFO","..........-- {}".format(rackServersDiscoveryDict["Comment"]))
        if rackServersDiscoveryDict is not None and "RackServers" in rackServersDiscoveryDict:
            requiredDiscoveryProps = ["Id","IPv4Address","PduSocketId", "CredentialsId" ]
            for svc in rackServersDiscoveryDict["RackServers"]:
                badEntry=False
                for prop in requiredDiscoveryProps:
                    if prop not in svc:
                        badEntry=True
                        break
                if badEntry is True:
                    rdr.logMsg("ERROR",
                    "........error getting discovery properties (svcId, netloc, pduSocket, CredentialsId from rackServersDiscoveryDict")
                    rdr.logMsg("ERROR","............skipping server and continuing...")
                    continue  # next server 

                # if here, we know that all of the required properties are in the entry
                # extract the Id and create a netloc for each server
                svcId = svc["Id"]
                svcNetloc = svc["IPv4Address"]      # the bmc netloc
                svcPduSockId = svc["PduSocketId"]
                svcCredsId = svc["CredentialsId"]

                # verify that the credentialsId is valid
                if svcCredsId not in self.rdr.backend.credentialsDb:
                    rdr.logMsg("ERROR",
                    "........The credentiasId in the discovery file is not a valid credentialsId in the credentials file")
                    rdr.logMsg("ERROR","............skipping server and continuing...")
                    continue  # next server 

                # create a RootSvc Entry for the rack server
                svcRootId, svcRootEntry = self.addRfaRackServerRoot(svcId, svcNetloc, svcCredsId, svcPduSockId)
                if svcRootId is not None:
                    self.aggrSvcRootDb[svcRootId] = svcRootEntry 
        else:
            # else from if rackServersDiscoveryDict is not None and "RackServers" in rackServersDiscoveryDict:
            rdr.logMsg("CRITICAL",".......no \"RackServers\" array in rackServersDiscoveryDict. fatal")
            return(-9)


        # PHASE-1f: sequentially communicate w/ each server BMC service root and add links to Chassis, Managers, and Servers
        rdr.logMsg("INFO","....discovery: running phase-1f.  getting ServiceRoot, Server, and Chassis info from BMCs")
        for svcId in self.aggrSvcRootDb:
            svc=self.aggrSvcRootDb[svcId]
            requiredPropsInSvcRootDb=["SvcId","Netloc","CredentialsId"]
            for prop in requiredPropsInSvcRootDb:
                if prop not in svc:
                    rdr.logMsg("ERROR","..........Error-no {} prop in managersDict  ".format(prop))
                    continue

            #svcId = svc["SvcId"]
            rdr.logMsg("INFO","....... getting ServiceRoot from BMC Id:{}".format(svcId))
            netloc=svc["Netloc"]
            credentialsId=svc["CredentialsId"]
            credentialsInfo = self.rdr.backend.credentialsDb[credentialsId] # we earlier verified that all credIds are valid

            # create a transport to the manager
            rft = BmcRedfishTransport(rhost=netloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug, 
                                      credentialsInfo=credentialsInfo)
            waitTimeSave=rft.waitTime

            # read the service root
            rft.waitTime=5
            rc,r,j,dSvcRoot = rft.rfSendRecvRequest("GET", "/redfish/v1")
            rft.waitTime=waitTimeSave
            if rc==6:
                rdr.logMsg("ERROR","..........error getting service root for id: {}. rc: {} RETRY".format(svcId,rc))
                rc,r,j,dSvcRoot = rft.rfSendRecvRequest("GET", "/redfish/v1")
            if rc is not 0:
                rdr.logMsg("ERROR","..........error getting service root for id: {}. rc: {}".format(svcId,rc))
            else:
                # save the root service uri, response, and redfish transport in the rootServiceDb
                rootUri=r.url
                svc["RootUri"]= rootUri
                svc["RedfishTransport"]=rft
                svc["ServiceRoot"]=dSvcRoot
                svc["ManagersMembers"]=[]
                svc["ChassisMembers"]=[]
                svc["SystemsMembers"]=[]
                svc["TopLevelChassisUrlList"] = [] 

                # get Managers Collection and store
                rdr.logMsg("INFO","..........getting Manager Collection ")
                if "Managers" in dSvcRoot and "@odata.id" in dSvcRoot["Managers"]:
                    mgrCollUri = dSvcRoot["Managers"]["@odata.id"]    # url to collection of Managers
                    rc,r,j,dMgrColl = rft.rfSendRecvRequest( "GET", mgrCollUri ) 
                    if rc is not 0:
                        rdr.logMsg("ERROR","............ GET Managers Collection failed for uri {}".format(mgrCollUri))
                    else:
                        if ("Members" in dMgrColl):
                                svc["ManagersMembers"]=dMgrColl["Members"]
                        else:
                            rdr.logMsg("WARNING","............ no Members list found in Managers Collection for {}".format(svcId))
                else:
                    rdr.logMsg("WARNING","............ no Managers property in service root for {}".format(svcId))

                # get Chassis Collection and store
                rdr.logMsg("INFO","..........getting Chassis Collection ")
                if "Chassis" in dSvcRoot and "@odata.id" in dSvcRoot["Chassis"]:
                    chasCollUri = dSvcRoot["Chassis"]["@odata.id"]    # url to collection of Managers
                    rc,r,j,dChasColl = rft.rfSendRecvRequest( "GET", chasCollUri ) 
                    if rc is not 0:
                        rdr.logMsg("ERROR","............ GET Chassis Collection failed for uri {}".format(chasCollUri))
                    else:
                        if ("Members" in dChasColl):
                                svc["ChassisMembers"]=dChasColl["Members"]
                        else:
                            rdr.logMsg("WARNING","............ no Members list found in Chassis Collection for {}".format(svcId))
                else:
                    rdr.logMsg("WARNING","............ no Chassis property in service root for {}".format(svcId))
                #print("EEEEEEEEEEEEEE: Managers: {}".format(svc["ManagersMembers"]))

                # get Systems Collection and store
                rdr.logMsg("INFO","..........getting Systems Collection ")
                if "Systems" in dSvcRoot and "@odata.id" in dSvcRoot["Systems"]:
                    sysCollUri = dSvcRoot["Systems"]["@odata.id"]    # url to collection of Systems
                    rc,r,j,dSysColl = rft.rfSendRecvRequest( "GET", sysCollUri ) 
                    if rc is not 0:
                        rdr.logMsg("ERROR","............ GET Systems Collection failed for uri {}".format(sysCollUri))
                    else:
                        if ("Members" in dChasColl):
                                svc["SystemsMembers"]=dSysColl["Members"]
                        else:
                            rdr.logMsg("WARNING","............ no Members list found in Systems Collection for {}".format(svcId))
                else:
                    rdr.logMsg("WARNING","............ no Systems property in service root for {}".format(svcId))


        # PHASE-1g: find all of the "Top-Level" chassis under each service root
        #    this info is needed to properly generate the Links between the AggrMgr, AggrChas, and rackServers and chassis
        #    if there is only one chassis in the Chassis Collection for a service, set it as the Top-Level chassis implicitly
        #    else: Get each Chassis entry under that service 
        #          if the entry has a ContainedBy propoerty, do not put it in the listo
        #          if there is no ContainedBy property or the property = None or equal to "", set ContainedBy to None
        #          otherwise store the containtedBy list
        rdr.logMsg("INFO","....discovery: running phase-1g.  checking for Chassis that are \"ContainedBy\"  another chassis")
        for svcId in self.aggrSvcRootDb:
            svc=self.aggrSvcRootDb[svcId]
            #svcId = svc["SvcId"]
            if "ChassisMembers" in svc:
                chassisMembers = svc["ChassisMembers"]
                numOfChassis = len(chassisMembers)
            else:
                rdr.logMsg("ERROR","..........no ChassisMembers in svc ")
                continue   # and leave svc[TopLevelChassisUrlList] an empty list 
            if numOfChassis == 0:
                continue   # and leave svc[TopLevelChassisUrlList] an empty list 
            elif numOfChassis == 1:
                if "@odata.id" in svc["ChassisMembers"][0]:
                    chasUrl = svc["ChassisMembers"][0]["@odata.id"]
                    svc["TopLevelChassisUrlList"].append( chasUrl ) # add the one entry to topLevelChassisUrlList
            else:
                # get each chassis under this root serivce and check if it has a ContainedBy
                for chasMember in svc["ChassisMembers"]:
                    if "@odata.id" in chasMember:
                        chasUrl = chasMember["@odata.id"]
                        rft = svc["RedfishTransport"]
                        rc,r,j,dChas = rft.rfSendRecvRequest("GET", chasUrl)
                        if rc is not 0:
                            rdr.logMsg("ERROR","....error reading chassis entry for url: {}".format(chasUrl))
                            continue
                        if "Links" in dChas: 
                            if "ContainedBy" in dChas["Links"]:
                                chasContainedByVal = dChas["Links"]["ContainedBy"]
                                if chasContainedByVal is not None and chasContainedByVal != "":
                                    continue # dont add this chas member to topLevelChassisUrlList
                        # if here, we know the chassis does not have a ContainedBy link
                        # add it to the topLevelChasUrlList
                        svc["TopLevelChassisUrlList"].append( chasUrl ) # add to topLevelChassisUrlList
                    else:
                        rdr.logMsg("WARNING","....chassisMembers member has no odata.id" )
            # debug: display the topLevelChassis for this service
            #print("EEEEEE: topLvlChassisUriList: {}".format(svc["TopLevelChassisUrlList"]))
        return(0)

    # svcRootId, svcRootEntry = self.addRfaRackServerRoot(svcId, svcNetloc, svcCredsId, svcPduSockId)
    def addRfaRackServerRoot(self, svcId, svcNetloc, svcCredsId, svcPduSockId):
        resp=dict()
        resp["SvcId"]=svcId
        resp["Netloc"]=svcNetloc
        resp["CredentialsId"]=svcCredsId
        resp["PduSocketId"]=svcPduSockId
        return(svcId,resp)


    # Phase-2 discovery -- runs after Phase-1 discovery if  no errors
    #   Generally this is used to startup hw-monitors on separate threads
    #   For initial Aggregator integration, nothing to do here
    def discoverResourcesPhase2(self, rdr):
        # nothing to do in phasae2
        return(0)


    # --------------------------------------------------
    # Rules for linking between Systems, Chassis, and Managers with 1) AggrMgr and 2) AggrChassis
    # During Discovery:
    # for <svc> in rootSvcDb:
    #   for chasMember in <svc>[ChassisMembers] # the members array of chassis under this service
    #      if   len of the chassisMembers array is 0:  
    #         then set topLevelChassisList=[] # an empty list
    #      elif len of the chassisMembers array is 1:  
    #         then add the single chas url (chasMember[@odata.id]) to the topLevelChassisList
    #      else # case where there are several chassis.   
    #         # add all chassis that dont have a "ContainedBy" link to the list
    #         chasMemberUrl = chasMember[@odata.id]
    #         chasResponse  = GET chasMemberUrl
    #         if "ContainedBy" in chasResponse[Links] 
    #            chasContainedByVal = chasResponse[Links]["ContainedBy"] 
    #            if chasContainedByVal is not None and chasContainedByVal is not "":
    #               continue # dont put this chassis in the topLevelChassisList
    #         otherwise cases where there is a valid ContainedBy value, add the chas to topLevelChassisList
    #         add chasMemberUrl to the topLevelChassisList

    # DONE
    # if GET <chas>:
    #   if <chas> id is in topLevelChassisList  # that is: it does not have a ContainedBy link:
    #    x) add "ConatinedBy": <AggregationChassis> to the <chas>'s Links
    #    x) add <AggregationManager> to <chas>'s "ManagedBy" list

    # DONE
    # if GET <Rack Level Enclosure Chassis>:
    #    for each svc in rootSvcDb:
    #      for each id in svc[topLevelChassisList]# that is: chassis that do not have a ContainedBy link:
    #        x) add <chas> to the <RackEnclosureChassis>'s "Contains" list
    #    no "ComputerSystems" list

    # DONE
    # if GET <AggregationManager>:
    #    for each svc in rootSvcDb:
    #      for each id in svc[topLevelChassisList]# that is: chassis that do not have a ContainedBy link:
    #        x) add <chas> to the <AggregationManager>'s "ManagerForChassis" list
    #    for each svc in rootSvcDb:
    #      for each <sys> in svc[SystemsMembers] 
    #        x) add <sys> to the <AggregationManager>'s "ManagerForServers" list

    # DONE
    # if GET <system>:
    #    x) add <AggregationManager> to <systems>'s "ManagedBy" list
    #    x) the systems's Chassis list will not contain AggregationChassis

    # if GET <mgr>:
    #    x) nothing changes with AggMgr
    
    # --------------------------------------------------
    # --------------------------------------------------
    # --------------------------------------------------
    # --------------------------------------------------
    # --------------------------------------------------

