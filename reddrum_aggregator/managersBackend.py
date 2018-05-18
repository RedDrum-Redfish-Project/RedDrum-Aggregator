
# Copyright Notice:
#    Copyright 2018 Dell, Inc. All rights reserved.
#    License: BSD License.  For full license text see link: https://github.com/RedDrum-Redfish-Project/RedDrum-OpenBMC/LICENSE.txt

from .redfishTransports import BmcRedfishTransport
from .aggrMgrLinuxInterfaces import RdAggrMgrLinuxInterfaces
import time,json
import datetime
import os
#import subprocess
#from subprocess import Popen,PIPE

# Aggregator managersBackend resources
#
class  RdManagersBackend():
    # class for backend managers resource APIs
    def __init__(self,rdr):
        self.rdr=rdr
        self.version=1
        self.debug=False
        self.linuxApis=RdAggrMgrLinuxInterfaces(rdr)

    # update resourceDb and volatileDict
    def updateResourceDbs(self,managerid, updateStaticProps=False, updateNonVols=True ):
        self.rdr.logMsg("DEBUG","--------BACKEND updateResourceDBs. updateStaticProps={}".format(updateStaticProps))
        self.supportAggregationManager = True
        
        # set local properties to point to this managerid Db and VolDict, ...
        resDb=self.rdr.root.managers.managersDb[managerid]
        resVolDb=self.rdr.root.managers.managersVolatileDict[managerid]
        staticProperties=self.rdr.root.managers.staticProperties
        nonVolatileProperties=self.rdr.root.managers.nonVolatileProperties
        oemDellG5NonVolatileProperties=self.rdr.root.managers.oemDellG5NonVolatileProps
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
                self.rdr.logMsg("DEBUG","----------MgrBackend: time < min DbUpdateTime.  Returning w/o updating DBs")
                return(0,False)

        # STAGE1 of UPDATE:  get the sysHwMonData for the specific chassis resource
        sysHwMonData=dict()

        #    Volatile Data:  
        #        IndicatorLED         - not used in g5
        #        PowerState           - not used in g5
        #        DateTime             - not used in g5 except RM
        #        DateTimeLocalOffset  - not used in g5 except RM
        #        Status={"State": None, "Health": None}
        #    nonVolatile:
        #        FirmwareVersion
        #        OemDell/ LastUpdateStatus
        #        OemDell/ SafeBoot
        #        OemDell/ OpenLookupTableVersion   --bc

        if self.isManagerTheRackAggregationManager( managerid) is True:
            # update the db for the aggregation manager
            # xgTODO
            return(0,False)
        if self.isManagerRackServerManager( managerid) is not True:
            # pass not an aggregation manager here
            return(0,False)

        # if here, assume the manager is a bmc in a RackServer
        # get data from BMC
        if "Netloc" in resDb and "MgrUrl" in resDb:
            bmcNetloc=resDb["Netloc"]
            mgrUrl=resDb["MgrUrl"]
        else:
            return(17,False)

        # open Redfish transport to this bmc
        rft = BmcRedfishTransport(rhost=bmcNetloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug,
                                          credentialsPath=self.rdr.bmcCredentialsPath)
        # send request to the rackserver  BMC
        rc,r,j,sysHwMonData = rft.rfSendRecvRequest("GET", mgrUrl )
        if rc is not 0:
            self.rdr.logMsg("ERROR","..........error getting BMC entry from rackserver BMC: {}. rc: {}".format(chassisid,rc))
            return(19,False) # note: returning non-zero rc, will cause a 500 error from the frontend.

        # save front-end database update timestamp
        resVolDb["UpdateTime"] = curTime
        updateStaticProps=True
        updateNonVols = True

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


        # update the Dell Oem G5 nonVolatile properties
        if updateNonVols is True:
            for prop in oemDellG5NonVolatileProperties:
                if ("OemDellG5MCMgrInfo" in resDb) and (prop in resDb["OemDellG5MCMgrInfo"]):
                    if ("Oem" in sysHwMonData) and ( "Dell_G5MC" in sysHwMonData["Oem"]):
                        if prop in sysHwMonData["Oem"]["Dell_G5MC"]:
                            if resDb["OemDellG5MCMgrInfo"][prop] != sysHwMonData["Oem"]["Dell_G5MC"][prop]:
                                resDb["OemDellG5MCMgrInfo"][prop]=sysHwMonData["Oem"]["Dell_G5MC"][prop]
                                updatedResourceDb=True
        # update other properties
        aggrMgrOtherProps=["SerialConsole","GraphicalConsole","CommandShell"]
        for prop in aggrMgrOtherProps:
            if prop in sysHwMonData:
                resDb[prop]=sysHwMonData[prop]
                updatedResourceDb=True

        rc=0     # 0=ok
        return(rc,updatedResourceDb)



    # check if this manager is the rack aggregation manager
    #    -returns True or False
    def isManagerTheRackAggregationManager(self, managerid):
        if self.supportAggregationManager is not True:
            return(False)
        # return false if the manager does not exist
        if not managerid in self.rdr.root.managers.managersDb:
            return(0,False)
        # get the manager entry
        thisMgrDb=self.rdr.root.managers.managersDb[managerid]
        # if manager is the rack aggregation manager return true
        if "IsAggregatorManager" in thisMgrDb and thisMgrDb["IsAggregatorManager"] is True:
            return(True)
        else:
            return(False)

    # check if this manager is a rackServer manager
    #    -returns True or False
    def isManagerRackServerManager(self, managerid):
        if self.supportAggregationManager is not True:
            return(False)
        # return false if the manager does not exist
        if not managerid in self.rdr.root.managers.managersDb:
            return(0,False)
        # get the manager entry
        thisMgrDb=self.rdr.root.managers.managersDb[managerid]
        # if manager is the rack aggregation manager return true
        if "IsRackServerManager" in thisMgrDb and thisMgrDb["IsRackServerManager"] is True:
            return(True)
        else:
            return(False)

    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # DO action:  "Reset", "Hard,
    def doManagerReset(self,managerid,resetType):
        self.rdr.logMsg("DEBUG","--------BACKEND managerReset. resetType={}".format(resetType))
        #rc=self.dbus.resetObmcMgr(resetType)
        rc=0
        return(rc)


    # DO Patch to Manager  (DateTime, DateTimeOffset)
    def doPatch(self, managerid, patchData):
        # the front-end has already validated that the patchData and managerid is ok
        # so just send the request here
        self.rdr.logMsg("DEBUG","--------BACKEND Patch manager: {} data. patchData={}".format(managerid,patchData))

        # for OpenBMC, there are no base manager patches that go to the backend.
        #              DateTime and DateTimeOffset are handled in the frontend
        #              Nothing to do here
        return(0)


    # update NetworkProtocolsDb Info
    def updateManagerNetworkProtocolsDbFromBackend(self, mgrid, noCache=False):
        # set local properties to point to this managerid Db and VolDict, ...
        resDb=self.rdr.root.managers.managersDb[mgrid]

        if self.isManagerTheRackAggregationManager( mgrid) is True:
            backendSupportedProtocols = ["HTTP","HTTPS","SSH"]
            if "NetworkProtocols" in resDb:
                rc,mgrNetwkProtoInfo = self.linuxApis.getObmcNetworkProtocolInfo()
                print("EEEEExg99: rc: {},   mnp: {}".format(rc,mgrNetwkProtoInfo))
                if rc==0:
                    for proto in backendSupportedProtocols:
                        if proto in resDb["NetworkProtocols"] and proto in mgrNetwkProtoInfo:
                            resDb["NetworkProtocols"][proto]["ProtocolEnabled"] = mgrNetwkProtoInfo[proto]["ProtocolEnabled"]
                    if "HostName" in mgrNetwkProtoInfo:
                            resDb["NetworkProtocols"]["HostName"] = mgrNetwkProtoInfo["HostName"]
                    if "FQDN" in mgrNetwkProtoInfo:
                            resDb["NetworkProtocols"]["FQDN"] = mgrNetwkProtoInfo["FQDN"]
                else:
                    return(9)
            return(0)

        elif self.isManagerRackServerManager( mgrid) is True:
            # this is a rackServer BMC manager.
            # FINISH:  xg99
            return(0)

        else:
            # pass - not an aggregation manager here
            return(0)


    # update EthernetInterface Info
    def updateManagerEthernetEnterfacesDbFromBackend(self, mgrid, noCache=False, ethid=None):
        resDb=self.rdr.root.managers.managersDb[mgrid]

        if self.isManagerTheRackAggregationManager( mgrid) is True:
            if "EthernetInterfaces" in resDb:
                if (ethid is not None) and (ethid in resDb["EthernetInterfaces"]):
                    ethResDb = resDb["EthernetInterfaces"][ethid]
    
                    # update IPv4Address info and MACAddress info
                    rc,ipInfo=self.linuxApis.getObmcIpInfo(ethid)
                    ipProperties = ["Name","MACAddress","PermanentMACAddress","InterfaceEnabled","LinkStatus",
                                    "SpeedMbps","HostName","FQDN","AutoNeg", "IPv4Addresses" ]
                    for ipProp in ipProperties:
                        if ipProp in ipInfo:
                            ethResDb[ipProp] = ipInfo[ipProp]
            return(0)

        elif self.isManagerRackServerManager( mgrid) is True:
            # this is a rackServer BMC manager.
            # FINISH:  xg99
            return(0)

        else:
            # pass - not an aggregation manager here
            return(0)
    
