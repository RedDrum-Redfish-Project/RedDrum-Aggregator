from .aggregatorConfig import RfaConfig
from .aggregatorUtils  import RfaBackendUtils
import json

class RfaRackEnclosureChassisResources():
    def __init__(self,rdr ):
        self.rdr=rdr
        self.rfaCfg=RfaConfig()  # aggregatorConfig data
        self.rfaUtils=RfaBackendUtils(rdr)  
        self.chassisResource = None    # the resource data returned in responses
        self.chassisResourceMgt = None # additional management data for the resource
        self.powerResource = None
        self.thermalResource = None

    def addRfaRackEnclosureChassisResource(self):
        resId = self.rfaCfg.rackEnclosureChassisId
        odataType,odataContext = self.rfaUtils.genOdataTypeContext("Chassis","v1_4_0","Chassis")
        res=dict()
        res["Id"]=resId
        odataId = "/redfish/v1/Chassis/" + resId
        res["@odata.id"]=odataId
        res["@odata.type"]=odataType
        res["@odata.context"]=odataContext

        res["Name"]="Redfish_Aggretator_Rack"
        res["Description"]="Rack-Level Enclosure for of Redfish Aggregator Servers and Mgt Switch "
        res["ChassisType"]="Rack"

        # properties configerable in rfaConfig.py
        res["Model"]=self.rfaCfg.rackEnclosureChassisModelNumber
        res["Manufacturer"]=self.rfaCfg.rackEnclosureChassisManufacturer
        res["SerialNumber"]=self.rfaCfg.rackEnclosureChassisSerialNumber
        res["AssetTag"]=self.rfaCfg.rackEnclosureChassisDefaultAssetTag

        # static links 
        res["Links"] = {}
        if self.rfaCfg.includeAggregatorManager is True:
            res["Links"]["ManagedBy"]=[ { "@odata.id": self.rfaCfg.aggregatorMgrId } ]
            res["Links"]["ManagersInChassis"]=[ { "@odata.id": self.rfaCfg.aggregatorMgrId } ] # 
        res["Links"]["Contains"]=[]  # update using updateRfaRackEnclosureChassisContainsList() 

        res["PowerState"]="On"  # if aggregator is on, then rack must be on

        # Add Management Props that are not returned in resource
        resMgt=dict()
        resMgt["IsTopLevelChassisEnclosureRack"]=True
        resMgt["AddOemActionsDellESIReseatChassis"] = True
        resMgt["AddOemPropertiesDellESI"] = False
        resMgt["AddOemPropertiesRackScaleLocation"]=self.rfaCfg.includeRackScaleOemProperties
        resMgt["Patchable"]=["AssetTag" ] 


        # update the database with the stored patch data 
        rc,storedPatchData = self.rfaUtils.readPatchData("RackEnclosureChassisDb.json"  )
        if rc is 0 and storedPatchData is not None:
            for prop in resMgt["Patchable"]:
                if prop in storedPatchData:
                    res[prop]= storedPatchData[prop]

        # if no patchDataStore, then create one from defaults now
        if rc is 9 and storedPatchData is None: 
            storeData = {}
            for prop in resMgt["Patchable"]:
                storeData[prop] = res[prop]
            rc = self.rfaUtils.savePatchData( "RackEnclosureChassisDb.json", storeData )

        # create a Power Resource for the chassis
        #   includes rack-level power consumption
        rc, powerRef = self.addRfaRackEnclosureChassisPowerResource(resId)
        if rc is 0:
            res["Power"]= powerRef

        # create a Thermal Resource for the chassis
        #   includes top of rack temp
        rc, thermalRef = self.addRfaRackEnclosureChassisThermalResource(resId)
        if rc is 0:
            res["Thermal"]= thermalRef

        self.chassisResource = res
        self.chassisResourceMgt = resMgt

        # register the URI with the chassisUriTable: register the subpath under /redfish/v1/Chassis/
        rc = self.rdr.backend.chassis.registerUriPath( resId, self.chassisResource,
            Get=self.rfaGetRackEnclosureChassisResource, Patch=self.rfaPatchRackEnclosureChassisResource )

        return(0)


    def addRfaRackEnclosureChassisPowerResource(self,chasId):
        resId = "Power"
        odataType,odataContext = self.rfaUtils.genOdataTypeContext("Power","v1_5_0","Power")
        res=dict()
        res["Id"]=resId
        subPath = chasId + "/" + resId 
        odataId = "/redfish/v1/Chassis/" + subPath
        res["@odata.id"]=odataId
        res["@odata.type"]=odataType
        res["@odata.context"]=odataContext

        res["Name"]="Rack Enclosure Power Resoruce"
        res["Description"]="Rack-Level Enclosure Power Resource"

        # PowerControl resource
        pcRes=dict()
        pcRes["@odata.id"]= odataId + "#/PowerControl/0"
        pcRes["MemberId"]="0"
        pcRes["Name"]="Rack Level Power Control"
        pcRes["PhysicalContext"]="Chassis"   # the entire rack chassis
        pcRes["PowerConsumedWatts"]=None
        chasUrl = "/redfish/v1/Chassis/" + chasId
        pcRes["RelatedItems"]=[ {"@odata.id": chasUrl } ]
        pcRes["Status"]={ "State": "Enabled", "Health": "OK" }

        res["PowerControl"]=[ pcRes ]

        self.powerResource = res
        powerRef = {"@odata.id": odataId }

        #register the UriPath in the chassis UriPath table
        rc = self.rdr.backend.chassis.registerUriPath( subPath, self.powerResource,
            Get=self.rfaGetRackEnclosurePowerResource)
        return(0,powerRef)

    def addRfaRackEnclosureChassisThermalResource(self,chasId):
        # later maybe put ambient temp here
        return(9,None)


    # GET HEAD Rack Chassis
    def rfaGetRackEnclosureChassisResource(self,request,subpath,allowList):
        resp = self.chassisResource
        containsList=[]

        if request.method=="HEAD":
            hdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="json", allow=allowList, resource=resp)
            return(0,200,"","",hdrs)

        # add the Mgt Switch chassis and Aggregator Host chassis (if it exists) to the Contains list
        # append the aggregator host chassis if it exists
        if self.rdr.backend.chassis.aggrHost.chassisResource is not None:
            newMemberUrl = self.rdr.backend.chassis.aggrHost.chassisResource["@odata.id"]
            newMember = {"@odata.id": newMemberUrl }
            containsList.append(newMember)

        # append the management switch chassis if it exists
        if self.rdr.backend.chassis.mgtSwitch.chassisResource is not None:
            newMemberUrl = self.rdr.backend.chassis.mgtSwitch.chassisResource["@odata.id"]
            newMember = {"@odata.id": newMemberUrl }
            containsList.append(newMember)

        # update Links/Contains to include all chassis
        if "Links" in resp and "Contains" in resp["Links"]:
            # append each top-level rack server chassis to the Contains list
            for svcId in self.rdr.backend.aggrSvcRootDb:
                svc=self.rdr.backend.aggrSvcRootDb[svcId]
                for chassisUrl in svc["TopLevelChassisUrlList"]:
                    rc,localUrl = self.rfaUtils.formLocalizedUri(svcId,chassisUrl)
                    if rc is 0 and localUrl is not None:
                        newMember = {"@odata.id": localUrl }
                        containsList.append(newMember)

        resp["Links"]["Contains"] = containsList

        hdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="json", allow=allowList,resource=resp )

        # convert to json
        jsonResp=json.dumps(resp,indent=4)

        #return(fc,statusCode,"statusMsg",resp,hdrs)
        return(0,200,"OK",jsonResp, hdrs) 


    # GET Rack Power
    def rfaGetRackEnclosurePowerResource(self,request,subpath,allowList):
        totalRackPower = self.rfaCalculateRackEnclosureChassisPowerResource()
        if "PowerControl" in self.powerResource and len(self.powerResource["PowerControl"]) == 1:
            if "PowerConsumedWatts" in self.powerResource["PowerControl"][0]:
                self.powerResource["PowerControl"][0]["PowerConsumedWatts"]=totalRackPower

        resp=self.powerResource

        hdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="json", allow=allowList,resource=resp )

        # convert to json
        jsonResp=json.dumps(resp,indent=4)

        #return(fc,statusCode,"statusMsg",resp,hdrs)
        return(0,200,"OK",jsonResp, hdrs) 


    # GET Rack Thermal
    def rfaGetRackEnclosureThermalResource(self,request,subpath,allowList):
        ambientRackTemp = self.rfaCalculateRackEnclosureChassisThermalResource()
        # xg99 TODO put ambient temp into temp array
        return(5,500,"ERROR","", {})


    # add up chassis power from all of the rack servers 
    def rfaCalculateRackEnclosureChassisPowerResource(self):
        # xg99 TODO add up power
        return(808)

    # get inlet temp from several servers in rack -- bottom, mid, top
    def rfaCalculateRackEnclosureChassisThermalResource(self):
        # xg99 TODO add up power
        return(None)


    # PATCH Rack Chassis
    def rfaPatchRackEnclosureChassisResource(self,request,subpath,allowList):
        # get the patch request data out of the request
        patchData = request.get_json(cache=True)

        # first verify that the patch data is acceptable
        for prop in patchData:
            if prop not in self.chassisResourceMgt["Patchable"]:
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
        self.rfaUtils.savePatchData( "RackEnclosureChassisDb.json", storeData )

        #return(fc,statusCode,"statusMsg",resp,hdrs)
        hdrs = self.rdr.root.hdrs.rfRespHeaders(request )

        # convert to json
        return(0,204,"No Content","", hdrs) 



