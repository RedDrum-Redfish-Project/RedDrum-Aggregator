
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
            # get data from BMC
            if "Netloc" in resDb and "MgrUrl" in resDb:
                bmcNetloc=resDb["Netloc"]
                mgrUrl=resDb["MgrUrl"]
            else:
                return(17,False)
            # open Redfish transport to this bmc
            rft = BmcRedfishTransport(rhost=bmcNetloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug,
                                          credentialsPath=self.rdr.bmcCredentialsPath)

            # check if we already have the URI for the manager networkProtocols
            if "NetworkProtocolUri" in resDb:
                networkProtocolUri=resDb["NetworkProtocolUri"]
            else:
                # we need to query the manager to get the NetworkProtocol URI
                self.rdr.logMsg("DEBUG","--------BACKEND NetworkProtocolUri not in database. mgrid={}".format(mgrid))
                # send request to the manager
                rc,r,j,dmgr = rft.rfSendRecvRequest("GET", mgrUrl )
                if rc is not 0:
                    self.rdr.logMsg("ERROR","..........error getting Manager base resource. rc: {}".format(rc))
                    return(18) # note: returning non-zero rc, will cause a 500 error from the frontend.
                if "NetworkProtocol" in dmgr and "@odata.id" in dmgr["NetworkProtocol"]:
                    networkProtocolUri=dmgr["NetworkProtocol"]["@odata.id"]
                    resDb["NetworkProtocolUri"]=networkProtocolUri
                else:
                    self.rdr.logMsg("INFO","..........No NetworkProtocol property in Manager Entry: {}".format(rc))
                    return(0) # note: returning non-zero rc, will cause a 500 error from the frontend.

            # send request to the rackserver  BMC to get the Network Protocol resource
            rc,r,j,dnetwkProtos = rft.rfSendRecvRequest("GET", networkProtocolUri )
            if rc is not 0:
                self.rdr.logMsg("ERROR","..........error getting NetworkProtocol resource from rackserver BMC: {}. rc: {}".format(mgrid,rc))
                return(19,False) # note: returning non-zero rc, will cause a 500 error from the frontend.

            # save front-end database update timestamp
            #resVolDb["UpdateTime"] = curTime
            #updateStaticProps=True
            #updateNonVols = True

            # get the properties
            networkProtocolProperties=["Name","HTTP","HTTPS","SSH", "NTP","HostName","FQDN","Telnet","Status","SNMP",
                                       "VirtualMedia","SSDP","IPMI","KVMIP"]
            if "NetworkProtocols" not in resDb:
                resDb["NetworkProtocols"]={}

            for prop in networkProtocolProperties:
                if prop in dnetwkProtos:
                    resDb["NetworkProtocols"][prop] = dnetwkProtos[prop]

            print("#EE#######################")
            print("networkProtocols:   {}".format(dnetwkProtos))
            print("#EE#######################")
            print("KVMIP:   {}".format(dnetwkProtos["KVMIP"]))

            # FINISH:  xg99
            return(0)

        else:
            # pass - not an aggregation manager here
            return(0)


    # update EthernetInterface Info
    def updateManagerEthernetEnterfacesDbFromBackend(self, mgrid, noCache=False, ethid=None):
        mgrDb=self.rdr.root.managers.managersDb
        resDb=self.rdr.root.managers.managersDb[mgrid]
        mgrInfoCacheTimeout=self.rdr.processorInfoCacheTimeout  #xg99 need a mgrInfoCacheTimeout
        maxCollectionEntries=8

        # get time 
        curTime=datetime.datetime.utcnow()
        lastMgrEtherUpdateTime=None

        # if using processor cache is enabled/selected, check if cache exists
        if (mgrInfoCacheTimeout > 0) and (noCache is False):
            if( (mgrid in mgrDb) and ("Id" in  mgrDb[mgrid]) and
                ("EthernetUpdateTime" in mgrDb[mgrid]) and (mgrDb[mgrid]["EthernetUpdateTime"] is not None) ):
                # if we have a mgrid entry in procDb with an "Id" resource, then we have a proc cache
                # (the sys monitor or hotplug code will clear the db for this sysid if it is out of date
                #  by removing the entry or setting UpdateTime to None)

                #check if the cache timeout has occured
                # note lastProcDbUpdateTime in string form: "2017-06-13 16:12:02.729333"
                lastProcDbUpdateTime=datetime.datetime.strptime(str(procDb[sysid]["UpdateTime"]), "%Y-%m-%d %H:%M:%S.%f")
                # if currentTime - lastUpdateTime is less than rdr.procInfoCacheTimeout, return. no update required
                #if ( (curTime - lastProcDbUpdateTime) < datetime.timedelta(seconds=1)):
                if ( (curTime - lastMgrEtherUpdateTime) < datetime.timedelta(seconds=procInfoCacheTimeout)):
                    self.rdr.logMsg("DEBUG","---------BACKEND ManagerInfo: cache not timed-out. Return w/o updating Db")
                    return(0)

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
            #fixIdracProperties=["ProcessorArchitecture", "InstructionSet" ]
            managerEthernetProperties=["Name", "UefiDevicePath", "Status", "InterfaceEnabled", "PermanentMACAddress", 
                "MACAddress", "SpeedMbps", "AutoNeg", "FullDuplex", "MTUSize", "HostName", "FQDN", 
                "MaxIPv6StaticAddresses", "VLAN", "IPv4Addresses", "IPv6Addresses", "IPv6StaticAddresses", 
                "IPv6AddressPolicyTable","IPv6DefaultGateway","NameServers", "VLANs"]

            # get data from BMC
            if "Netloc" in resDb and "MgrUrl" in resDb:
                bmcNetloc=resDb["Netloc"]
                mgrUrl=resDb["MgrUrl"]
            else:
                return(17,False)
            # open Redfish transport to this bmc
            rft = BmcRedfishTransport(rhost=bmcNetloc, isSimulator=self.rdr.backend.isSimulator, debug=self.debug,
                                          credentialsPath=self.rdr.bmcCredentialsPath)

            # check if we already have the URI for the Managers EthernetInterfaces collection 
            if "EthernetInterfacesUri" in resDb:
                ethernetInterfacesUri=resDb["EthernetInterfacesUri"]
            else:
                # we need to query the manager to get the EthernetInterfaces Collection URI
                self.rdr.logMsg("DEBUG","--------BACKEND EthernetInterfacesUri not in database. mgrid={}".format(mgrid))
                # send request to the manager
                rc,r,j,dmgr = rft.rfSendRecvRequest("GET", mgrUrl )
                if rc is not 0:
                    self.rdr.logMsg("ERROR","..........error getting Manager base resource. rc: {}".format(rc))
                    return(18) # note: returning non-zero rc, will cause a 500 error from the frontend.
                if "EthernetInterfaces" in dmgr and "@odata.id" in dmgr["EthernetInterfaces"]:
                    ethernetInterfacesUri=dmgr["EthernetInterfaces"]["@odata.id"]
                    resDb["EthernetInterfacesUri"]=ethernetInterfacesUri
                else:
                    self.rdr.logMsg("INFO","..........No EthernetInterfaces property in Manager Entry: {}".format(rc))
                    return(0) # note: returning non-zero rc, will cause a 500 error from the frontend.

            # update the base level ethernetInterfaces Db entry 
            if "EthernetInterfacesUri" in resDb:   # if we have an ethernet interfaces collection at all 
                resDb["EthernetInterfaces"]={}
            if "EthernetUpdateTime" not in resDb:
                resDb["EthernetUpdateTime"]=None

            # Get the Manager Ethernet Collection from the Node
            #self.rdr.logMsg("DEBUG","mgrUri: {}".format(ethernetInterfacesUri))

            rc,r,j,dCollection=rft.rfSendRecvRequest("GET",ethernetInterfacesUri)
            if( (rc== 0) and (r.status_code==200) and (j is True)):
                # walk the collection members and read each member to get its Id and data
                if "Members" in dCollection and (len(dCollection["Members"])< maxCollectionEntries  ):
                    for member in dCollection["Members"]:
                        # extract the Uri
                        memberUri = member["@odata.id"]
                        rc,r,j,d=rft.rfSendRecvRequest("GET",memberUri)
                        if( rc== 0 ):
                            # save the entry
                            memberId=d["Id"]
                            if any( i in memberId for i in "#" ):
                                memberId = memberId.replace("#","-")
                            if memberId not in resDb["EthernetInterfaces"]:
                                resDb["EthernetInterfaces"][memberId]={}
                            for prop in managerEthernetProperties:
                                if prop in d:
                                    resDb["EthernetInterfaces"][memberId][prop] = d[prop]

                    # add update time
                    resDb["EthernetUpdateTime"]=curTime
                    return(0)
                else:
                    self.rdr.logMsg("ERROR","--------BACKEND Get Mgr Ethernet Collecton bad response, mgrid={}".format(mgrid))
                    return(0)
            else:
                self.rdr.logMsg("WARNING","--------BACKEND Get Mgr Collecton returned error rc={}, mgrid={}".format(rc,mgrid))
                return(0)

            return(0)

        else:
            # pass - not an aggregation manager here
            return(0)
    
