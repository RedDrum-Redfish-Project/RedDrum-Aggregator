
# Copyright Notice:
#    Copyright 2018 Dell, Inc. All rights reserved.
#    License: BSD License.  For full license text see link: https://github.com/RedDrum-Redfish-Project/RedDrum-OpenBMC/LICENSE.txt

import time,json
import datetime
from .redfishTransports import BmcRedfishTransport

# RedDrum-Aggregator chassisBackend resources
#
class  RdChassisBackend():
    # class for backend chassis resource APIs
    def __init__(self,rdr):
        self.version=0.9
        self.rdr=rdr
        self.debug=False
        self.supportAggregationChassis=True   # set True for aggregator
        self.supportDss9000Rack=False         # set False for aggregator


    # update resourceDB and volatileDict properties for a base Chassis GET
    def updateResourceDbs(self,chassisid, updateStaticProps=False, updateNonVols=True ):
        self.rdr.logMsg("DEBUG","--------BACKEND updateResourceDBs. updateStaticProps={}".format(updateStaticProps))
        resDb=self.rdr.root.chassis.chassisDb[chassisid]
        resVolDb=self.rdr.root.chassis.chassisVolatileDict[chassisid]
        staticProperties=self.rdr.root.chassis.staticProperties
        nonVolatileProperties=self.rdr.root.chassis.nonVolatileProperties
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
            if ( (curTime - lastDbUpdateTime) < datetime.timedelta(seconds=10)):
                self.rdr.logMsg("DEBUG","----------Chas Backend: time < min DbUpdateTime.  Returning w/o updating DBs")
                return(0,False)

        # STAGE1 of UPDATE:  get the sysHwMonData for the specific chassis resource
        sysHwMonData=dict()

        # disable flow for non-aggregator
        if self.supportDss9000Rack is True: 
            pass
            # do the flow below here

            # #if chassis is [Dss9000] Rack  
            # if self.g5id.isRack(chassisid):    # check if dss9000 rack chassis
            #     ...
            #     isDss9000Chassis=True
            #     sysHwMonData = ...

            # #elif chassis is [Dss9000] PowerBay
            # elif self.g5id.isPowerBay(chassisid):
            #     ...
            #     isDss9000Chassis=True
            #     sysHwMonData = ...

            # #elif chassis is [Dss9000] Block
            # elif self.g5id.isBlock(chassisid):
            #     ...
            #     isDss9000Chassis=True
            #     sysHwMonData = ...

            # #elif chassis is [Dss9000] Sled chassis
            # elif self.g5id.isSled(chassisid):
            #     isDss9000Chassis=True
            #     #if compute sled
            #      if self.g5id.isJbodSled(self.rdr, chassisid) is False:  # it is a Compute Sled
            #        ... compute sled
            #         sysHwMonData = ...

            #     #else if jbod
            #     else: 
            #         ... jbod
            #         sysHwMonData = ...

            #

        if self.isChassisAnAggregationRackChassis(chassisid) is True: 
            # if chassis is the top-level chassis enclosure in an aggregator rack
            if "IsTopLevelChassisInAggrRack" in resDb and resDb["IsTopLevelChassisInAggrRack"] is True:
                # update top level chassis properties
                # xgTODO
                sysHwMonData["PowerState"]="On"
    
            # else if chassis is the Mgt Switch chassis 
            elif "IsMgtSwitchChassisInAggrRack" in resDb and resDb["IsMgtSwitchChassisInAggrRack"] is True:
                # get data from MgtSwitch
                # xgTODO
                sysHwMonData["PowerState"]="On"
    
            # else if chassis is an aggregator Host Server chassis (agg mgr in a separate chassis)
            elif "IsAggrHostServerChassisInAggrRack" in resDb and resDb["IsAggrHostServerChassisInAggrRack"] is True:
                # get data from the Aggregator Host server's local bmc
                # xgTODO
                sysHwMonData["PowerState"]="On"
    
            # else if this is a RackServer chassis (monolythic in the rack)
            elif "IsRackServerChassis" in resDb and resDb["IsRackServerChassis"] is True:
                # get data about the rackServer chassis from the bmc
                if "Netloc" in resDb and "ChasUrl" in resDb:
                    bmcNetloc=resDb["Netloc"]
                    chasUrl=resDb["ChasUrl"]
                else:
                    return(17,False)
    
                # open Redfish transport to this bmc
                rft = BmcRedfishTransport(rhost=bmcNetloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug,
                                          credentialsPath=self.rdr.bmcCredentialsPath)
                # send request to the rackserver  BMC
                rc,r,j,sysHwMonData = rft.rfSendRecvRequest("GET", chasUrl )
                if rc is not 0:
                    self.rdr.logMsg("ERROR","..........error getting chassis entry from rackserver BMC: {}. rc: {}".format(chassisid,rc))
                    return(19,False) # note: returning non-zero rc, will cause a 500 error from the frontend.
    
            # else:  dont know what kind of aggregation chassis this is, just skip it
            else:
                pass


        # STAGE2 of UPDATE:  check if cache is ahead of monitors
        # note that for aggregator, updateTime is not in sysHwMonData so this is a no-op for compatibility w/ dss9000 backend
        # check if  HWMonUpdate preceeds the last FrontEnd cache update 
        # if front-end vol cache is later, then we patched data and HW monitor has not yet caught up
        hwMonUpdateTime=None
        if "updateTime" in sysHwMonData:
            hwMonUpdateTime=datetime.datetime.strptime(str(sysHwMonData["updateTime"]), "%Y-%m-%d %H:%M:%S.%f")
            if lastDbUpdateTime is not None:
                if ( hwMonUpdateTime < lastDbUpdateTime ):
                    self.rdr.logMsg("DEBUG","----------Chas Backend: FrontEnd database were updated after HWMonitors last updated HWMon Db")
                    return(0,False)

        # save front-end database update timestamp
        resVolDb["UpdateTime"] = curTime


        # STAGE3 of UPDATE:  update the resource Db from sysHwMonData obtained in stage1
        # update Static data if flag is set to do so.   
        # this is generally done once to pickup static data discovered by backend
        if updateStaticProps is True:
            for prop in staticProperties:
                if (prop in resDb) and (prop in sysHwMonData):
                    if resDb[prop] != sysHwMonData[prop]:
                        resDb[prop]=sysHwMonData[prop]
                        updatedResourceDb=True

        # update Volatile Properties
        if "Volatile" in resDb:
             for prop in resDb["Volatile"]:
                if prop in sysHwMonData:
                    resVolDb[prop]=sysHwMonData[prop]

        # update the volatile status properties
        if ("Status" in resDb) and ("Status" in sysHwMonData):
            for prop in resDb["Status"]:
                if prop in sysHwMonData["Status"]:
                    if "Status" not in resVolDb:
                        resVolDb["Status"]={}
                    resVolDb["Status"][prop]=sysHwMonData["Status"][prop]
        # update NonVolatile Properties
        if updateNonVols is True:
            for prop in nonVolatileProperties:
                if (prop in resDb) and (prop in sysHwMonData):
                    if resDb[prop] != sysHwMonData[prop]:
                        resDb[prop]=sysHwMonData[prop]
                        updatedResourceDb=True

        # update Actions Reset AllowableValues
        if "ActionsResetAllowableValues" in resDb:
            if "Actions" in sysHwMonData and "#Chassis.Reset" in sysHwMonData["Actions"]:
                if "ResetType@Redfish.AllowableValues" in sysHwMonData["Actions"]["#Chassis.Reset"]:
                    resDb["ActionsResetAllowableValues"]=sysHwMonData["Actions"]["#Chassis.Reset"]["ResetType@Redfish.AllowableValues"]
                    updatedResourceDb=True
                if "target" in sysHwMonData["Actions"]["#Chassis.Reset"]:
                    resDb["SysResetTargetUrl"]=sysHwMonData["Actions"]["#Chassis.Reset"]["target"]
                    updatedResourceDb=True

        rc=0     # 0=ok
        return(rc,updatedResourceDb)


    def doChassisReset(self, chassisid, resetType):
        self.rdr.logMsg("DEBUG","--------BACKEND got POST for chassis Reset.  resetType={}".format(resetType))
        sendResetToBmc=False
        resDb=self.rdr.root.chassis.chassisDb[chassisid]

        # the front-end has already validated that the patchData and chassisid is ok
        if "IsTopLevelChassisInAggrRack" in resDb and resDb["IsTopLevelChassisInAggrRack"] is True:
            # xgTODO 
            netloc = None
            chasUrl = None
            sendResetToBmc = False # for now
            rc=0
    
        # else if chassis is the Mgt Switch chassis 
        elif "IsMgtSwitchChassisInAggrRack" in resDb and resDb["IsMgtSwitchChassisInAggrRack"] is True:
            # patch data in MgtSwitch
            # xgTODO
            netloc = None
            chasUrl = None
            sendResetToBmc = False # for now
            rc=0
    
        # else if chassis is an aggregator Host Server chassis (agg mgr in a separate chassis)
        elif "IsAggrHostServerChassisInAggrRack" in resDb and resDb["IsAggrHostServerChassisInAggrRack"] is True:
            # get data from the Aggregator Host server's local bmc
            # xgTODO
            netloc = None
            chasUrl = None
            sendResetToBmc = False # for now
            rc=0
    
        # else if this is a RackServer chassis (monolythic in the rack)
        elif "IsRackServerChassis" in resDb and resDb["IsRackServerChassis"] is True:
            # extract the netloc and chassis entry URL from the chassisDb saved during discovery
            sendResetToBmc = True
            netloc = resDb["Netloc"]
            chasUrl = resDb["ChasUrl"]

            # open Redfish transport to this bmc
            rft = BmcRedfishTransport(rhost=netloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug,
                                      credentialsPath=self.rdr.bmcCredentialsPath)
        else:
            rc=9

        # execute below if sendResetToBmc was set true, and netloc, chasUrl, and rft have been set above
        if sendResetToBmc is True: 
            # check if we already have a system reset URI collected
            if "ChasResetTargetUrl" in resDb:
                chasResetTargetUrl = resDb["ChasResetTargetUrl"]
            else:
                # send request to the rackserver  BMC to read the chassis resource
                rc,r,j,d = rft.rfSendRecvRequest("GET", chasUrl )
                if rc is not 0:
                    self.rdr.logMsg("ERROR","..........error getting chassis entry from rackserver BMC: {}. rc: {}".format(systemid,rc))
                    return(19,False) # note: returning non-zero rc, will cause a 500 error from the frontend.
                if "Actions" in d and "#Chassis.Reset" in d["Actions"]:
                    if "target" in d["Actions"]["#Chassis.Reset"]:
                        chasResetTargetUrl = d["Actions"]["#Chassis.Reset"]["target"]
                        resDb["ChasResetTargetUrl"] = chasResetTargetUrl
                        updatedResourceDb=True
                    if "ResetType@Redfish.AllowableValues" in d["Actions"]["#Chassis.Reset"]:
                        resDb["ActionsResetAllowableValues"]=d["Actions"]["#Chassis.Reset"]["ResetType@Redfish.AllowableValues"]
                        updatedResourceDb=True
                    # xg99 todo, support using getActionInfoAllowableValues

            # check if reset type is in allowable values
            allowableValues=resDb["ActionsResetAllowableValues"]
            if resetType not in allowableValues:
                return(400)

            # send Post request to the rackserver  BMC to reset
            self.rdr.logMsg("INFO","-------- BACKEND sending Post Reset to bmc")
            resetData = { "ResetType": resetType }
            reqPostData=json.dumps(resetData)

            rc,r,j,dsys = rft.rfSendRecvRequest("POST", chasUrl,reqData=reqPostData )
            if rc is not 0:
                self.rdr.logMsg("ERROR","..........error sending chassis reset to rackserver BMC: {}. rc: {}".format(chassisid,rc))
                return(19,False) # note: returning non-zero rc, will cause a 500 error from the frontend.
        return(rc)


    def doChassisOemReseat(self, chassisid ):
        self.rdr.logMsg("DEBUG","--------BACKEND POST for Chassis OemReseat")
        reseatViaPdu=False
        resDb=self.rdr.root.chassis.chassisDb[chassisid]

        # the front-end has already validated that the patchData and chassisid is ok
        if "IsTopLevelChassisInAggrRack" in resDb and resDb["IsTopLevelChassisInAggrRack"] is True:
            # xgTODO 
            netloc = None
            chasUrl = None
            reseatViaPdu = False # for now
            rc=0
    
        # else if chassis is the Mgt Switch chassis 
        elif "IsMgtSwitchChassisInAggrRack" in resDb and resDb["IsMgtSwitchChassisInAggrRack"] is True:
            # patch data in MgtSwitch
            # xgTODO
            netloc = None
            chasUrl = None
            reseatViaPdu = False # for now
            rc=0
    
        # else if chassis is an aggregator Host Server chassis (agg mgr in a separate chassis)
        elif "IsAggrHostServerChassisInAggrRack" in resDb and resDb["IsAggrHostServerChassisInAggrRack"] is True:
            # get data from the Aggregator Host server's local bmc
            # xgTODO
            netloc = None
            chasUrl = None
            reseatViaPdu = False # for now
            rc=0
    
        # else if this is a RackServer chassis (monolythic in the rack)
        elif "IsRackServerChassis" in resDb and resDb["IsRackServerChassis"] is True:
            # extract the netloc and chassis entry URL from the chassisDb saved during discovery
            reseatViaPdu=True
            netloc = resDb["Netloc"]
            chasUrl = resDb["ChasUrl"]

        else:
            rc=9

        # execute below if sendReseatToBmc was set true, and netloc, chasUrl, and rft have been set above
        if reseatViaPdu is True: 
            # send Post request to the rackserver  BMC to reseat
            self.rdr.logMsg("INFO","-------- BACKEND sending msg to smart PDU to Reseat chas")
            rc=0

        return(rc)




    #PATCH Chassis
    # patchData is a dict of form: { <patchProperty>: <patchValue> }
    #    the front-end will send an individual call for IndicatorLED and AssetTag 
    # DO Patch to chassis  (IndicatorLED, AssetTag) 
    # the front-end will send an individual call for IndicatorLED and AssetTag 
    def doPatch(self, chassisid, patchData):
        # so just send the request here
        sendPatchToBmc=False
        self.rdr.logMsg("DEBUG","--------BACKEND Patch chassis data. patchData={}".format(patchData))
        resDb=self.rdr.root.chassis.chassisDb[chassisid]

        # the front-end has already validated that the patchData and chassisid is ok
        if "IsTopLevelChassisInAggrRack" in resDb and resDb["IsTopLevelChassisInAggrRack"] is True:
            # xgTODO 
            netloc = None
            chasUrl = None
            sendPatchToBmc = False # for now
            rc=0
    
        # else if chassis is the Mgt Switch chassis 
        elif "IsMgtSwitchChassisInAggrRack" in resDb and resDb["IsMgtSwitchChassisInAggrRack"] is True:
            # patch data in MgtSwitch
            # xgTODO
            netloc = None
            chasUrl = None
            sendPatchToBmc = False # for now
            rc=0
    
        # else if chassis is an aggregator Host Server chassis (agg mgr in a separate chassis)
        elif "IsAggrHostServerChassisInAggrRack" in resDb and resDb["IsAggrHostServerChassisInAggrRack"] is True:
            # get data from the Aggregator Host server's local bmc
            # xgTODO
            netloc = None
            chasUrl = None
            sendPatchToBmc = False # for now
            rc=0
    
        # else if this is a RackServer chassis (monolythic in the rack)
        elif "IsRackServerChassis" in resDb and resDb["IsRackServerChassis"] is True:
            # extract the netloc and chassis entry URL from the chassisDb saved during discovery
            sendPatchToBmc=True
            netloc = resDb["Netloc"]
            chasUrl = resDb["ChasUrl"]

            # open Redfish transport to this bmc
            rft = BmcRedfishTransport(rhost=netloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug,
                                      credentialsPath=self.rdr.bmcCredentialsPath)
        else:
            rc=9

        # execute below if sendPatchToBmc was set true, and netloc, chasUrl, and rft have been set above
        if sendPatchToBmc is True: 
            # send PATCH request to the rackserver  BMC to reset
            self.rdr.logMsg("INFO","-------- BACKEND sending Patch to bmc")
            reqPatchData=json.dumps(patchData)

            rc,r,j,dsys = rft.rfSendRecvRequest("PATCH", chasUrl,reqData=reqPatchData )
            if rc is not 0:
                self.rdr.logMsg("ERROR","..........error sending chassis patch to rackserver BMC: {}. rc: {}".format(chassisid,rc))
                return(19,False) # note: returning non-zero rc, will cause a 500 error from the frontend.
        return(rc)


    # check if this chassis is a rack aggregation chassis
    #    -returns True or False
    def isChassisAnAggregationRackChassis(self, chassisid):
        if self.supportAggregationChassis is not True:
            return(False)

        # return false if the chassis does not exist
        if not chassisid in self.rdr.root.chassis.chassisDb:
            return(0,False)

        # get the chassis entry
        thisChasDb=self.rdr.root.chassis.chassisDb[chassisid]

        # if chassis is the top-level rack enclosure
        if "IsTopLevelChassisInAggrRack" in thisChasDb and thisChasDb["IsTopLevelChassisInAggrRack"] is True:
            return(True)

        # else if chassis is the Mgt Switch chassis 
        elif "IsMgtSwitchChassisInAggrRack" in thisChasDb and thisChasDb["IsMgtSwitchChassisInAggrRack"] is True:
            return(True)

        # else if chassis is an aggregator Host Server chassis (agg mgr in a separate chassis)
        elif "IsAggrHostServerChassisInAggrRack" in thisChasDb and thisChasDb["IsAggrHostServerChassisInAggrRack"] is True:
            return(True)

        # else if this is a RackServer chassis (monolythic in the rack)
        elif "IsRackServerChassis" in thisChasDb and thisChasDb["IsRackServerChassis"] is True:
            return(True)
        else:
            return(False)

    def isRackServerChassis(self,chassisid):
        if self.supportAggregationChassis is not True:
            return(False)
        # return false if the chassis does not exist
        if not chassisid in self.rdr.root.chassis.chassisDb:
            return(0,False)
        # get the chassis entry
        thisChasDb=self.rdr.root.chassis.chassisDb[chassisid]
        if "IsRackServerChassis" in thisChasDb and thisChasDb["IsRackServerChassis"] is True:
            return(True)
        else:
            return(False)
        

    # update Temperatures resourceDB and volatileDict properties
    # returns: rc, updatedResourceDb(T/F).  rc=0 if no error
    def updateTemperaturesResourceDbs(self, chassisid, updateStaticProps=False, updateNonVols=True ):
        self.rdr.logMsg("DEBUG","--------BE updateTemperaturesResourceDBs. updateStaticProps={}".format(updateStaticProps))

        # The aggregator will update all "thermal" Dbs (temperaturesDb + fansDb) when the Frontend calls this api
        if self.isChassisAnAggregationRackChassis(chassisid) is True:
            rc,updatedResourceDb=self.aggregatorUpdateThermalResources(chassisid, updateStaticProps, updateNonVols)
            return(rc,updatedResourceDb)
        # ...if here, the flow is normal non-aggregator flow
        
        # Defensive check for temporary time. We are returning False, because the below logic
        # is not completed and gives failures.
        #return (0,False)
        # set hashname and local properties to point to this chassisid Db and VolDict, ...
        self.curChasDb=self.rdr.root.chassis.chasDb
        self.resDb=self.rdr.root.chassis.tempSensorsDb[chassisid]
        self.resVolDb=self.rdr.root.chassis.tempSensorsVolatileDict[chassisid]
        self.staticProperties=self.rdr.root.chassis.temperatureStaticProperties
        self.nonVolatileProperties=self.rdr.root.chassis.temperatureNonVolatileProperties
        redisHash="TemperaturesMonHashDb" 
        # call generic methods to update the DBs from the redis hash
        rc,curTime,lastDbUpdateTime=self.genericChkIfRecentDbUpdate(self.resVolDb)
        # if we recently updated the resources, return rc=0 (no-error) w/o updating them again
        if( rc==1 ):
            return(0,False)
        rc,updatedResourceDb=self.genericUpdateResourceDbs(chassisid, curTime, lastDbUpdateTime, redisHash,
                                   updateStaticProps=updateStaticProps, updateNonVols=updateNonVols )
        return(rc,updatedResourceDb)


    # update Fans resourceDB and volatileDict properties
    # returns: rc, updatedResourceDb(T/F).  rc=0 if no error
    def updateFansResourceDbs(self, chassisid, updateStaticProps=False, updateNonVols=True ):
        self.rdr.logMsg("DEBUG","--------BE updateFansResourceDBs. updateStaticProps={}".format(updateStaticProps))

        # The aggregator updates FansDb when updateTemperatureResourceDbs is called. so just return ok here 
        if self.isChassisAnAggregationRackChassis(chassisid) is True:
            return(0,False)

        # ...if here, the flow is normal non-aggregator flow
        
        # Defensive check for temporary time. We are returning False, because the below logic
        # is not completed and gives failures.
        # return (0,False)
        # set hashname and local properties to point to this chassisid Db and VolDict, ...
        self.resDb=self.rdr.root.chassis.fansDb[chassisid]
        self.resVolDb=self.rdr.root.chassis.fansVolatileDict[chassisid]
        self.staticProperties=self.rdr.root.chassis.fansStaticProperties
        self.nonVolatileProperties=self.rdr.root.chassis.fansNonVolatileProperties
        redisHash="FanMonHashDb"

        # call generic methods to update the DBs from the redis hash
        rc,curTime,lastDbUpdateTime=self.genericChkIfRecentDbUpdate(self.resVolDb)
        # if we recently updated the resources, return rc=0 (no-error) w/o updating them again
        if( rc==1 ):
            return(0,False)

        rc,updatedResourceDb=self.genericUpdateResourceDbs(chassisid, curTime, lastDbUpdateTime, redisHash,
                                   updateStaticProps=updateStaticProps, updateNonVols=updateNonVols )
        # updatedResourceDb=""
        # rc=0
        return(rc,updatedResourceDb)




    # update Voltages resourceDB and volatileDict properties
    # returns: rc, updatedResourceDb(T/F).  rc=0 if no error
    def updateVoltagesResourceDbs(self, chassisid, updateStaticProps=False, updateNonVols=True ):
        self.rdr.logMsg("DEBUG","--------BE updateVoltagesResourceDBs. updateStaticProps={}".format(updateStaticProps))

        # The aggregator will update all "power" Dbs (voltagesDb + powerControlDb + powerSuppliesDb) when the Frontend 
        #    calls this api
        if self.isChassisAnAggregationRackChassis(chassisid) is True:
            rc,updatedResourceDb=self.aggregatorUpdatePowerResources(chassisid, updateStaticProps, updateNonVols)
            return(rc,updatedResourceDb)
        # ...if here, the flow is normal non-aggregator flow

        # Defensive check for temporary time. We are returning False, because the below logic
        # is not completed and gives failures.        
        #return (0,False)
        # set hashname and local properties to point to this chassisid Db and VolDict, ...
        self.resDb=self.rdr.root.chassis.voltageSensorsDb[chassisid]
        self.resVolDb=self.rdr.root.chassis.voltageSensorsVolatileDict[chassisid]
        self.staticProperties=self.rdr.root.chassis.voltagesStaticProperties
        self.nonVolatileProperties=self.rdr.root.chassis.voltagesNonVolatileProperties
        redisHash="VoltagesMonHashDb"

        # call generic methods to update the DBs from the redis hash
        rc,curTime,lastDbUpdateTime=self.genericChkIfRecentDbUpdate(self.resVolDb)
        # if we recently updated the resources, return rc=0 (no-error) w/o updating them again
        if( rc==1 ):
            return(0,False)

        rc,updatedResourceDb=self.genericUpdateResourceDbs(chassisid,  curTime, lastDbUpdateTime, redisHash,
                                   updateStaticProps=updateStaticProps, updateNonVols=updateNonVols )
        return(rc,updatedResourceDb)



    # update PowerControl resourceDB and volatileDict properties
    # returns: rc, updatedResourceDb(T/F).  rc=0 if no error
    def updatePowerControlResourceDbs(self, chassisid, updateStaticProps=False, updateNonVols=True ):
        self.rdr.logMsg("DEBUG","--------BE updatePowerControlResourceDBs. updateStaticProps={}".format(updateStaticProps))

        # The aggregator updates powerControlDb when updateVoltagesResourceDbs is called. so just return ok here 
        if self.isChassisAnAggregationRackChassis(chassisid) is True:
            return(0,False)

        # ...if here, the flow is normal non-aggregator flow
        

        # Defensive check for temporary time. We are returning False, because the below logic
        # is not completed and gives failures.
        # return (0,False)

        # set hashname and local properties to point to this chassisid Db and VolDict, ...
        self.resDb=self.rdr.root.chassis.powerControlDb[chassisid]
        self.resVolDb=self.rdr.root.chassis.powerControlVolatileDict[chassisid]
        self.staticProperties=self.rdr.root.chassis.powerControlStaticProperties
        self.nonVolatileProperties=[]
        redisHash="PowerControlMonHashDb"

        # call generic methods to update the DBs from the redis hash
        rc,curTime,lastDbUpdateTime=self.genericChkIfRecentDbUpdate(self.resVolDb)
        # if we recently updated the resources, return rc=0 (no-error) w/o updating them again
        if( rc==1 ):
            return(0,False)

        rc,updatedResourceDb=self.genericUpdateResourceDbs(chassisid, curTime, lastDbUpdateTime, redisHash,
                                   updateStaticProps=updateStaticProps, updateNonVols=updateNonVols )
        return(rc,updatedResourceDb)


    # update PowerSupplies resourceDB and volatileDict properties
    # returns: rc, updatedResourceDb(T/F).  rc=0 if no error
    def updatePowerSuppliesResourceDbs(self, chassisid, updateStaticProps=False, updateNonVols=True ):
        self.rdr.logMsg("DEBUG","--------BE updatePowerSuppliesResourceDBs. updateStaticProps={}".format(updateStaticProps))
        # The aggregator updates powerControlDb when updateVoltagesResourceDbs is called. so just return ok here 
        if self.isChassisAnAggregationRackChassis(chassisid) is True:
            return(0,False)

        # ...if here, the flow is normal non-aggregator flow

        # Defensive check for temporary time. We are returning False, because the below logic
        # is not completed and gives failures.        
        # return (0,False)
        # set hashname and local properties to point to this chassisid Db and VolDict, ...
        
        self.resDb=self.rdr.root.chassis.powerSuppliesDb[chassisid]
        self.resVolDb=self.rdr.root.chassis.powerSuppliesVolatileDict[chassisid]
        self.staticProperties=self.rdr.root.chassis.psusStaticProperties
        self.nonVolatileProperties=self.rdr.root.chassis.psusNonVolatileProperties
        redisHash="PowerSuppliesMonHashDb"

        # call generic methods to update the DBs from the redis hash
        rc,curTime,lastDbUpdateTime=self.genericChkIfRecentDbUpdate(self.resVolDb)
        # if we recently updated the resources, return rc=0 (no-error) w/o updating them again
        if( rc==1 ):
            return(0,False)

        rc,updatedResourceDb=self.genericUpdateResourceDbs(chassisid,  curTime, lastDbUpdateTime, redisHash,
                                   updateStaticProps=updateStaticProps, updateNonVols=updateNonVols )
        return(rc,updatedResourceDb)


    # get curTime, initialize lastDbUpdateTIme, and check if we have updated the resourceDb recently
    #   here: recently is 10 sec
    # return rc, curTime, lastDbUpdateTime
    # if we have recently updated the resourceDbs, rc=1,
    def genericChkIfRecentDbUpdate(self,resVolDb ):

        # check if front-end database was updated within the last few sec
        # if so, don't try to update from HWMonitor Redis Db
        curTime=datetime.datetime.utcnow()
        lastDbUpdateTime=None
        rc=0
        if "UpdateTime" in resVolDb:
            # note lastDbUpdateTime in string form: "2017-06-13 16:12:02.729333"
            lastDbUpdateTime=datetime.datetime.strptime(str(resVolDb["UpdateTime"]), "%Y-%m-%d %H:%M:%S.%f")
            # if less than a sec since we update the volatile dict, just return and use current database
            if ( (curTime - lastDbUpdateTime) < datetime.timedelta(seconds=10)):
                self.rdr.logMsg("DEBUG","----------Chas Backend: time < min DbUpdateTime.  Returning w/o updating DBs")
                rc=1
        return(rc,curTime,lastDbUpdateTime)



    # update all Thermal Databases:  tempSensorsDb, FansDb
    #    - used by aggregator
    #    - returns rc=0 if no error, non-zero if error,
    #    - returns updatedResourceDb (True/False) indicating if the resourceDb was updated
    def aggregatorUpdateThermalResources(self,chassisid, updateStaticProps, updateNonVols):
        # first use tempSensorsDb to determine if Thermal resources have been recently updated
        self.resVolDb=self.rdr.root.chassis.tempSensorsVolatileDict[chassisid]
        # call generic methods to update the DBs from the redis hash
        rc,curTime,lastDbUpdateTime=self.genericChkIfRecentDbUpdate(self.resVolDb)
        # if we recently updated the resources, return rc=0 (no-error) w/o updating them again
        if( rc==1 ):
            return(0,False)

        # xg9 currently we dont support Power and Thermal on the MgtSwitch or aggregationManagerHost chassis
        if self.isRackServerChassis(chassisid) is not True:
            return(0,False)

        # if here, we need to update both tempSensorsDb and FansDb
        # get the resource data from the bmc
        if chassisid in self.rdr.root.chassis.chassisDb:
            thisChasDb=self.rdr.root.chassis.chassisDb[chassisid]
        else:
            return(0,False)
        if "Netloc" in thisChasDb and "ChasUrl" in thisChasDb:
            bmcNetloc=thisChasDb["Netloc"]
            chasUrl=thisChasDb["ChasUrl"]
        else:
            return(17,False)

        # open Redfish transport to this bmc
        rft = BmcRedfishTransport(rhost=bmcNetloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug,
                                      credentialsPath=self.rdr.bmcCredentialsPath)
        # if we have never stored the thermal or Power Url, read the chassis now and store them
        if "ThermalUrl" in thisChasDb:
            thermalUrl=thisChasDb["ThermalUrl"]
        else:
            rc,r,j,d = rft.rfSendRecvRequest("GET", chasUrl )
            if rc is not 0:
                self.rdr.logMsg("ERROR","..........error getting chassis entry from rackserver BMC: {}. rc: {}".format(chassisid,rc))
                return(19,False) # note: returning non-zero rc, will cause a 500 error from the frontend.
                # we should handle case where no power or thermal resource and return 404?
            # save both thermal and power URLs
            thermalUrl=None
            powerUrl=None
            if "Thermal" in d and "@odata.id" in d["Thermal"]:
                thermalUrl=d["Thermal"]["@odata.id"]
            if "Power" in d and "@odata.id" in d["Thermal"]:
                powerUrl=d["Power"]["@odata.id"]
            thisChasDb["ThermalUrl"] = thermalUrl
            if "PowerUrl" not in thisChasDb:  # update powerUrl if its not already there
                thisChasDb["PowerUrl"] = powerUrl
        # now we have the thermalUrl, get the response from bmc
        if thermalUrl is not None:
            rc,r,j,d = rft.rfSendRecvRequest("GET", thermalUrl )
            if rc is not 0:
                self.rdr.logMsg("ERROR","..........error getting chassis Thermal resource from rackserver BMC: {}. rc: {}".format(chassisid,rc))
                return(19,False) # note: returning non-zero rc, will cause a 500 error from the frontend.
        else:
            self.rdr.logMsg("DEBUG","..........no Thermal resource in BMC")
            return(0,False) 

        # get the TemperatureSensors sub-resource and update the tempSensorsDb
        self.sysHwMonData=dict()
        self.sysHwMonData["Id"]={}
        if "Temperatures" in d:
            for sensor in d["Temperatures"]:
                if "MemberId" in sensor:
                    sensorId=sensor["MemberId"]
                    self.sysHwMonData["Id"][sensorId] = {}
                    self.sysHwMonData["Id"][sensorId]["Volatile"]=["ReadingCelsius"]
                    self.sysHwMonData["Id"][sensorId]["AddRelatedItems"]=["Chassis","System"]
                    for prop in sensor:
                        self.sysHwMonData["Id"][sensorId][prop]=sensor[prop]

        # set properties to point to tempSensorsDb first and update the resource Temp sensor DBs
        self.resDb=self.rdr.root.chassis.tempSensorsDb[chassisid]
        self.staticProperties=self.rdr.root.chassis.temperatureStaticProperties
        self.nonVolatileProperties=self.rdr.root.chassis.temperatureNonVolatileProperties

        rc, updatedResourceDb=self.aggrGenericUpdateResourceDbs(chassisid, curTime, lastDbUpdateTime )
        if rc is not 0:
            return(rc,updatedResourceDb)

        # get the Fans sub-resource and update the fansDb
        self.sysHwMonData=dict()
        self.sysHwMonData["Id"]={}
        self.sysHwMonData["RedundancyGroup"]={}
        if "Fans" in d:
            for sensor in d["Fans"]:
                if "MemberId" in sensor:
                    sensorId=sensor["MemberId"]
                    self.sysHwMonData["Id"][sensorId] = {}
                    self.sysHwMonData["Id"][sensorId]["Volatile"]=["Reading"]
                    self.sysHwMonData["Id"][sensorId]["AddRelatedItems"]=["Chassis","System"]
                    self.sysHwMonData["Id"][sensorId]["RedundancyGroup"]="0" # xg hardcoding one redun grp
                    for prop in sensor:
                        self.sysHwMonData["Id"][sensorId][prop]=sensor[prop]
        if "Redundancy" in d:
            for entry in d["Redundancy"]:
                if "MemberId" in entry:
                    redGrpId=entry["MemberId"]
                    self.sysHwMonData["RedundancyGroup"][redGrpId] = {}
                    for prop in entry:
                        self.sysHwMonData["RedundancyGroup"][redGrpId][prop]=entry[prop]

        # set properties to point to tempSensorsDb first and update the resource Temp sensor DBs
        self.resDb=self.rdr.root.chassis.fansDb[chassisid]
        self.resVolDb=self.rdr.root.chassis.fansVolatileDict[chassisid]
        self.staticProperties=self.rdr.root.chassis.fansStaticProperties
        self.nonVolatileProperties=self.rdr.root.chassis.fansNonVolatileProperties

        rc, updatedResourceDb=self.aggrGenericUpdateResourceDbs( chassisid, curTime, lastDbUpdateTime )

        return(rc,updatedResourceDb)



    # update all Power Databases:  voltagesDb, powerControlDb, powerSuppliesDb
    #    - used by aggregator
    #    - returns rc=0 if no error, non-zero if error,
    #    - returns updatedResourceDb (True/False) indicating if the resourceDb was updated
    def aggregatorUpdatePowerResources(self,chassisid, updateStaticProps, updateNonVols):
        # first use voltageSensorsDb to determine if Power resources have been recently updated
        self.resVolDb=self.rdr.root.chassis.voltageSensorsVolatileDict[chassisid]
        # call generic methods to update the DBs 
        rc,curTime,lastDbUpdateTime=self.genericChkIfRecentDbUpdate(self.resVolDb)
        # if we recently updated the resources, return rc=0 (no-error) w/o updating them again
        if( rc==1 ):
            return(0,False)

        # xg9 currently we dont support Power and Thermal on the MgtSwitch or aggregationManagerHost chassis
        if self.isRackServerChassis(chassisid) is not True:
            return(0,False)

        # if here, we need to update voltageSensorsDb, powerSuppliesDb, and powerControlDb
        # get the resource data from the bmc
        if chassisid in self.rdr.root.chassis.chassisDb:
            thisChasDb=self.rdr.root.chassis.chassisDb[chassisid]
        else:
            return(0,False)
        if "Netloc" in thisChasDb and "ChasUrl" in thisChasDb:
            bmcNetloc=thisChasDb["Netloc"]
            chasUrl=thisChasDb["ChasUrl"]
        else:
            return(17,False)

        # open Redfish transport to this bmc
        rft = BmcRedfishTransport(rhost=bmcNetloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug,
                                      credentialsPath=self.rdr.bmcCredentialsPath)
        # if we have never stored the thermal or Power Url, read the chassis now and store them
        if "PowerUrl" in thisChasDb:
            powerUrl=thisChasDb["PowerUrl"]
        else:
            rc,r,j,d = rft.rfSendRecvRequest("GET", chasUrl )
            if rc is not 0:
                self.rdr.logMsg("ERROR","..........error getting chassis entry from rackserver BMC: {}. rc: {}".format(chassisid,rc))
                return(19,False) # note: returning non-zero rc, will cause a 500 error from the frontend.
                # we should handle case where no power or thermal resource and return 404?
            # save both thermal and power URLs
            thermalUrl=None
            powerUrl=None
            if "Thermal" in d and "@odata.id" in d["Thermal"]:
                thermalUrl=d["Thermal"]["@odata.id"]
            if "Power" in d and "@odata.id" in d["Power"]:
                powerUrl=d["Power"]["@odata.id"]
            thisChasDb["PowerUrl"] = powerUrl
            if "ThermalUrl" not in thisChasDb:  # update powerUrl if its not already there
                thisChasDb["ThermalUrl"] = thermalUrl
        # now we have the thermalUrl, get the response from bmc
        if powerUrl is not None:
            rc,r,j,d = rft.rfSendRecvRequest("GET", powerUrl )
            if rc is not 0:
                self.rdr.logMsg("ERROR","..........error getting chassis Power resource from rackserver BMC: {}. rc: {}".format(chassisid,rc))
                return(19,False) # note: returning non-zero rc, will cause a 500 error from the frontend.
        else:
            self.rdr.logMsg("DEBUG","..........no Power resource in BMC")
            return(0,False) 

        # get the Voltages sub-resource and update the voltageSensorsDb
        self.sysHwMonData=dict()
        self.sysHwMonData["Id"]={}
        if "Voltages" in d:
            for sensor in d["Voltages"]:
                if "MemberId" in sensor:
                    sensorId=sensor["MemberId"]
                    self.sysHwMonData["Id"][sensorId] = {}
                    self.sysHwMonData["Id"][sensorId]["Volatile"]=["ReadingVolts"]
                    self.sysHwMonData["Id"][sensorId]["AddRelatedItems"]=["Chassis","System"]
                    for prop in sensor:
                        self.sysHwMonData["Id"][sensorId][prop]=sensor[prop]

        # set properties to point to voltageSensorsDb first and update the resource DBs
        self.resDb=self.rdr.root.chassis.voltageSensorsDb[chassisid]
        self.staticProperties=self.rdr.root.chassis.voltagesStaticProperties
        self.nonVolatileProperties=self.rdr.root.chassis.voltagesNonVolatileProperties

        rc, updatedResourceDb=self.aggrGenericUpdateResourceDbs(chassisid, curTime, lastDbUpdateTime )
        if rc is not 0:
            return(rc,updatedResourceDb)

        # get the PowerSupplies sub-resource and update the fansDb
        self.sysHwMonData=dict()
        self.sysHwMonData["Id"]={}
        self.sysHwMonData["RedundancyGroup"]={}
        if "PowerSupplies" in d:
            for sensor in d["PowerSupplies"]:
                if "MemberId" in sensor:
                    sensorId=sensor["MemberId"]
                    self.sysHwMonData["Id"][sensorId] = {}
                    self.sysHwMonData["Id"][sensorId]["Volatile"]=["LineInputVoltage","LastPowerOutputWatts"]
                    self.sysHwMonData["Id"][sensorId]["AddRelatedItems"]=["Chassis","System"]
                    self.sysHwMonData["Id"][sensorId]["RedundancyGroup"]="0" # xg hardcoding one redun grp
                    for prop in sensor:
                        self.sysHwMonData["Id"][sensorId][prop]=sensor[prop]
        if "Redundancy" in d:
            for entry in d["Redundancy"]:
                if "MemberId" in entry:
                    redGrpId=entry["MemberId"]
                    self.sysHwMonData["RedundancyGroup"][redGrpId] = {}
                    for prop in entry:
                        self.sysHwMonData["RedundancyGroup"][redGrpId][prop]=entry[prop]

        # set properties to point to powerSuppliesDb 
        self.resDb=self.rdr.root.chassis.powerSuppliesDb[chassisid]
        self.resVolDb=self.rdr.root.chassis.powerSuppliesVolatileDict[chassisid]
        self.staticProperties=self.rdr.root.chassis.psusStaticProperties
        self.nonVolatileProperties=self.rdr.root.chassis.psusNonVolatileProperties

        rc, updatedResourceDb=self.aggrGenericUpdateResourceDbs( chassisid, curTime, lastDbUpdateTime )
        if rc is not 0:
            return(rc,updatedResourceDb)


        # update Power Control
        self.sysHwMonData=dict()
        self.sysHwMonData["Id"]={}
        if "PowerControl" in d:
            for sensor in d["PowerControl"]:
                if "MemberId" in sensor:
                    sensorId=sensor["MemberId"]
                    self.sysHwMonData["Id"][sensorId] = {}
                    self.sysHwMonData["Id"][sensorId]["Volatile"]=["PowerConsumedWatts"]
                    self.sysHwMonData["Id"][sensorId]["AddRelatedItems"]=["Chassis","System"]
                    for prop in sensor:
                        self.sysHwMonData["Id"][sensorId][prop]=sensor[prop]

        # set properties to point to powerControl DBs 
        self.resDb=self.rdr.root.chassis.powerControlDb[chassisid]
        self.resVolDb=self.rdr.root.chassis.powerControlVolatileDict[chassisid]
        self.staticProperties=self.rdr.root.chassis.powerControlStaticProperties
        self.nonVolatileProperties=[]

        rc, updatedResourceDb=self.aggrGenericUpdateResourceDbs( chassisid, curTime, lastDbUpdateTime )


        return(rc,updatedResourceDb)
        #xg999777
        
    # if redisHash is None, then the sysHwMonData is taken from self.sysHwMonData
    def aggrGenericUpdateResourceDbs(self, chassisid, curTime, lastDbUpdateTime ):
        updatedResourceDb=True
        updateStaticProps = True
        updateNonVols = True

        # use the sysHwMonData stored under backendChassis self class
        sysHwMonData=self.sysHwMonData

        # save front-end database update timestamp
        self.resVolDb["UpdateTime"] = curTime

        # make sure the frontend databases are built-out
        if "Id" in sysHwMonData:
            if "Id" not in self.resDb:
                self.resDb["Id"]={}
            if "Id" not in self.resVolDb:
                self.resVolDb["Id"]={}

            for resId in sysHwMonData["Id"]:
                if resId not in self.resDb["Id"]:
                    self.resDb["Id"][resId]={}
                if resId not in self.resVolDb["Id"]:
                    self.resVolDb["Id"][resId]={}
        else:
            return(8,False)

        # update Static data if flag is set to do so.   
        # this is generally done once to pickup static data discovered by backend
        if updateStaticProps is True:
            for resId in sysHwMonData["Id"]:
                for prop in self.staticProperties:
                    if prop in sysHwMonData["Id"][resId]:
                        self.resDb["Id"][resId][prop]=sysHwMonData["Id"][resId][prop]
                        updatedResourceDb=True

        # update Volatile Properties
        for resId in sysHwMonData["Id"]:
            if "Volatile" in sysHwMonData["Id"][resId]:
                for prop in sysHwMonData["Id"][resId]["Volatile"]:
                    self.resVolDb["Id"][resId][prop]=sysHwMonData["Id"][resId][prop]

        # update the volatile status properties
        for resId in sysHwMonData["Id"]:
            if "Status" in sysHwMonData["Id"][resId]:
                for prop in sysHwMonData["Id"][resId]["Status"]:
                    if "Status" not in self.resVolDb["Id"][resId]:
                        self.resVolDb["Id"][resId]["Status"]={}
                    self.resVolDb["Id"][resId]["Status"][prop]=sysHwMonData["Id"][resId]["Status"][prop]

        # update NonVolatile Properties
        if updateNonVols is True:
            for resId in sysHwMonData["Id"]:
                for prop in self.nonVolatileProperties:
                    if prop in sysHwMonData["Id"][resId]:
                        self.resDb["Id"][resId][prop]=sysHwMonData["Id"][resId][prop]
                        updatedResourceDb=True

        # other reddrum props
        redDrumNonVolatiles=["Volatile","AddRelatedItems","RedundancyGroup"]
        for resId in sysHwMonData["Id"]:
            for prop in redDrumNonVolatiles:
                if prop in sysHwMonData["Id"][resId]:
                    self.resDb["Id"][resId][prop]=sysHwMonData["Id"][resId][prop]
                    updatedResourceDb=True

        rc=0     # 0=ok
        return(rc,updatedResourceDb)


    # the std dss9000 update
    def genericUpdateResourceDbs(self, chassisid, curTime, lastDbUpdateTime, redisHash, 
                                   updateStaticProps=False, updateNonVols=True ):

        updatedResourceDb=False

        # if this is a traditional Dss9000 update from Redis, get it that way
        sysHwMonData=dict()
        #get sysHwMonData from the RedisDB
        # sysHwMonData={"Prop": "VAL", ..."Status": {...}, 
        #                "updateTime": "2017-06-13 16:12:02.729333"
        #                "Id": {
        #                    "0": { .... },
        #                    "1": { .... },
        #                     ...
        #              }  }
        # Read the Rack chassis resources from the Redis Database using the Redis Transport to get rackPower
        #rc,msg,d = self.rdt.getHashDbEntry(redisHash, chassisid)
        #if rc == 0 and isinstance(d,dict):
        #    sysHwMonData = copy.deepcopy(d)
        #else:
        #    self.rdr.logMsg("ERROR","Chas Backend: Error getting data from Redis hash: {} chassisid: {}".format(redisHash,rc))
        pass


        # check if  HWMonUpdate preceeds the last FrontEnd cache update 
        # if front-end vol cache is later, then we patched data and HW monitor has not yet caught up
        hwMonUpdateTime=None
        if "updateTime" in sysHwMonData:
            hwMonUpdateTime=datetime.datetime.strptime(str(sysHwMonData["updateTime"]), "%Y-%m-%d %H:%M:%S.%f")
            if lastDbUpdateTime is not None:
                if ( hwMonUpdateTime < lastDbUpdateTime ):
                    self.rdr.logMsg("DEBUG","----------Chas Backend: DBs were updated after HWMonitors last updated Redis Db-cont w/o updating DB. Hash: {}, chassid: {}".format(redisHash,chassisid))
                    return(0,False)

        # save front-end database update timestamp
        self.resVolDb["UpdateTime"] = curTime

        # update Static data if flag is set to do so.   
        # this is generally done once to pickup static data discovered by backend
        if updateStaticProps is True:
            if ("Id" in self.resDb) and ("Id" in sysHwMonData):
                for resId in self.resDb["Id"]:
                    if resId in sysHwMonData["Id"]:
                        for prop in self.staticProperties:
                            if (prop in self.resDb["Id"][resId]) and (prop in sysHwMonData["Id"][resId]):
                                if self.resDb["Id"][resId][prop] != sysHwMonData["Id"][resId][prop]:
                                    self.resDb["Id"][resId][prop]=sysHwMonData["Id"][resId][prop]
                                    updatedResourceDb=True

        # update Volatile Properties
        if ("Id" in self.resDb) and ("Id" in sysHwMonData):
            for resId in self.resDb["Id"]:
                if resId in sysHwMonData["Id"]:
                    if "Volatile" in self.resDb["Id"][resId]:
                        for prop in self.resDb["Id"][resId]["Volatile"]:
                            if prop in sysHwMonData["Id"][resId]:
                                if "Id" not in self.resVolDb:
                                    self.resVolDb["Id"]={}
                                if resId not in self.resVolDb["Id"]:
                                    self.resVolDb["Id"][resId]={}
                                self.resVolDb["Id"][resId][prop]=sysHwMonData["Id"][resId][prop]

        # update the volatile status properties
        if ("Id" in self.resDb) and ("Id" in sysHwMonData):
            for resId in self.resDb["Id"]:
                if resId in sysHwMonData["Id"]:
                    if ("Status" in self.resDb["Id"][resId]) and ("Status" in sysHwMonData["Id"][resId]):
                        for prop in self.resDb["Id"][resId]["Status"]:
                            if prop in sysHwMonData["Id"][resId]["Status"]:
                                if "Id" not in self.resVolDb:
                                    self.resVolDb["Id"]={}
                                if resId not in self.resVolDb["Id"]:
                                    self.resVolDb["Id"][resId]={}
                                if "Status" not in self.resVolDb["Id"][resId]:
                                    self.resVolDb["Id"][resId]["Status"]={}
                                self.resVolDb["Id"][resId]["Status"][prop]=sysHwMonData["Id"][resId]["Status"][prop]

        # update NonVolatile Properties
        if updateNonVols is True:
            if ("Id" in self.resDb) and ("Id" in sysHwMonData):
                for resId in self.resDb["Id"]:
                    if resId in sysHwMonData["Id"]:
                        for prop in self.nonVolatileProperties:
                            if (prop in self.resDb["Id"][resId]) and (prop in sysHwMonData["Id"][resId]):
                                if self.resDb["Id"][resId][prop] != sysHwMonData["Id"][resId][prop]:
                                    self.resDb["Id"][resId][prop]=sysHwMonData["Id"][resId][prop]
                                    updatedResourceDb=True

        rc=0     # 0=ok
        return(rc,updatedResourceDb)


    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx


