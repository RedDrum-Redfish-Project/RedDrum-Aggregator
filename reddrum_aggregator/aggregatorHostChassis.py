from .aggregatorConfig import RfaConfig
from .aggregatorUtils  import RfaBackendUtils
import json

class RfaAggregatorHostChassisResources():
    def __init__(self,rdr ):
        self.rdr=rdr
        self.rfaCfg=RfaConfig()  # aggregatorConfig data
        self.rfaUtils=RfaBackendUtils(rdr)  
        self.chassisResource = None    # the resource data returned in responses
        self.chassisResourceMgt = None # additional management data for the resource
        self.powerResource = None
        self.thermalResource = None

    def addRfaAggregatorHostChassisResource(self):
        resId = self.rfaCfg.aggregatorHostChassisId
        odataType,odataContext = self.rfaUtils.genOdataTypeContext("Chassis","v1_4_0","Chassis")
        res=dict()
        res["Id"]=resId
        odataId = "/redfish/v1/Chassis/" + resId 
        res["@odata.id"]=odataId
        res["@odata.type"]=odataType
        res["@odata.context"]=odataContext

        res["Name"]="Redfish Aggregator HOST Chassis"
        res["Description"]="The host processor enclosure that contains the Redfish Aggregator when it is not embedded in a mgt switch"

        # properties configerable in rfaConfig.py
        res["ChassisType"]=self.rfaCfg.aggregatorHostChassisType
        res["Manufacturer"]=self.rfaCfg.aggregatorHostChassisManufacturer
        res["Model"]=self.rfaCfg.aggregatorHostChassisModelNumber
        res["SerialNumber"]=self.rfaCfg.aggregatorHostChassisSerialNumber

        # settable properties stored in ~rfdb/AggregatorHostChassisDb.json
        res["AssetTag"]=self.rfaCfg.aggregatorHostChassisDefaultAssetTag

        # static links 
        if self.rfaCfg.includeAggregatorManager is True:
            res["Links"] = {}
            res["Links"]["ManagedBy"]=[ { "@odata.id": "/redfish/v1/Managers/" + self.rfaCfg.aggregatorMgrId } ]
            res["Links"]["ManagersInChassis"]=[ { "@odata.id": self.rfaCfg.aggregatorMgrId } ] # 
        if self.rfaCfg.includeLocalRackEnclosureChassis is True:
            if "Links" not in res:
                res["Links"] = {}
            res["Links"]["ContainedBy"]=[ { "@odata.id": "/redfish/v1/Chassis/" + self.rfaCfg.rackEnclosureChassisId} ]
        
        res["PowerState"]="On"  # xg9 if aggregator is on, then rack must be on

        # Add Management Props that are not returned in resource
        resMgt=dict()
        resMgt["IsAggregatorHostChassis"]=True
        resMgt["AddOemActionsDellESIReseatChassis"] = False
        resMgt["AddOemPropertiesDellESI"] = False
        resMgt["AddOemPropertiesRackScaleLocation"]=self.rfaCfg.includeRackScaleOemProperties
        resMgt["Patchable"]=["AssetTag" ] 

        # update the database with the stored patch data 
        rc,storedPatchData = self.rfaUtils.readPatchData("AggregatorHostChassisDb.json"  )
        if rc is 0 and storedPatchData is not None:
            for prop in resMgt["Patchable"]:
                if prop in storedPatchData:
                    res[prop]= storedPatchData[prop]

        # if no patchDataStore, then create one from defaults now
        if rc is 9 and storedPatchData is None: 
            storeData = {}
            for prop in resMgt["Patchable"]:
                storeData[prop] = res[prop]
            rc = self.rfaUtils.savePatchData( "AggregatorHostChassisDb.json", storeData )

        # create a Power Resource for the chassis
        #   includes rack-level power consumption
        rc, powerRef = self.addRfaAggregatorHostChassisPowerResource(resId)
        if rc is 0:
            res["Power"]= powerRef

        # create a Thermal Resource for the chassis
        #   includes top of rack temp
        rc, thermalRef = self.addRfaAggregatorHostChassisThermalResource(resId)
        if rc is 0:
            res["Thermal"]= thermalRef

        self.chassisResource = res
        self.chassisResourceMgt = resMgt

        #register the UriPath in the chassis UriPath table
        uripath = resId
        rc = self.rdr.backend.chassis.registerUriPath( uripath, self.chassisResource,
            Get=self.rfaGetAggregatorHostChassisResource, Patch=self.rfaPatchAggregatorHostChassisResource)
        return(0)


    def addRfaAggregatorHostChassisPowerResource(self,chasId):
        # later maybe put ambient temp here
        return(9,None)

    def addRfaAggregatorHostChassisThermalResource(self,chasId):
        # later maybe put ambient temp here
        return(9,None)


    # GET AggrHost Chassis
    def rfaGetAggregatorHostChassisResource(self,request,subpath,allowList):
        resp = self.chassisResource

        if request.method=="HEAD":
            hdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="json", allow=allowList, resource=resp)
            return(0,200,"","",hdrs)

        #return(fc,statusCode,"statusMsg",resp,hdrs)
        hdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="json", allow=allowList,resource=resp )

        # convert to json
        jsonResp=json.dumps(resp,indent=4)
        return(0,200,"OK",jsonResp, {}) # set hdrs=None and higher code will fill it in



    # GET AggrHost Power
    def rfaGetAggregatorHostPowerResource(self,request,subpath,allowList):
        return(5,500,"ERROR","", {}) 

    # GET Rack Thermal
    def rfaGetAggregatorHostThermalResource(self,request,subpath,allowList):
        return(5,500,"ERROR","", {}) 



    # PATCH Rack Chassis
    def rfaPatchAggregatorHostChassisResource(self,request,subpath,allowList):
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
        self.rfaUtils.savePatchData( "AggregatorHostChassisDb.json", storeData )

        #return(fc,statusCode,"statusMsg",resp,hdrs)
        hdrs = self.rdr.root.hdrs.rfRespHeaders(request )

        # convert to json
        return(0,204,"No Content","", hdrs)




