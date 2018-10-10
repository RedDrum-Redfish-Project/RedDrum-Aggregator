from .aggregatorConfig import RfaConfig
from .aggregatorUtils  import RfaBackendUtils
from .mgrLinuxInterfaces import RdMgrLinuxInterfaces
import json
import datetime
import pytz

class RfaAggregatorManagerResources():
    def __init__(self,rdr ):
        self.rfaCfg=RfaConfig()  # aggregatorConfig data
        self.rfaUtils=RfaBackendUtils(rdr)  
        self.rdr=rdr
        self.linuxApis=RdMgrLinuxInterfaces(rdr)
        self.managerResource = None    # the resource data returned in responses
        self.managerResourceMgt = None # additional management data for the resource
        self.networkProtocolResource = None
        self.ethernetInterfaceCollectionlResource = None
        self.ethernetInterfaceResource = None

    def addRfaAggregatorManagerResource(self):
        resId = self.rfaCfg.aggregatorMgrId
        odataType,odataContext = self.rfaUtils.genOdataTypeContext("Manager","v1_4_0","Manager")
        res=dict()
        res["Id"]=resId
        res["@odata.id"]= "/redfish/v1/Managers/" + resId
        res["@odata.type"]=odataType
        res["@odata.context"]=odataContext

        res["Name"]="RedDrum Aggregator Manager"
        res["Description"]="The top-level Redfish Aggregator Manager Resource"
        res["ManagerType"]="EnclosureManager"
        res["FirmwareVersion"]="v2.0"
        res["Status"]={"State": "Enabled", "Health": "OK" }
        #res["SerialConsole"]={"ServiceEnabled": True, "MaxConcurrentSessions": 100, "ConnectTypesSupported": ["SSH"]}
        #resp["CommandShell"]={"ServiceEnabled": True, "MaxConcurrentSessions": 100, "ConnectTypesSupported": ["SSH"]}
        res["DateTime"]   = None
        res["DateTimeLocalOffset"]  = None 
        res["UUID"]=None

        # Actions
        target = "/redfish/v1/Managers/" + resId + "/Actions/Manager.Reset"
        allowableValues = ["GracefulRestart","ForceRestart"]     # xg99 we need to support this
        res["Actions"]= {}
        res["Actions"]["#Manager.Reset"] = {}
        res["Actions"]["#Manager.Reset"]["target"] = target
        res["Actions"]["#Manager.Reset"]["ResetType@Redfish.AllowableValues"] = allowableValues

        # static links 
        res["Links"] = {}
        if self.rfaCfg.redfishAggregatorIsInsideSwitch is True and self.rfaCfg.includeLocalMgtSwitchChassis is True:
            res["Links"]["ManagerInChassis"]={"@odata.id": "/redfish/v1/Chassis/" + self.rfaCfg.mgtSwitchChassisId }
        elif self.rfaCfg.includeLocalAggregatorHostChassis is True:
            res["Links"]["ManagerInChassis"]={"@odata.id": "/redfish/v1/Chassis/" + self.rfaCfg.aggregatorHostChassisId }
        elif self.rfaCfg.includeLocalRackEnclosureChassis is True:
            res["Links"]["ManagerInChassis"]={"@odata.id": "/redfish/v1/Chassis/" + self.rfaCfg.rackEnclosureChassisId }
        res["Links"]["ManagerForServers"]=[]
        res["Links"]["ManagerForChassis"]=[]

        # Add Management Props that are not returned in resource
        resMgt=dict()
        resMgt["IsAggregatorManager"]=True
        resMgt["Netloc"]="127.0.0.1"
        resMgt["GetDateTimeFromOS"]=True
        resMgt["GetUuidFromServiceRoot"]=True
        resMgt["GetServiceEntryPointUuidFrom"]="ServiceRoot"   # ServiceRoot | UUID 
        resMgt["Patchable"]=["DateTime", "DateTimeLocalOffset"]   # Recommended in BaseServerProfile  xg need to support
        resMgt["Stored"]=["DateTimeLocalOffset"]   # Recommended in BaseServerProfile  xg need to support
        resMgt["AddOemPropertiesDellESI"] = False
        resMgt["AddOemPropertiesRackScaleLocation"]=self.rfaCfg.includeRackScaleOemProperties

        # update the database with the stored patch data 
        rc,storedPatchData = self.rfaUtils.readPatchData("AggregatorManagerDb.json"  )
        if rc is 0 and storedPatchData is not None:
            for prop in resMgt["Stored"]:
                if prop in storedPatchData:
                    res[prop]= storedPatchData[prop]

        # if no patchDataStore, then create one from defaults now
        if rc is 9 and storedPatchData is None: 
            storeData = {}
            for prop in resMgt["Stored"]:
                storeData[prop] = res[prop]
            rc = self.rfaUtils.savePatchData( "AggregatorManagerDb.json", storeData )

        # create a NetworkProtocol Resource 
        rc, networkProtocolRef = self.addRfaAggregatorManagerNetworkProtocol(resId)
        if rc is 0:
            res["NetworkProtocol"] = networkProtocolRef 

        # create a EthernetInterfaces Resource 
        rc, ethernetInterfacesRef = self.addRfaAggregatorManagerEthernetInterfaces(resId)
        if rc is 0:
            res["EthernetInterfaces"] = ethernetInterfacesRef

        self.managerResource = res
        self.managerResourceMgt = resMgt

        # register the URI with the managers UriTable: register the subpath under /redfish/v1/Managers/
        rc = self.rdr.backend.managers.registerUriPath( resId, self.managerResource,
            Get=self.rfaGetAggregatorManagerResource, Patch=self.rfaPatchAggregatorManagerResource )

        return(0)


    def addRfaAggregatorManagerNetworkProtocol(self,mgrId):
        resId = "NetworkProtocol"
        odataType,odataContext = self.rfaUtils.genOdataTypeContext("NetworkProtocol","v1_4_0","NetworkProtocol")  #xg99
        res = dict()
        res["Id"]=resId
        subPath = mgrId + "/" + resId
        odataid = "/redfish/v1/Managers/" + subPath
        res["@odata.id"]= odataid
        res["@odata.type"]=odataType
        res["@odata.context"]=odataContext
        res["Name"] =  "Aggregation Manager Network Protocols"
        res["Description"] =  "Aggregation Manager Network Protocols"
        # set default values
        res["HTTP"] =  {"Port": 80, "ProtocolEnabled":  None}
        res["HTTPS"] = {"Port": 443,"ProtocolEnabled": None }
        res["SSH"] =   {"Port": 22, "ProtocolEnabled": None }
        #res["NTP"] =   {} 
        res["HostName"] = ""
        res["FQDN"] = ""
        res["Status"] = {"State": "Enabled", "Health": "OK"}
        networkProtocolRef = {"@odata.id":  odataid }
        self.networkProtocolResource = res
        # register the URI with the managers UriTable: register the subpath under /redfish/v1/Managers/
        rc = self.rdr.backend.managers.registerUriPath( subPath, self.networkProtocolResource,
            Get=self.rfaGetAggregatorManagerNetworkProtocol )
        return(0,networkProtocolRef)


    def addRfaAggregatorManagerEthernetInterfaces(self,mgrId):
        resId = "EthernetInterfaces"
        odataType,odataContext = self.rfaUtils.genOdataTypeContext("EthernetInterfaceCollection",None,"EthernetInterfaceCollection")
        res = dict()
        subPath = mgrId + "/" + resId 
        odataid = "/redfish/v1/Managers/" + subPath
        res["@odata.id"]= odataid
        res["@odata.type"]=odataType
        res["@odata.context"]=odataContext
        res["Name"] =  "Aggregator Manager Network Protocols"
        res["Description"] =  "Aggregation Manager Network Protocols"
        res["Members"] = []
        rc,eth0ref = self.addRfaAggregatorManagerEth0(mgrId)
        if rc is 0 and eth0ref is not None:
            res["Members"].append(eth0ref)
            ethernetInterfacesRef = {"@odata.id":  odataid }
            rc=0
        else:
            ethernetInterfacesRef=None
            rc=9
        res["Members@odata.count"] = len(res["Members"])
        self.ethernetInterfaceCollectionlResource = res
        # register the URI with the managers UriTable: register the subpath under /redfish/v1/Managers/
        rc = self.rdr.backend.managers.registerUriPath( subPath, self.ethernetInterfaceCollectionlResource,
            Get=self.rfaGetAggregatorManagerEthernetInterfaces )
        return(rc,ethernetInterfacesRef)

    def addRfaAggregatorManagerEth0(self,mgrId):
        resId = "eth0"
        odataType,odataContext = self.rfaUtils.genOdataTypeContext("EthernetInterface","v1_4_0","EthernetInterface")
        res = dict()
        subPath = mgrId + "/EthernetInterfaces/" + resId 
        odataid = "/redfish/v1/Managers/" + subPath
        res["Id"] = resId
        res["@odata.id"]= odataid
        res["@odata.type"]=odataType
        res["@odata.context"]=odataContext
        res["Name"] = "eth0"
        res["Description"] = "Aggregation Manager's Ethernet Interface"
        eth0Ref = { "@odata.id": odataid }
        self.ethernetInterfaceResource = res
        # register the URI with the managers UriTable: register the subpath under /redfish/v1/Managers/
        rc = self.rdr.backend.managers.registerUriPath( subPath, self.ethernetInterfaceResource,
            Get=self.rfaGetAggregatorManagerEthernet )
        return(0,eth0Ref)


    # GET aggregator Manager
    def rfaGetAggregatorManagerResource(self,request,subpath,allowList):
        resp = self.managerResource

        if request.method=="HEAD":
            hdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="json", allow=allowList, resource=resp)
            return(0,200,"","",hdrs)

        # update managerForChassis
        # update Links/ManagerForChassis list to include all chassis
        if "Links" in resp and "ManagerForChassis" in resp["Links"]:
            managerForChassisList = []

            # append the RackEnclosure Chassis
            chas = self.rdr.backend.chassis.rack.chassisResource
            if chas is not None and "@odata.id" in chas:
                newMember = {"@odata.id": chas["@odata.id"] }
                managerForChassisList.append(newMember)

            # append the Management Switch Chassis
            chas = self.rdr.backend.chassis.mgtSwitch.chassisResource
            if chas is not None and "@odata.id" in chas:
                newMember = {"@odata.id": chas["@odata.id"] }
                managerForChassisList.append(newMember)

            # append the aggregator Host Chassis if it exists
            chas = self.rdr.backend.chassis.aggrHost.chassisResource
            if chas is not None and "@odata.id" in chas:
                newMember = {"@odata.id": chas["@odata.id"] }
                managerForChassisList.append(newMember)

            # append each top-level rack server chassis 
            for svcId in self.rdr.backend.aggrSvcRootDb:
                svc=self.rdr.backend.aggrSvcRootDb[svcId]
                for chassisUrl in svc["TopLevelChassisUrlList"]:
                    rc,localUrl = self.rfaUtils.formLocalizedUri(svcId,chassisUrl)
                    if rc is 0 and localUrl is not None:
                        newMember = {"@odata.id": localUrl }
                        managerForChassisList.append(newMember)
            resp["Links"]["ManagerForChassis"] = managerForChassisList

        # update managerForServers
        if "Links" in resp and "ManagerForServers" in resp["Links"]:
            managerForServersList = []
            # append each top-level rack server chassis 
            for svcId in self.rdr.backend.aggrSvcRootDb:
                svc=self.rdr.backend.aggrSvcRootDb[svcId]
                for systemMember in svc["SystemsMembers"]:
                    if "@odata.id" in systemMember: 
                        rc,localUrl = self.rfaUtils.formLocalizedUri(svcId,systemMember["@odata.id"])
                        if rc is 0 and localUrl is not None:
                            newMember = {"@odata.id": localUrl }
                            managerForServersList.append(newMember)
            resp["Links"]["ManagerForServers"]= managerForServersList

        # check if we are constructing datetime from the Manager OS
        if "GetDateTimeFromOS" in self.managerResourceMgt:
            if self.managerResourceMgt["GetDateTimeFromOS"] is True:
                datetimeManagerOsUtc = datetime.datetime.now(pytz.utc).replace(microsecond=0).isoformat('T')
                datetimeOffsetManagerOsUtc="+00:00"
                resp["DateTime"] = datetimeManagerOsUtc
                resp["DateTimeLocalOffset"] = datetimeOffsetManagerOsUtc

        # check if we are constructing manager/UUID from the ServiceRoot UUID
        if "GetUuidFromServiceRoot" in self.managerResourceMgt:
            if self.managerResourceMgt["GetUuidFromServiceRoot"] is True:
                resp["UUID"] = self.rdr.root.resData["UUID"]

        # check if we are constructing manager/ServiceEntryPointUUID from the UUID in ServiceRoot
        if "GetServiceEntryPointUuidFrom" in self.managerResourceMgt:
            if self.managerResourceMgt["GetServiceEntryPointUuidFrom"] == "ServiceRoot":
                resp["ServiceEntryPointUUID"] = self.rdr.root.resData["UUID"]


        #return(fc,statusCode,"statusMsg",resp,hdrs)
        hdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="json", allow=allowList,resource=resp )

        # convert to json
        jsonResp=json.dumps(resp,indent=4)
        return(0,200,"OK",jsonResp, {}) # set hdrs=None and higher code will fill it in


    # GET aggregator NetworkProtocol
    def rfaGetAggregatorManagerNetworkProtocol(self,request,subpath,allowList):
        resp = self.networkProtocolResource 
        hdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="json", allow=allowList,resource=resp )

        # get the data from the local host that the aggregator is running on
        rc,mgrNetwkProtoInfo = self.linuxApis.getMgrNetworkProtocolInfo()
        #print("EEEEExg99: rc: {},   mnp: {}".format(rc,mgrNetwkProtoInfo))
        if rc==0:
            backendSupportedProtocols = ["HTTP","HTTPS","SSH"]
            for proto in backendSupportedProtocols:
                if proto in resp and proto in mgrNetwkProtoInfo:
                    if "ProtocolEnabled" in mgrNetwkProtoInfo[proto]:
                        resp[proto]["ProtocolEnabled"] = mgrNetwkProtoInfo[proto]["ProtocolEnabled"]
            if "HostName" in mgrNetwkProtoInfo:
                    resp["HostName"] = mgrNetwkProtoInfo["HostName"]
            if "FQDN" in mgrNetwkProtoInfo:
                    resp["FQDN"] = mgrNetwkProtoInfo["FQDN"]
        else:
            return(5,500,"Internal Error","", {})

        # convert to json
        jsonResp=json.dumps(resp,indent=4)

        #return(fc,statusCode,"statusMsg",resp,hdrs)
        return(0,200,"OK",jsonResp, hdrs)


    # GET aggregator EthernetInterfaces Collection
    def rfaGetAggregatorManagerEthernetInterfaces(self,request,subpath,allowList):
        resp = self.ethernetInterfaceCollectionlResource 
        hdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="json", allow=allowList,resource=resp )

        # convert to json
        jsonResp=json.dumps(resp,indent=4)

        #return(fc,statusCode,"statusMsg",resp,hdrs)
        return(0,200,"OK",jsonResp, hdrs)

    # GET aggregator EthernetInterface Entry
    def rfaGetAggregatorManagerEthernet(self,request,subpath,allowList):
        resp = self.ethernetInterfaceResource 
        hdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="json", allow=allowList,resource=resp )

        ethid=resp["Id"]
        # get the actual data
        # update IPv4Address info and MACAddress info
        rc,ipInfo=self.linuxApis.getMgrIpInfo(ethid)
        for ipProp in ipInfo:
            resp[ipProp] = ipInfo[ipProp]

        # convert to json
        jsonResp=json.dumps(resp,indent=4)

        #return(fc,statusCode,"statusMsg",resp,hdrs)
        return(0,200,"OK",jsonResp, hdrs)


    # PATCH Aggregation Manager
    def rfaPatchAggregatorManagerResource(self,request,subpath,allowList):
        # get the patch request data out of the request
        patchData = request.get_json(cache=True)

        # first verify that the patch data is acceptable
        for prop in patchData:
            if prop not in self.managerResourceMgt["Patchable"]:
                return(400,"property: {} is not patchable".format(prop)) # some of the patch data is invalid
        # next verify that the value is acceptable
        # xg TODO 

        # next update the resourceDb dict
        for prop in patchData:
            self.chassisResource[prop] = patchData[prop]

        # finally update the patchData Store  
        storeData = dict()
        for prop in self.chassisResourceMgt["Patchable"]:
            storeData[prop] = self.chassisResource[prop]
        self.rfaUtils.savePatchData( "AggregatorManagerDb.json", storeData )

        hdrs = self.rdr.root.hdrs.rfRespHeaders(request )

        #return(fc,statusCode,"statusMsg",resp,hdrs)
        return(0,204,"No Content","", hdrs)




