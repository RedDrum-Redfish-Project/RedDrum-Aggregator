
# Copyright Notice:
#    Copyright 2018 Dell, Inc. All rights reserved.
#    License: BSD License.  For full license text see link: https://github.com/RedDrum-Redfish-Project/RedDrum-OpenBMC/LICENSE.txt

import json
from .aggregatorUtils  import RfaBackendUtils
from .redfishTransports import BmcRedfishTransport

from .aggregatorManager import RfaAggregatorManagerResources


# V2 RedDrum-Aggregator managersBackend resources
class  RdManagersBackend():
    # class for backend managers resource APIs
    def __init__(self,rdr):
        self.rdr=rdr
        self.uriPathTable = dict()
        self.rfaUtils=RfaBackendUtils(rdr)
        self.methods = ["GET","HEAD","PATCH","POST","DELETE","PUT"]

        # create the managers local sub-objects
        self.aggrMgr = RfaAggregatorManagerResources(rdr)


    # uli handler table for local managers Urls
    # the uriPaths are paths relative to /redfish/v1/Managers/
    # self.uriPathTable = {
    #    "<path>": { "<method1>": class.function, "<method2>": class.function, ... },
    #    "exRack":  { "GET": self.rack.getRack, "HEAD": self.rack.headRack, "PATCH": self.rack.patchRack... },
    #    "exRackEnclosure/Power":  { "GET": self.rack.getRackPower, "PATCH": self.rack.patchRackPower... },
    #    ...
    #    }
    def registerUriPath(self, uriPath, resource, Get=None,Patch=None,Post=None,Delete=None,Put=None):
        if uriPath is None:
            self.rdr.logMsg("ERROR","----------backend.managers.registerUriPath: uriPath is None")
            return(9)
        if resource is None:
            self.rdr.logMsg("ERROR","----------backend.managers.registerUriPath: resource is None")
            return(8)
        entry=dict()
        entry["GET"] = Get
        entry["HEAD"] = Get     # we use the Get function to execute heads
        entry["PATCH"] = Patch
        entry["POST"] = Post
        entry["DELETE"] = Delete
        entry["PUT"] = Put
        entry["Resource"] = resource
        self.uriPathTable[uriPath]=entry
        return(0)


    # GET Managers Collection from Aggregator
    #  -- create base collection properties
    #  -- add the local rack-level managers to the collection
    #  -- add the aggregated rack-server managers to the collection
    def getManagersCollection(self, request):
        # create base collection properties
        resp=dict()
        resp["@odata.context"] = "/redfish/v1/$metadata#ManagersCollection.ManagersCollection"
        resp["@odata.id"] = "/redfish/v1/Managers"
        resp["@odata.type"] = "#ManagersCollection.ManagersCollection"
        resp["Name"] = "Managers Collection"
        resp["Description"] = "Collection of Physical Containers"
        membersList = []
        count = 0

        if request.method=="HEAD":
            hdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="json", allow="Get", resource=resp)
            return(0,200,"","",hdrs)

        # add the local rack-level managers to the managers members list 
        for subpath in self.uriPathTable:
            if "Resource" in self.uriPathTable[subpath]:
                # verify that this is a managers resource
                resrc = self.uriPathTable[subpath]["Resource"]
                rc,namespace,version,resourceType = self.rfaUtils.parseOdataType(resrc)
                if rc is 0 and resourceType == "Manager":
                    entry = { "@odata.id": "/redfish/v1/Managers/" + subpath }
                    membersList.append(entry)
                    count = count + 1

        # add the aggregated rack-server managers to the collection
        for svcId in self.rdr.backend.aggrSvcRootDb:
            svc=self.rdr.backend.aggrSvcRootDb[svcId]
            if "ManagersMembers" in svc:
                managersMembers = svc["ManagersMembers"]
                for member in managersMembers: # managersMembers is a list
                    if "@odata.id" in member:
                        memberUrl = member["@odata.id"]
                        rc,entryUrl=self.rfaUtils.formLocalizedUri(svcId, memberUrl)
                        if rc==0 and entryUrl is not None:
                            entry={ "@odata.id": entryUrl }
                            membersList.append(entry)
                            count = count + 1

        # put members array into the response
        resp["Members"] = membersList
        resp["Members@odata.count"] = count

        # create headers
        hdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="json", allow="Get", resource=resp)

        # convert to json
        jsonRespData = json.dumps(resp,indent=4)

        #return(rc,statusCode,statusMsg,resp,hdrs)
        return(0, 200, "OK", jsonRespData, hdrs)


    # Process any operation on a Managers Resource under the managers collection
    # requests with URIs starting with /redfish/v1/Managers/<path: subpath>  are routed here
    #    where subpath will be of form:   <chasId>[/the rest of the poath]
    def processManagersResource(self, request, subpath):
        # subpath is the url following /redfish/v1/Managers/ starting w/ managersId
        # first check if the managersid is a local managers and not part of the rack aggregation 
        if subpath in self.uriPathTable:
            allowList=[]
            for k,v in self.uriPathTable[subpath].items():
                if k in self.methods and v is not None:
                    allowList.append(k)
            if request.method not in self.uriPathTable[subpath]:
                # return 405-Method Not Allowed
                hdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="raw", allow=allowList )
                return(5,405,"","",hdrs)
            # otherwise, process the request with the function associated with the http method 
            else:
                rc,statusCode,statusMsg,resp,hdrs=self.uriPathTable[subpath][request.method](request, subpath, allowList)
                return(rc,statusCode,statusMsg,resp,hdrs)

        # else check if the url is a valid aggregated rack server managers  
        rc,serviceIdPrefix,collectionId,bmcUrl = self.rfaUtils.parseAggregatedUrl("/redfish/v1/Managers/", subpath)
        errHdrs = self.rdr.root.hdrs.rfRespHeaders(request, contentType="raw" )
        if rc is not 0:
            if rc==1: # invalid serviceIdPrefix prefix in subpath
                errMsg="Not Found- svcId prefix: {} is not valid".format(serviceIdPrefix)
                return(rc,404,errMsg,"",errHdrs)

            elif rc==2: # the service is not in the currently discovered rootService Db
                errMsg="Not Found- svcId prefix: {} does not match any aggregated services.".format(serviceIdPrefix)
                return(rc,404,errMsg,"",errHdrs)

            elif rc==3: # the service does not have a managers with the specified managers ID
                errMsg="Not Found-the collectonId: {} does is not any managers for svcId: {}.".format(collectionId, serviceIdPrefix)
                return(rc,404,errMsg,"",errHdrs)
            else:
                errMsg="Not Found-ManagersId and serviceIdPrefix prefix parsing error. rc={}.".format(rc)
                return(rc,404,errMsg,"",errHdrs)

        # if here, the serviceIdPrefix and collectionId is good. 
        # send the request to the aggregated server BMC using bmc url bmcUrl
        svc=self.rdr.backend.aggrSvcRootDb[serviceIdPrefix]
        bmcRft=svc["RedfishTransport"]
        rc,r,j,respd = bmcRft.rfSendRecvRequest(request.method,bmcUrl,reqData=request.data)
        if rc  is not 0:
            errMsg="..........error getting response from rack server BMC: {}. rc: {}".format(serviceIdPrefix,rc)
            errMsgLine2="..............method: {}. bmcUrl: {}".format(request.method,bmcUrl)
            self.rdr.logMsg("ERROR",errMsgLine2)
            if r is not None:
                return(rc,r.status_code,errMsg,"",errHdrs) 
            else:
                return(rc,500,errMsg,"",errHdrs) 



        #  localize any links returned in the response to include the Service ID as a prefix to 
        #      the main collection IDs
        sc=r.status_code
        if sc is 200:
            self.rfaUtils.localizeResource(serviceIdPrefix, respd)  # this modifies respd
        else:
            respd={}

        # create headers
        hdrs = self.rfaUtils.addLocalizedResponseHeaders(serviceIdPrefix, request, r)  # this modifies respd

        # add oem data 

        # patch response

        # convert to json
        jsonRespData = json.dumps(respd,indent=4)

        #return(rc,statusCode,statusMsg,resp,hdrs)
        return(0, 200, "OK", jsonRespData, hdrs)


