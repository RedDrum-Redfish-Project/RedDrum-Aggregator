from .aggregatorConfig import RfaConfig
from .aggregatorUtils  import RfaBackendUtils
import json

class RfaMgtSwitchChassisResources():
    def __init__(self,rdr ):
        self.rdr=rdr
        self.rfaCfg=RfaConfig()  # aggregatorConfig data
        self.rfaUtils=RfaBackendUtils(rdr)  

        self.chassisResource = None    # the resource data returned in responses
        self.chassisResourceMgt = None # additional management data for the resource
        self.powerResource = None
        self.thermalResource = None

    def addRfaMgtSwitchChassisResource(self):
        resId = self.rfaCfg.mgtSwitchChassisId
        odataType,odataContext = self.rfaUtils.genOdataTypeContext("Chassis","v1_4_0","Chassis")
        res=dict()
        res["Id"]=resId
        odataId = "/redfish/v1/Chassis/" + resId 
        res["@odata.id"]=odataId
        res["@odata.type"]=odataType
        res["@odata.context"]=odataContext

        res["Name"]="Redfish Aggregator Management Switch Chassis"
        res["Description"]="The chassis enclosure resource for the rack management switch"

        # properties configerable in rfaConfig.py
        res["ChassisType"]=self.rfaCfg.mgtSwitchChassisType
        res["Manufacturer"]=self.rfaCfg.mgtSwitchChassisManufacturer
        res["Model"]=self.rfaCfg.mgtSwitchChassisModelNumber
        res["SerialNumber"]=self.rfaCfg.mgtSwitchChassisSerialNumber

        # settable properties stored in ~rfdb/MgtSwitchChassisDb.json
        res["AssetTag"]=self.rfaCfg.mgtSwitchChassisDefaultAssetTag

        # static links 
        if self.rfaCfg.includeAggregatorManager is True:
            res["Links"] = {}
            res["Links"]["ManagedBy"]=[ { "@odata.id": "/redfish/v1/Managers/" + self.rfaCfg.aggregatorMgrId } ]
            if self.rfaCfg.redfishAggregatorIsInsideSwitch is True:
                res["Links"]["ManagersInChassis"]=[ { "@odata.id": self.rfaCfg.aggregatorMgrId } ] # 
        if self.rfaCfg.includeLocalRackEnclosureChassis is True:
            if "Links" not in res:
                res["Links"] = {}
            res["Links"]["ContainedBy"]=[ { "@odata.id": "/redfish/v1/Chassis/" + self.rfaCfg.rackEnclosureChassisId} ]

        res["PowerState"]="On"  # xg9 if aggregator is on, then rack must be on

        # Add Management Props that are not returned in resource
        resMgt=dict()
        resMgt["IsMgtSwitchChassis"]=True
        resMgt["AddOemActionsDellESIReseatChassis"] = False
        resMgt["AddOemPropertiesDellESI"] = False
        resMgt["AddOemPropertiesRackScaleLocation"]=self.rfaCfg.includeRackScaleOemProperties
        resMgt["Patchable"]=["AssetTag" ] 

        # update the database with the stored patch data 
        rc,storedPatchData = self.rfaUtils.readPatchData("MgtSwitchChassisDb.json"  )
        if rc is 0 and storedPatchData is not None:
            for prop in resMgt["Patchable"]:
                if prop in storedPatchData:
                    res[prop]= storedPatchData[prop]

        # if no patchDataStore, then create one from defaults now
        if rc is 9 and storedPatchData is None: 
            storeData = {}
            for prop in resMgt["Patchable"]:
                storeData[prop] = res[prop]
            rc = self.rfaUtils.savePatchData( "MgtSwitchChassisDb.json", storeData )

        # create a Power Resource for the chassis
        #   includes rack-level power consumption
        rc, powerRef = self.addRfaMgtSwitchChassisPowerResource(resId)
        if rc is 0:
            res["Power"]= powerRef

        # create a Thermal Resource for the chassis
        #   includes top of rack temp
        rc, thermalRef = self.addRfaMgtSwitchChassisThermalResource(resId)
        if rc is 0:
            res["Thermal"]= thermalRef

        self.chassisResource = res
        self.chassisResourceMgt = resMgt

        #register the UriPath in the chassis UriPath table
        uripath = resId
        rc = self.rdr.backend.chassis.registerUriPath( uripath, self.chassisResource,
            Get=self.rfaGetMgtSwitchChassisResource, Patch=self.rfaPatchMgtSwitchChassisResource )
        return(0)


    def addRfaMgtSwitchChassisPowerResource(self,chasId):
        # later maybe put ambient temp here
        # dont create this for now
        return(9,None)

    def addRfaMgtSwitchChassisThermalResource(self,chasId):
        # later maybe put ambient temp here
        # dont create this for now
        return(9,None)


    # GET AggrHost Chassis
    def rfaGetMgtSwitchChassisResource(self,request,subpath,allowList):
        resp = self.chassisResource
        if request.method=="HEAD":
            hdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="json", allow=allowList, resource=resp)
            return(0,200,"","",hdrs)

        #return(fc,statusCode,"statusMsg",resp,hdrs)
        hdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="json", allow=allowList,resource=resp )

        # convert to json
        jsonResp=json.dumps(resp,indent=4)
        return(0,200,"OK",jsonResp, hdrs) 


    # GET AggrHost Power
    def rfaGetMgtSwitchPowerResource(self,request,subpath,allowList):
        return(5,500,"ERROR","", {})


    # GET Rack Thermal
    def rfaGetMgtSwitchThermalResource(self,request,subpath,allowList):
        ambientRackTemp = self.rfaCalculateMgtSwitchChassisThermalResource()
        # xg99 TODO put ambient temp into temp array
        return(5,500,"ERROR","", {})

    # add up chassis power from all of the rack servers 
    def rfaCalculateMgtSwitchChassisPower(self):
        # xg99 TODO add up power
        return(None)

    # get inlet temp from several servers in rack -- bottom, mid, top
    def rfaCalculateMgtSwitchChassisThermal(self):
        # xg99 TODO add up power
        return(None)


    # PATCH Rack Chassis
    def rfaPatchMgtSwitchChassisResource(self,request,subpath,allowList, patchData):
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
        self.rfaUtils.savePatchData( "MgtSwitchChassisDb.json", storeData )

        #return(fc,statusCode,"statusMsg",resp,hdrs)
        hdrs = self.rdr.root.hdrs.rfRespHeaders(request )

        # convert to json
        return(0,204,"No Content","", hdrs) 



