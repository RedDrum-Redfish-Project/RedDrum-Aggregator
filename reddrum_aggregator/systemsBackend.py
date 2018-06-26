
# Copyright Notice:
#    Copyright 2018 Dell, Inc. All rights reserved.
#    License: BSD License.  For full license text see link: https://github.com/RedDrum-Redfish-Project/RedDrum-OpenBMC/LICENSE.txt

import datetime
import json

from .redfishTransports import  BmcRedfishTransport
from .ipmiTransports import BmcIpmiTransport

# systemBackend resources for RedDrum OpenBMC implementation
#
class  RdSystemsBackend():
    # class for backend systems resource APIs
    def __init__(self,rdr):
        self.version=1
        self.rdr=rdr
        self.nonVolatileDataChanged=False
        self.debug=False


    # update resourceDB and volatileDict properties
    def updateResourceDbs(self,systemid, updateStaticProps=False, updateNonVols=True ):
        self.rdr.logMsg("DEBUG","--------BACKEND updateResourceDBs. updateStaticProps={}".format(updateStaticProps))
        rc=0
        resDb=self.rdr.root.systems.systemsDb[systemid]
        resVolDb=self.rdr.root.systems.systemsVolatileDict[systemid]
        staticProperties=self.rdr.root.systems.staticProperties
        nonVolatileProperties=self.rdr.root.systems.nonVolatileProperties

        updatedResourceDb=False

        # check if front-end database was updated within the last sec
        # if so, don't try to update from HWMonitor Redis Db
        curTime=datetime.datetime.utcnow()
        lastDbUpdateTime=None
        if "UpdateTime" in resVolDb:
            # note lastDbUpdateTime in string form: "2017-06-13 16:12:02.729333"
            lastDbUpdateTime=datetime.datetime.strptime(str(resVolDb["UpdateTime"]), "%Y-%m-%d %H:%M:%S.%f")
            # if less than a sec since we update the volatile dict, just return and use current database
            #if ( (curTime - lastDbUpdateTime) < datetime.timedelta(seconds=1)):
            if ( (curTime - lastDbUpdateTime) < datetime.timedelta(seconds=1)):
                self.rdr.logMsg("DEBUG","----------Backend: time < min DbUpdateTime.  Returning w/o updating DBs")
                return(0,False)
        # save front-end database update timestamp
        resVolDb["UpdateTime"] = curTime

        # extract the netloc and system entry URL from the systemsDb saved during discovery
        netloc = resDb["Netloc"]
        sysUrl = resDb["SysUrl"]

        # open Redfish transport to this bmc
        rft = BmcRedfishTransport(rhost=netloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug,
                                      credentialsPath=self.rdr.bmcCredentialsPath)
        # send request to the rackserver  BMC
        rc,r,j,dsys = rft.rfSendRecvRequest("GET", sysUrl )
        if rc is not 0:
            self.rdr.logMsg("ERROR","..........error getting system entry from rackserver BMC: {}. rc: {}".format(systemid,rc))
            return(19,False) # note: returning non-zero rc, will cause a 500 error from the frontend.

        # for aggregator, force update on static props all the time
        updateStaticProps = True

        # update Static data if flag is set to do so.   
        # this is generally done once to pickup static data discovered by backend
        if updateStaticProps is True:
            for prop in staticProperties:
                if (prop in resDb) and (prop in dsys):
                    if resDb[prop] != dsys[prop]:
                        resDb[prop]=dsys[prop]
                        updatedResourceDb=True

        # update Volatile Properties
        if "Volatile" in resDb:
             for prop in resDb["Volatile"]:
                if prop in dsys:
                    resVolDb[prop]=dsys[prop]

        # then update the volatile boot properties
        if ("BootSourceAllowableValues" in resDb) and ("BootSourceVolatileProperties" in resDb) and ("Boot" in dsys):
            for prop in resDb["BootSourceVolatileProperties"]:
                if prop in dsys["Boot"]:
                    resVolDb[prop]=dsys["Boot"][prop]

        # update the volatile status properties
        if ("Status" in resDb) and ("Status" in dsys):
            for prop in resDb["Status"]:
                if prop in dsys["Status"]:
                    if "Status" not in resVolDb:
                        resVolDb["Status"]={}
                    resVolDb["Status"][prop]=dsys["Status"][prop]

        # update NonVolatile Properties
        if updateNonVols is True:
            for prop in nonVolatileProperties:
                if (prop in resDb) and (prop in dsys):
                    if resDb[prop] != dsys[prop]:
                        resDb[prop]=dsys[prop]
                        updatedResourceDb=True

        # update NonVolatile MemorySummary Properties
        if (updateNonVols is True) and ("MemorySummary" in resDb) and ("MemorySummary" in dsys):
            for prop in resDb["MemorySummary"]:
                if prop in dsys["MemorySummary"]:
                    if prop == "Status":
                        for subProp in resDb["MemorySummary"]["Status"]:
                            if subProp in dsys["MemorySummary"]["Status"]:
                                if resDb["MemorySummary"]["Status"][subProp] != dsys["MemorySummary"]["Status"][subProp]:
                                    resDb["MemorySummary"]["Status"][subProp]=dsys["MemorySummary"]["Status"][subProp]
                                    #print (" The property is " + str(dsys["MemorySummary"]["Status"][prop]))
                                    updatedResourceDb=True
                    else: # properties other than Status
                        if resDb["MemorySummary"][prop] != dsys["MemorySummary"][prop]:
                            resDb["MemorySummary"][prop]=dsys["MemorySummary"][prop]
                            #print (" The property is " + str(resDb["MemorySummary"][prop]))
                            updatedResourceDb=True

        # update NonVolatile ProcessorSummary Properties
        if (updateNonVols is True) and ("ProcessorSummary" in resDb) and ("ProcessorSummary" in dsys):
            for prop in resDb["ProcessorSummary"]:
                if prop in dsys["ProcessorSummary"]:
                    if prop == "Status":
                        for subProp in resDb["ProcessorSummary"]["Status"]:
                            if subProp in dsys["ProcessorSummary"]["Status"]:
                                if resDb["ProcessorSummary"]["Status"][subProp] != dsys["ProcessorSummary"]["Status"][subProp]:
                                    resDb["ProcessorSummary"]["Status"][subProp]=dsys["ProcessorSummary"]["Status"][subProp]
                                    updatedResourceDb=True
                    else: # properties other than Status
                        if resDb["ProcessorSummary"][prop] != dsys["ProcessorSummary"][prop]:
                            resDb["ProcessorSummary"][prop]=dsys["ProcessorSummary"][prop]
                            updatedResourceDb=True

        # update Actions Reset AllowableValues
        if "ActionsResetAllowableValues" in resDb:
            if "Actions" in dsys and "#ComputerSystem.Reset" in dsys["Actions"]:
                if "ResetType@Redfish.AllowableValues" in dsys["Actions"]["#ComputerSystem.Reset"]:
                    resDb["ActionsResetAllowableValues"]=dsys["Actions"]["#ComputerSystem.Reset"]["ResetType@Redfish.AllowableValues"]
                    updatedResourceDb=True
                if "target" in dsys["Actions"]["#ComputerSystem.Reset"]:
                    resDb["SysResetTargetUrl"]=dsys["Actions"]["#ComputerSystem.Reset"]["target"]
                    updatedResourceDb=True

        rc=0
        return(rc,updatedResourceDb)


    # DO action:   Reset OpenBMC System
    def doSystemReset(self,systemid,resetType):
        self.rdr.logMsg("DEBUG","-------- BACKEND systemReset. resetType={}".format(resetType))
        resDb=self.rdr.root.systems.systemsDb[systemid]

        # extract the netloc and system entry URL from the systemsDb saved during discovery
        netloc = resDb["Netloc"]
        sysUrl = resDb["SysUrl"]

        # open Redfish transport to this bmc
        rft = BmcRedfishTransport(rhost=netloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug,
                                      credentialsPath=self.rdr.bmcCredentialsPath)
        # check if we already have a system reset URI collected
        if "SysResetTargetUrl" in resDb:
            sysResetTargetUrl = resDb["SysResetTargetUrl"]
        else:
            # send request to the rackserver  BMC to read the system resource
            rc,r,j,dsys = rft.rfSendRecvRequest("GET", sysUrl )
            if rc is not 0:
                self.rdr.logMsg("ERROR","..........error getting system entry from rackserver BMC: {}. rc: {}".format(systemid,rc))
                return(19,False) # note: returning non-zero rc, will cause a 500 error from the frontend.
            if "Actions" in dsys and "#ComputerSystem.Reset" in dsys["Actions"]:
                if "target" in dsys["Actions"]["#ComputerSystem.Reset"]:
                    sysResetTargetUrl = dsys["Actions"]["#ComputerSystem.Reset"]["target"]
                    resDb["SysResetTargetUrl"] = sysResetTargetUrl 
                    updatedResourceDb=True
                if "ResetType@Redfish.AllowableValues" in dsys["Actions"]["#ComputerSystem.Reset"]:
                    resDb["ActionsResetAllowableValues"]=dsys["Actions"]["#ComputerSystem.Reset"]["ResetType@Redfish.AllowableValues"]
                    updatedResourceDb=True
                # xg99 todo, support using getActionInfoAllowableValues

        # check if reset type is in allowable values
        allowableValues=resDb["ActionsResetAllowableValues"]
        if resetType not in allowableValues:
            return(400)

        # send POST request to the rackserver  BMC to reset
        self.rdr.logMsg("INFO","-------- BACKEND sending Reset to bmc")
        resetData={"ResetType": resetType }
        reqPostData=json.dumps(resetData)

        rc,r,j,dsys = rft.rfSendRecvRequest("POST", sysResetTargetUrl,reqData=reqPostData )
        if rc is not 0:
            self.rdr.logMsg("ERROR","..........error sending system reset to rackserver BMC: {}. rc: {}".format(systemid,rc))
            return(19,False) # note: returning non-zero rc, will cause a 500 error from the frontend.

        return(rc)




    # DO Patch to System  (IndicatorLED, AssetTag, or boot overrides
    #   the front-end will send an individual call for IndicatorLED and AssetTag or bootProperties
    #   multiple boot properties may be combined in one patch
    def doPatch(self, systemid, patchData):
        # the front-end has already validated that the patchData and systemid is ok
        # so just send the request here

        self.rdr.logMsg("DEBUG","--------BACKEND Patch system data. patchData={}".format(patchData))
        resDb=self.rdr.root.systems.systemsDb[systemid]

        # extract the netloc and system entry URL from the systemsDb saved during discovery
        netloc = resDb["Netloc"]
        sysUrl = resDb["SysUrl"]

        # open Redfish transport to this bmc
        rft = BmcRedfishTransport(rhost=netloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug,
                                      credentialsPath=self.rdr.bmcCredentialsPath)

        # send PATCH request to the rackserver  BMC to reset
        self.rdr.logMsg("INFO","-------- BACKEND sending Patch to bmc")
        reqPatchData=json.dumps(patchData)

        rc,r,j,dsys = rft.rfSendRecvRequest("PATCH", sysUrl,reqData=reqPatchData )
        if rc is not 0:
            self.rdr.logMsg("ERROR","..........error sending system patch to rackserver BMC: {}. rc: {}".format(systemid,rc))
            return(19,False) # note: returning non-zero rc, will cause a 500 error from the frontend.

        return(rc)



    # update ProcessorsDb 
    def updateProcessorsDbFromBackend(self, sysid, procid=None, noCache=False ):
        # if here we know sysid is in systemsDb, BaseNavigationProperties is in systemsDb[sysid] 
        #    and Processors is in systemsDb[sysid]["BaseNavitationProperties"]
        procDb=self.rdr.root.systems.processorsDb
        procInfoCacheTimeout=self.rdr.processorInfoCacheTimeout

        # get time 
        curTime=datetime.datetime.utcnow()
        lastProcDbUpdateTime=None

        # if using processor cache is enabled/selected, check if cache exists
        if (procInfoCacheTimeout > 0) and (noCache is False):
            if( (sysid in procDb) and ("Id" in  procDb[sysid]) and
                ("UpdateTime" in procDb[sysid]) and (procDb[sysid]["UpdateTime"] is not None) ):
                # if we have a sysid entry in procDb with an "Id" resource, then we have a proc cache
                # (the sys monitor or hotplug code will clear the db for this sysid if it is out of date
                #  by removing the entry or setting UpdateTime to None)

                #check if the cache timeout has occured
                # note lastProcDbUpdateTime in string form: "2017-06-13 16:12:02.729333"
                lastProcDbUpdateTime=datetime.datetime.strptime(str(procDb[sysid]["UpdateTime"]), "%Y-%m-%d %H:%M:%S.%f")
                # if currentTime - lastUpdateTime is less than rdr.procInfoCacheTimeout, return. no update required
                #if ( (curTime - lastProcDbUpdateTime) < datetime.timedelta(seconds=1)):
                if ( (curTime - lastProcDbUpdateTime) < datetime.timedelta(seconds=procInfoCacheTimeout)):
                    self.rdr.logMsg("DEBUG","---------BACKEND ProcessorInfo: cache not timed-out. Return w/o updating Db")
                    return(0)

        # if here, we need to update the full processor info database for this systemid
        rc=self.updateProcessorDbFromNode(sysid, procDb, curTime)
        return(rc)

    def updateProcessorDbFromNode(self, sysid, procDb, curTime):
        sysDbEntry = self.rdr.root.systems.systemsDb[sysid]
        sysNetloc = sysDbEntry["Netloc"]
        sysUrl = sysDbEntry["SysUrl"]
        processorsUri=None
        maxCollectionEntries = 8
        processorInfoProperties=["Name","Socket","ProcessorType","Manufacturer","Model","MaxSpeedMHz","TotalCores",
                        "TotalThreads", "ProcessorId" ]
        fixIdracProperties=["ProcessorArchitecture", "InstructionSet" ]

        # open Redfish transport to this bmc
        nodeRft = BmcRedfishTransport(rhost=sysNetloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug,
                                      credentialsPath=self.rdr.bmcCredentialsPath)

        # check if we already have the URI for the processors collection 
        if "ProcessorsUri" in sysDbEntry:
            processorsUri=sysDbEntry["ProcessorsUri"]
        else: 
            # we need to query the systemEntry to get the Processor collection URI
            self.rdr.logMsg("DEBUG","--------BACKEND ProcessorsUri not in database. getting root. sysid={}".format(sysid))
            # send request to the rackserver  BMC
            rc,r,j,dsys = nodeRft.rfSendRecvRequest("GET", sysUrl )
            if rc is not 0:
                self.rdr.logMsg("ERROR","..........error getting service root entry rc: {}".format(rc))
                return(18) # note: returning non-zero rc, will cause a 500 error from the frontend.
            if "Processors" in dsys and "@odata.id" in dsys["Processors"]:
                processorsUri=dsys["Processors"]["@odata.id"]
                sysDbEntry["ProcessorsUri"]=processorsUri
            else:
                self.rdr.logMsg("ERROR","..........No Processors property in SystemEntry: {}".format(rc))
                return(17) # note: returning non-zero rc, will cause a 500 error from the frontend.

        # update the base level processor Db entry 
        if sysid not in procDb:
            procDb[sysid]={}
        if "Id" not in procDb[sysid]:
            procDb[sysid]["Id"]={}
        if "UpdateTime" not in procDb[sysid]:
            procDb[sysid]["UpdateTime"]=None

        # Get the Processors Collection from the Node
        #self.rdr.logMsg("DEBUG","eeeeeeeeeeeeprocUri: {}".format(processorsUri))
        rc,r,j,dCollection=nodeRft.rfSendRecvRequest("GET",processorsUri)
        if( (rc== 0) and (r.status_code==200) and (j is True)):
            # walk the collection members and read each member to get its Id and data
            if "Members" in dCollection and (len(dCollection["Members"])< maxCollectionEntries  ):
                for member in dCollection["Members"]:
                    # extract the Uri
                    memberUri = member["@odata.id"]
                    rc,r,j,d=nodeRft.rfSendRecvRequest("GET",memberUri)
                    if( rc== 0 ):
                        # save the entry
                        memberId=d["Id"]
                        if memberId not in procDb[sysid]["Id"]:
                            procDb[sysid]["Id"][memberId]={}
                        for prop in processorInfoProperties:
                            if prop in d:
                                procDb[sysid]["Id"][memberId][prop] = d[prop]
                        for prop in fixIdracProperties:
                            if prop in d:
                                if isinstance(d[prop],list) is True:
                                    # parse current incorrect array structure returned by idrac
                                    if (len( d[prop]) > 0) and ("Member" in d[prop][0]):
                                        procDb[sysid]["Id"][memberId][prop] = d[prop][0]["Member"]
                                else:
                                    # parse correct prop=val response 
                                    procDb[sysid]["Id"][memberId][prop] = d[prop]
                        # xg99 we may want to use a flag for this
                        if "OemIntelRsd" not in procDb[sysid]["Id"][memberId]:
                            procDb[sysid]["Id"][memberId]["OemIntelRsd"] = { "Brand": "E5" }

                # add update time
                procDb[sysid]["UpdateTime"]=curTime
                return(0)
            else:
                self.rdr.logMsg("ERROR","--------BACKEND Get Processor Collecton bad response, sysid={}".format(sysid))
                return(0)
        else:
            self.rdr.logMsg("WARNING","--------BACKEND Get Processor Collecton returned error rc={}, sysid={}".format(rc,sysid))
            return(0)

        return(0)





    def updateMemoryDbFromBackend(self, sysid, memid=None, noCache=False ):
        # if here we know sysid is in systemsDb, BaseNavigationProperties is in memoryDb[sysid] 
        #    and "Memory" is in systemsDb[sysid]["BaseNavitationProperties"]
        memDb=self.rdr.root.systems.memoryDb
        memInfoCacheTimeout=self.rdr.memoryInfoCacheTimeout

        # get time 
        curTime=datetime.datetime.utcnow()
        lastMemDbUpdateTime=None

       # if using memory cache is enabled/selected, check if cache exists
        if (memInfoCacheTimeout > 0) and (noCache is False):
            if( (sysid in memDb) and ("Id" in  memDb[sysid]) and
                ("UpdateTime" in memDb[sysid]) and (memDb[sysid]["UpdateTime"] is not None) ):
                # if we have a sysid entry in memDb with an "Id" resource, then we have a mem cache
                # (the sys monitor or hotplug code will clear the db for this sysid if it is out of date
                #  by removing the entry or setting UpdateTime to None)

                #check if the cache timeout has occured
                # note lastMemDbUpdateTime in string form: "2017-06-13 16:12:02.729333"
                lastMemDbUpdateTime=datetime.datetime.strptime(str(memDb[sysid]["UpdateTime"]), "%Y-%m-%d %H:%M:%S.%f")
                # if currentTime - lastUpdateTime is less than rdr.memoryInfoCacheTimeout, return. no update required
                if ( (curTime - lastMemDbUpdateTime) < datetime.timedelta(seconds=memInfoCacheTimeout)):
                    self.rdr.logMsg("DEBUG","---------BACKEND MemoryInfo: cache not timed-out. Return w/o updating Db")
                    return(0)

        # if here, we need to update the database 
        rc=self.updateMemoryDbFromNode(sysid, memDb, curTime)
        return(rc)

    def updateMemoryDbFromNode(self, sysid, memDb, curTime):
        # tryRedfishMemoryApis  tryIpmiMemoryApis  tryIpmiStubMemoryApis
        tryRedfishMemoryApis=True # try to use Redfish to get mem inventory from BMC. set to false if it doesn't supt
        tryIpmiMemoryApis=False   # if bmc doesn't support redfish, try IPMI APIs -- not stubs
        tryIpmiStubMemoryApis=True # if bmc doesn't support redfish, use stub APIs in the ipmi transport
        redfishMemoryApiFound=None
        doIpmiCall=False
        sysDbEntry=self.rdr.root.systems.systemsDb[sysid]
        sysNetloc=sysDbEntry["Netloc"]
        sysUrl = sysDbEntry["SysUrl"]
        maxDimms=32
        memoryUri=None

        memoryInfoProperties=["Name", "DeviceLocator", "SerialNumber","MemoryType",
                              "OperatingSpeedMHz","DataWidthBits","ErrorCorrection",
                              "BaseModuleType","CapacityMiB","BusWidthBits","Manufacturer",
                              "PartNumber","MemoryDeviceType", "RankCount", "Status" ]

        # open Redfish transport to this bmc
        nodeRft = BmcRedfishTransport(rhost=sysNetloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug,
                                      credentialsPath=self.rdr.bmcCredentialsPath)

        if tryRedfishMemoryApis is True:
            # check if we already have the URI for the processors collection 
            if "MemoryUri" in sysDbEntry:
                memoryUri=sysDbEntry["MemoryUri"]
                redfishMemoryApiFound=True
            else:
                if not "RedfishMemoryApisNotFound" in sysDbEntry:
                    # if we havent already check to see if bmc support Rf api
                    # we need to query the systemEntry to get the Memory collection URI
                    self.rdr.logMsg("DEBUG","--------BACKEND memoryUri not in database. getting root. sysid={}".format(sysid))
                    # send request to the rackserver  BMC
                    rc,r,j,dsys = nodeRft.rfSendRecvRequest("GET", sysUrl )
                    if rc is not 0:
                        self.rdr.logMsg("ERROR","..........error getting service root entry rc: {}".format(rc))
                        return(18) # note: returning non-zero rc, will cause a 500 error from the frontend.
                    if "Memory" in dsys and "@odata.id" in dsys["Memory"]:
                        memoryUri=dsys["Memory"]["@odata.id"]
                        sysDbEntry["MemoryUri"]=memoryUri
                        redfishMemoryApiFound=True
                    else:
                        self.rdr.logMsg("INFO","..........No Memory property in SystemEntry-using stub: {}".format(rc))
                        #return(17) # note: returning non-zero rc, will cause a 500 error from the frontend.
                        redfishMemoryApiFound=False
                        sysDbEntry["RedfishMemoryApisNotFound"]=False

        # update the base level memory Db entry 
        if sysid not in memDb:
            memDb[sysid]={}
        if "Id" not in memDb[sysid]:
            memDb[sysid]["Id"]={}
        if "UpdateTime" not in memDb[sysid]:
            memDb[sysid]["UpdateTime"]=None

        if tryRedfishMemoryApis is True and redfishMemoryApiFound is True:
            # process response from Redfish API response from the BMC
            # Get the Memory Collection from the Node
            self.rdr.logMsg("DEBUG","eeeeeeeeeeeeprocUri: {}".format(memoryUri))
            rc,r,j,dCollection=nodeRft.rfSendRecvRequest("GET",memoryUri)
            if( (rc== 0) and (r.status_code==200) and (j is True)):
                # walk the collection members and read each member to get its Id and data
                if "Members" in dCollection and (len(dCollection["Members"])< maxDimms  ):
                    for member in dCollection["Members"]:
                        # extract the Uri
                        memberUri = member["@odata.id"]
                        rc,r,j,d=nodeRft.rfSendRecvRequest("GET",memberUri)
                        if( rc== 0 ):
                            # save the entry
                            memberId=d["Id"]
                            if memberId not in procDb[sysid]["Id"]:
                                memDb[sysid]["Id"][memberId]={}
                            for prop in memoryInfoProperties:
                                if prop in d:
                                    memDb[sysid]["Id"][memberId][prop] = d[prop]

        elif tryIpmiMemoryApis is True:
            stub=False
            doIpmiCall=True
        elif tryIpmiStubMemoryApis is True:
            stub=True
            doIpmiCall=True
        else:
                errMsg="---------BACKEND Memory APIs not supported "
                self.rdr.logMsg("ERROR",errMsg)
                return(0)

        # tryRedfishMemoryApis  tryIpmiMemoryApis  tryIpmiStubMemoryApis
        if doIpmiCall is True:
            nodeIpmiTp=BmcIpmiTransport(rhost=sysNetloc, isLocal=self.rdr.backend.isSimulator)
            # ping the node using IPMI Transport and getDeviceId command
            rc,cc,resp = nodeIpmiTp.getDeviceId(stub=stub)
            if rc!=0 or cc !=0:
                errMsg="---------BACKEND Get Mem Info using IPMI: getDevId returned error: rc: {}, cc: {}".format(rc,cc)
                self.rdr.logMsg("ERROR",errMsg)
                return(0)

            # get system Info using IPMI Transport to find out how many DIMMs are in the system
            rc,cc,resp = nodeIpmiTp.getSystemInfo(stub=stub)
            if rc!=0 or cc !=0:
                errMsg="---------BACKEND Get Mem Info using IPMI: getSystemInfo returned error: rc: {}, cc: {}".format(rc,cc)
                self.rdr.logMsg("ERROR",errMsg)
                return(0)

            if isinstance(resp, dict) and "NumOfDIMMs" in resp:
                numOfDimms = int(resp["NumOfDIMMs"])
            else:
                errMsg="---------BACKEND Get Mem Info using IPMI: getSystemInfo response not a dict or missing NumOfDIMMs"
                self.rdr.logMsg("ERROR",errMsg)
                return(0)

            if numOfDimms > maxDimms:
                self.rdr.logMsg("ERROR","---------BACKEND getMemInfo: num of dimms exceeds max:{}".format(numOfDimms))
                return(0)


            # now query node for each Dimm 1 to numOfDimms+1 to get the DIMM Info
            for dimm in range(1, numOfDimms+1):
                rc,cc,resp = nodeIpmiTp.getMemoryInfo(dimm, stub=stub)
                if rc!=0 or cc !=0 or isinstance(resp,dict) is False:
                    errMsg="---------BACKEND GetMemoryInfo returned error or nonDict: rc: {}, cc: {}, memid: {}".format(rc,cc,dimm)
                    self.rdr.logMsg("ERROR",errMsg)
                else:
                    # save the entry
                    memberId=str(dimm)
                    if memberId not in memDb[sysid]["Id"]:
                        memDb[sysid]["Id"][memberId]={}
                    for prop in memoryInfoProperties:
                        if prop in resp:
                            memDb[sysid]["Id"][memberId][prop] = resp[prop]

        # add update time
        memDb[sysid]["UpdateTime"]=curTime
        return(0)


    # update SimpleStorageDb 
    def updateSimpleStorageDbFromBackend(self, sysid, cntlrid=None, noCache=False ):
        # if here we know sysid is in systemsDb, BaseNavigationProperties is in systemsDb[sysid] 
        #    and SimpleStorage is in systemsDb[sysid]["BaseNavitationProperties"]
        simpleStorageDb=self.rdr.root.systems.simpleStorageDb
        simpleStorageInfoCacheTimeout=self.rdr.simpleStorageInfoCacheTimeout

        # get time 
        curTime=datetime.datetime.utcnow()
        lastSstoDbUpdateTime=None

        # if using simpleStorage cache is enabled/selected, check if cache exists
        if (simpleStorageInfoCacheTimeout > 0) and (noCache is False):
            if( (sysid in simpleStorageDb) and ("Id" in  simpleStorageDb[sysid]) and
                ("UpdateTime" in simpleStorageDb[sysid]) and (simpleStorageDb[sysid]["UpdateTime"] is not None) ):
                # if we have a sysid entry in simpleStorageDb with an "Id" resource, then we have a simpleStorage cache
                # (the sys monitor or hotplug code will clear the db for this sysid if it is out of date
                #  by removing the entry or setting UpdateTime to None)

                #check if the cache timeout has occured
                # note lastSstoDbUpdateTime in string form: "2017-06-13 16:12:02.729333"
                lastSstoDbUpdateTime=datetime.datetime.strptime(str(simpleStorageDb[sysid]["UpdateTime"]), "%Y-%m-%d %H:%M:%S.%f")
                # if currentTime - lastUpdateTime is less than rdr.simpleStorageInfoCacheTimeout, return. no update required
                if ( (curTime - lastSstoDbUpdateTime) < datetime.timedelta(seconds=simpleStorageInfoCacheTimeout)):
                    self.rdr.logMsg("DEBUG","---------BACKEND SimpleStorageInfo: cache not timed-out. Return w/o updating Db")
                    return(0)

        # if here, we need to update the database 
        rc=self.updateSimpleStorageDbFromNode(sysid, simpleStorageDb, curTime)
        return(rc)




    def updateSimpleStorageDbFromNode(self, sysid, simpleStorageDb, curTime):
        sysDbEntry=self.rdr.root.systems.systemsDb[sysid]
        sysNetloc=sysDbEntry["Netloc"]
        sysUrl = sysDbEntry["SysUrl"]
        simpleStorageUri=None
        maxCollectionEntries = 8

        simpleStorageInfoProperties=["Name", "UefiDevicePath" ]
        devicesProperties=["Name", "Manufacturer", "Model", "CapacityBytes", "Status"]
        statusProperties=["State", "Health" ]

        # open Redfish transport to this bmc
        nodeRft = BmcRedfishTransport(rhost=sysNetloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug,
                                      credentialsPath=self.rdr.bmcCredentialsPath)
        # check if we already have the URI for the processors collection 
        if "SimpleStorageUri" in sysDbEntry:
            simpleStorageUri=sysDbEntry["SimpleStorageUri"]
        else:
            # we need to query the systemEntry to get the SimpleStorage collection URI
            self.rdr.logMsg("DEBUG","--------BACKEND SimpleStorageUri not in database. getting root. sysid={}".format(sysid))
            # send request to the rackserver  BMC
            rc,r,j,dsys = nodeRft.rfSendRecvRequest("GET", sysUrl )
            if rc is not 0:
                self.rdr.logMsg("ERROR","..........error getting service root entry rc: {}".format(rc))
                return(18) # note: returning non-zero rc, will cause a 500 error from the frontend.
            if "SimpleStorage" in dsys and "@odata.id" in dsys["SimpleStorage"]:
                simpleStorageUri=dsys["SimpleStorage"]["@odata.id"]
                sysDbEntry["SimpleStorageUri"]=simpleStorageUri
            else:
                self.rdr.logMsg("ERROR","..........No SimpleStorage property in SystemEntry: {}".format(rc))
                return(17) # note: returning non-zero rc, will cause a 500 error from the frontend.


        # update the base level processor Db entry 
        if sysid not in simpleStorageDb:
            simpleStorageDb[sysid]={}
        if "Id" not in simpleStorageDb[sysid]:
            simpleStorageDb[sysid]["Id"]={}
        if "UpdateTime" not in simpleStorageDb[sysid]:
            simpleStorageDb[sysid]["UpdateTime"]=None

        # Get the SimpleStorage Collection from the Node
        rc,r,j,dCollection=nodeRft.rfSendRecvRequest("GET",simpleStorageUri)
        if( (rc== 0) and (r.status_code==200) and (j is True)):
            # walk the collection members and read each member to get its Id and data
            if "Members" in dCollection and (len(dCollection["Members"])< maxCollectionEntries  ):
                for member in dCollection["Members"]:
                    # extract the Uri
                    memberUri = member["@odata.id"]
                    rc,r,j,d=nodeRft.rfSendRecvRequest("GET",memberUri)
                    if( rc== 0 ):
                        # save the entry
                        memberId=d["Id"]
                        if memberId not in simpleStorageDb[sysid]["Id"]:
                            simpleStorageDb[sysid]["Id"][memberId]={}
                        for prop in simpleStorageInfoProperties:
                            if prop in d:
                                simpleStorageDb[sysid]["Id"][memberId][prop] = d[prop]
                        deviceList=[]
                        if "Devices" in d:
                            for device in d["Devices"]:
                                thisDeviceEntry=dict()
                                for prop in devicesProperties:
                                    if prop in device:
                                        thisDeviceEntry[prop]=device[prop]
                                deviceList.append(thisDeviceEntry)
                        simpleStorageDb[sysid]["Id"][memberId]["Devices"] = deviceList

                # add update time
                simpleStorageDb[sysid]["UpdateTime"]=curTime
                return(0)
            else:
                self.rdr.logMsg("ERROR","--------BACKEND Get SimpleStorage Collecton bad response, sysid={}".format(sysid))
                return(0)
        else:
            self.rdr.logMsg("WARNING","--------BACKEND Get SimpleStorage Collecton returned error rc={}, sysid={}".format(rc,sysid))
            return(0)

        return(0)


    # update EthernetInterfaceDb 
    def updateEthernetInterfaceDbFromBackend(self, sysid, ethid=None, noCache=False ):
        # if here we know sysid is in systemsDb, BaseNavigationProperties is in systemsDb[sysid] 
        #    and EthernetInterfaces is in systemsDb[sysid]["BaseNavitationProperties"]
        ethDb=self.rdr.root.systems.ethernetInterfaceDb
        ethInfoCacheTimeout=self.rdr.ethernetInterfaceInfoCacheTimeout

        # get time 
        curTime=datetime.datetime.utcnow()
        lastEthDbUpdateTime=None


        # if using processor cache is enabled/selected, check if cache exists
        if (ethInfoCacheTimeout > 0) and (noCache is False):
            if( (sysid in ethDb) and ("Id" in  ethDb[sysid]) and
                ("UpdateTime" in ethDb[sysid]) and (ethDb[sysid]["UpdateTime"] is not None) ):
                # if we have a sysid entry in ethDb with an "Id" resource, then we have a eth interface cache
                # (the sys monitor or hotplug code will clear the db for this sysid if it is out of date
                #  by removing the entry or setting UpdateTime to None)

                #check if the cache timeout has occured
                # note lastProcDbUpdateTime in string form: "2017-06-13 16:12:02.729333"
                lastEthDbUpdateTime=datetime.datetime.strptime(str(ethDb[sysid]["UpdateTime"]), "%Y-%m-%d %H:%M:%S.%f")
                # if currentTime - lastUpdateTime is less than rdr.ethInfoCacheTimeout, return. no update required
                if ( (curTime - lastEthDbUpdateTime) < datetime.timedelta(seconds=ethInfoCacheTimeout)):
                    self.rdr.logMsg("DEBUG","---------BACKEND EthernetInterfaceInfo: cache not timed-out. Return w/o updating Db")
                    return(0)

        # if here, we need to update the database 
        rc=self.updateEthernetInterfaceDbFromNode(sysid, ethDb, curTime)
        return(rc)



    def updateEthernetInterfaceDbFromNode(self, sysid, ethDb, curTime):
        sysDbEntry=self.rdr.root.systems.systemsDb[sysid]
        sysNetloc=sysDbEntry["Netloc"]
        sysUrl = sysDbEntry["SysUrl"]
        ethernetInterfacesUri=None
        maxCollectionEntries = 8

        ethernetInterfaceProperties=["Name", "MACAddress", "PermanentMACAddress" ]

        # open Redfish transport to this bmc
        nodeRft = BmcRedfishTransport(rhost=sysNetloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug,
                                      credentialsPath=self.rdr.bmcCredentialsPath)

        # check if we already have the URI for the processors collection 
        if "ethernetInterfacesUri" in sysDbEntry:
            ethernetInterfacesUri=sysDbEntry["EthernetInterfacesUri"]
        else:
            # we need to query the systemEntry to get the Processor collection URI
            self.rdr.logMsg("DEBUG","--------BACKEND EthernetInterfacesUri not in database. getting root. sysid={}".format(sysid))
            # send request to the rackserver  BMC
            rc,r,j,dsys = nodeRft.rfSendRecvRequest("GET", sysUrl )
            if rc is not 0:
                self.rdr.logMsg("ERROR","..........error getting service root entry rc: {}".format(rc))
                return(18) # note: returning non-zero rc, will cause a 500 error from the frontend.
            if "EthernetInterfaces" in dsys and "@odata.id" in dsys["EthernetInterfaces"]:
                ethernetInterfacesUri=dsys["EthernetInterfaces"]["@odata.id"]
                sysDbEntry["EthernetInterfacesUri"]=ethernetInterfacesUri
            else:
                self.rdr.logMsg("ERROR","..........No EthernetInterfaces property in SystemEntry: {}".format(rc))
                return(17) # note: returning non-zero rc, will cause a 500 error from the frontend.

        # update the base level processor Db entry 
        if sysid not in ethDb:
            ethDb[sysid]={}
        if "Id" not in ethDb[sysid]:
            ethDb[sysid]["Id"]={}
        if "UpdateTime" not in ethDb[sysid]:
            ethDb[sysid]["UpdateTime"]=None
        # Get the Processors Collection from the Node
        rc,r,j,dCollection=nodeRft.rfSendRecvRequest("GET",ethernetInterfacesUri)
        if( (rc== 0) and (r.status_code==200) and (j is True)):
            # walk the collection members and read each member to get its Id and data
            if "Members" in dCollection and (len(dCollection["Members"])< maxCollectionEntries  ):
                for member in dCollection["Members"]:
                    # extract the Uri
                    memberUri = member["@odata.id"]
                    rc,r,j,d=nodeRft.rfSendRecvRequest("GET",memberUri)
                    if( rc== 0 ):
                        # save the entry
                        memberId=d["Id"]
                        if memberId not in ethDb[sysid]["Id"]:
                            ethDb[sysid]["Id"][memberId]={}
                        for prop in ethernetInterfaceProperties:
                            if prop in d:
                                if d[prop]=="":
                                    ethDb[sysid]["Id"][memberId][prop] = None
                                else:
                                    ethDb[sysid]["Id"][memberId][prop] = d[prop]

                # add update time
                ethDb[sysid]["UpdateTime"]=curTime
                return(0)
            else:
                self.rdr.logMsg("ERROR","--------BACKEND Get EthernetInterface Collecton bad response, sysid={}".format(sysid))
                return(0)
        else:
            self.rdr.logMsg("WARNING","--------BACKEND Get EthernetInterface Collecton returned error rc={}, sysid={}".format(rc,sysid))
            return(0)

        return(0)


