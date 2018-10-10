import os
import json
import re


class RfaBackendUtils():
    def __init__(self,rdr ):
        self.beData=rdr.backend
        self.rdr=rdr
        self.versionedOdataTypeMatch = re.compile('^#([a-zA-Z0-9]*)\.([a-zA-Z0-9\._]*)\.([a-zA-Z0-9]*)$')
        self.unVersionedOdataTypeMatch = re.compile('^#([a-zA-Z0-9]*)\.([a-zA-Z0-9]*)$')
        self.uriMatch=re.compile("^(/redfish/v1)/?([^/]*)/?([^/]*)(/?)(.*)$")
        self.debug=False

    # ---------------------------------------------------------------------------
    # ==== General Purpose Redfish Resource parsing utilities

    # parse the @odata.type property into {namespace, version, resourceType}  following redfish syntax rules
    # returns: rc,namespace, version, resourceType.
    #   if @odata.type is not in resource, returns:   1,None,None,None
    #   if error parsing, odata.type:      returns:   2,None,None,None.
    #   if unversioned collection:         returns:   0,namespace,None,resourceType
    #   if versioned resource:             returns:   0,namespace,version,resourceType
    # usage:   
    #     from .redfishUtils import RedfishUtils
    #     rfutils=RedfishUtils()
    #     rc,namespace, version, resourceType = rfutils.parseOdataType(resource)
    def parseOdataType(self, resource):
        if not "@odata.type" in resource:
            return(1,None,None,None)

        #print("RESOURCE: {}".format(resource)) 
        resourceOdataType=resource["@odata.type"]

        # first try versioned match
        resourceMatch = re.match(self.versionedOdataTypeMatch, resourceOdataType)
        if(resourceMatch is None):
            # try unVersioned match
            resourceMatch = re.match(self.unVersionedOdataTypeMatch, resourceOdataType)
            if( resourceMatch is None):
                return(2,None,None,None)
            else:
                # unversioned resource eg Collection
                rc=0
                namespace = resourceMatch.group(1)
                version = None
                resourceType = resourceMatch.group(2)
        else:
            # versioned resource 
            rc=0
            namespace = resourceMatch.group(1)
            version = resourceMatch.group(2)
            resourceType = resourceMatch.group(3)

        return(rc, namespace, version, resourceType)


    # ---------------------------------------------------------------------------
    # ==== Utilities used by RedDrum Aggregator for LOCAL Resources eg the RackENclosure or Aggregation Manager

    # generate an @odata.type and @odata.context property for local resources
    def genOdataTypeContext(self,namespace, version, resourceType):
        if version is not None:
            odataType = "#" + namespace + "." + version + "." + resourceType
        else:
            odataType = "#" + namespace + "." + resourceType
        odataContext = "/redfish/v1/$metadata#" + namespace + "." + resourceType
        return( odataType, odataContext )

    # used to get dynamic data for local resources created by the RedDrum Aggregator eg the Chassis Rack Enclosure resource
    # usage:  rc,storedPatchDate = patchableData = self.utils.readPatchData("RackEnclosureChassisDb.json", self.resourceMgt["Patchable"] )
    def readPatchData(self, dbFilename ):
        dbFilePath = os.path.join(self.rdr.varDataPath,"db",dbFilename)
        if os.path.isfile(dbFilePath):
            storedPatchData = json.loads( open(dbFilePath,"r").read() )
            rc=0
        else:
            self.rdr.logMsg("INFO","*****WARNING: Json Data file:{} Does not exist.".format(dbFilePath))
            storedPatchData = None
            rc=9
        return (rc, storedPatchData)

    # used to save dynamic data for local resources created by the RedDrum Aggregator eg the Chassis Rack Enclosure resource
    def savePatchData(self, dbFilename, saveData ):
        dbFilePath = os.path.join(self.rdr.varDataPath,"db",dbFilename)
        jsonData = json.dumps(saveData, indent=4 )
        with open( dbFilePath, 'w', encoding='utf-8') as f:
            f.write(jsonData)
        return(0)

    # ---------------------------------------------------------------------------
    # ==== Routines to Localize Redfish Resource Response

    # localize response
    #   pass-in a svcIdPrefix eg "SYS1" which is the serviceIdPrefix, and a response dict 
    #   if error parsing response, returns rc = non-0 and newResponse=None
    #   if no error, return rc=0, and newResponse 
    #   calls  self.formLocalizedUri(svcIdPrefix, uri) to update URIs
    # "svcIdPrefix" is the Id of the discovered Redfish service 
    def localizeResource( self, svcIdPrefix, resource):
        location_uri_type_list =  ['JsonSchemaFile', 'MessageRegistryFile']  
        id_uri_type_list = ['Chassis', 'ComputerSystem', 'Manager']
        rs=resource
        self.dbgprint("DEBUG-0: in localizeResource() svcIdPrefix: {}".format(svcIdPrefix))
        for k,v in rs.items():
            self.dbgprint("DEBUG-1: k: {} v: {}".format(k,v))
    
            # handle case of location uri references to JSON schemas and messages registries
            if k == 'Location':  # note v is a list
                self.dbgprint("DEBUG-2: case: k=Location ")
                rc,ns,ver,resType=self.parseOdataType(rs)
                if rc is 0 and resType in location_uri_type_list:
                    if isinstance(v,list):
                        for loc in v:
                            if isinstance(loc,dict) and "Uri" in loc:
                                if isinstance(loc["Uri"], str):
                                    # this uri is a link to a LOCAL jsonschema store
                                    uriVal = loc["Uri"]
                                    self.dbgprint("DEBUG-2 ...updating location uri ".format(uriVal))
                                    rc,newUri = self.formLocalizedJsonSchemaFileLocationUri(svcIdPrefix, uriVal)
                                    if rc is 0: 
                                        loc["Uri"] = newUri
    
            elif k == 'target':  # note v is a list
                if isinstance(v, str):
                    self.dbgprint("DEBUG-3: case: k=target, v:{}, updating uri ".format(v))
                    rc, newUri = self.formLocalizedUri(svcIdPrefix, v)
                    if rc is 0:
                        rs[k] = newUri
            elif isinstance(v, str) and k=="@odata.id":
                self.dbgprint("DEBUG-4: case: k=odata.id, v:{}, updating uri ".format(v))
                rc, newUri = self.formLocalizedUri(svcIdPrefix, v)
                if rc is 0:
                    rs["@odata.id"] = newUri
            elif isinstance(v, str) and k=="Id":
                # fix: only localize Id if this is top level res
                rc,ns,ver,resType=self.parseOdataType(rs)
                if rc is 0 and resType in id_uri_type_list:
                    self.dbgprint("DEBUG-5: case: k=Id, v:{}, resType:{} updating uri ".format(resType,v))
                    rc, newId = self.formLocalizedResourceId(svcIdPrefix, v)
                    if rc is 0:
                        rs["Id"] = newId
    
            # if list, for each member that is a dict call this recursively: all navProps are a dict with key @odata.id
            elif isinstance(v,list):
                self.dbgprint("DEBUG-6: case v is list: k={}, do recursive call to each member ".format(k))
                for x in v:
                    if isinstance(x,dict):
                        self.localizeResource( svcIdPrefix, x)
    
            elif isinstance(v, dict):
                self.dbgprint("DEBUG-7: case v is dict: k={}".format(k))
                # This is to make sure there is only one key-value pair and it has "@odata.id" as key
                if len(v) == 1 and '@odata.id' in v:
                    self.dbgprint("DEBUG-7A: ... v is a one member dict: {}, updating uri" .format(v))
                    rc, newUri = self.formLocalizedUri(svcIdPrefix, v["@odata.id"])
                    if rc is 0:
                        rs[k]["@odata.id"] = newUri
                # this is case of an expanded collection eg GET logs collection
                elif len(v) >1 and '@odata.type' in v and "@odata.id" in v:
                    self.dbgprint("DEBUG-7B ...v is a multi-property with odata.id and odata.type eg logs ")
                    rc,ns,ver,resType=self.parseOdataType(v)
                    if rc is 0 and resType == 'LogEntry':
                        rc, newUri = self.formLocalizedUri(svcIdPrefix, v["@odata.id"])
                        if rc is 0:
                            rs[k]["@odata.id"] = newUri
                else:
                    self.dbgprint("DEBUG-7C...v is a dict that is a complex Struct")
                    for x,y in v.items():
                        if x=="target":
                            if isinstance(y, str):
                                self.dbgprint("DEBUG-7C ......x=target y={}, updating uri".format(y))
                                rc, newUri = self.formLocalizedUri(svcIdPrefix, y)
                                if rc is 0:
                                    rs[k][x] = newUri
                        if isinstance(y, dict):
                            self.dbgprint("DEBUG-7C ......y is dict, recurse...")
                            self.localizeResource( svcIdPrefix, y)
                        elif isinstance(y,list):
                            self.dbgprint("DEBUG-7C ......y is list, recurse for each member...")
                            for z in y:
                                if isinstance(z,dict):
                                    self.localizeResource( svcIdPrefix, z)
            else:
                pass
        # end for k,v in rs.items():
        return(None)

    
    def dbgprint(self, printstring):
        if self.debug is True:
            print(printstring)
        return(None)

    
    # creates a localized value for the "Id" property.  called by localizeResource()
    def formLocalizedResourceId(self, svcIdPrefix, resourceId):
        #self.rdr.logMsg("INFO","....formLocalizedResourceId: create uri for: {}".format(resourceId))
        newId = svcIdPrefix + "-" + resourceId
        return(0,newId)

    # pass-in a svcIdPrefix eg "SYS1", and a URI eg "/redfish/v1/Chassis/Rack1/Power"
    # if error parsing URI, returns rc = non-0 and newUri=None
    # if no error, return rc=0, and newUri based on 
    def formLocalizedUri(self, svcIdPrefix, uri):
        baseCollections = ["Systems", "Chassis", "Managers" ]  
        baseCollectionsExceptions = ["systems"]  #hp uses systems for some oem apis
        uriMatch=re.compile("^(/redfish/v1)/?([^/]*)/?([^/]*)(/?)(.*)$")
    
        uriParts = re.search(uriMatch,uri)
        if uriParts is not None:
            baseRedfishPath=uriParts.group(1)
            baseCollectionName=uriParts.group(2)
            baseCollectionId=uriParts.group(3)
            slashBeforeSubpath=uriParts.group(4)
            uriSubPath=uriParts.group(5)
            idSegment = svcIdPrefix + "-" + baseCollectionId
    
            if baseCollectionName in baseCollections or baseCollectionName in baseCollectionsExceptions:
                # note that some vendors include slashes after their resource URIs.  if so we get them also here
                newUri = baseRedfishPath + "/" +baseCollectionName + "/" + idSegment + slashBeforeSubpath + uriSubPath
            else:
                self.rdr.logMsg("ERROR","**formLocalizedUri: base connection: {} not supported".format(baseCollectionName))
                self.rdr.logMsg("INFO","...:uri is: {}".format(uri))
                return(3,None)
        else:
            self.rdr.logMsg("ERROR","**formLocalizedUri: base path: {} not /redfish/v1".format(baseRedfishPath))
            self.rdr.logMsg("INFO","...:uri is: {}".format(uri))
            return(4,None)
        return(0, newUri)

    # Form Localized JsonSchemaFile Location/Uri value
    # This is the value of the jsonSchemaFile["Location"]["Uri"] property and points to a LOCAL schemastore
    #  Note: This is similar to eht formLocalizedLinkHeader() except that the format is different
    #       (Link header encapsulates the uri with < > and adds ;rel=describedby)
    def formLocalizedJsonSchemaFileLocationUri(self, serviceIdPrefix, relPathToSchemafile):
        uriLink = "/redfish/v1/SchemaStores/" + serviceIdPrefix + "-" + relPathToSchemafile 
        return(0,uriLink)


    # ---------------------------------------------------------------------------
    # ==== Routines to used by backend resourceProcessing to parse an incoming Localized URI


    # parse the local subpath onto the serviceIdPrefix, collectionId,  and bmcUrl
    # returns rc=0 if no parse error
    # if error:
    #   rc=1: if the first segment of the subpath does not have a properly formed serviceId prefix followed by real Id
    #   rc=2: if the serviceId prefix is properly formed but not in the root service Db, 
    #   rc=3: if the serviceId prefix is valid and exists but the service does not have a collection entry that matches the chasId, 
    # syntax:
    # rc,serviceId,chasId,bmcUrl = parseAggregatedUrl(baseUrl, subpath)
    # example:
    #   rc,serviceId,chasId,bmcUrl = parseAggregatedUrl("/redfish/v1/Chassis/", subpath)
    def parseAggregatedUrl(self, baseUrl, subpath):
        # note that for a url eg: /redfish/v1/Systems/SYS1-Embedded.1/Processors/proc1, 
        #   baseUrl = "/redfish/v1/Systems/"
        #   subpath = "SYS1-Embedded.1/Processors/proc1" 
        #   return property: rc = 0 if success, 1-3 if error
        #   return property: serviceIdPrefix = SYS1 #the part of the subpath up to the first "-" 
        #   return property: collectionId = Embedded.1 # the rest of the main collection id after the first "-"
        #   return property: bmcUrl = /redfish/v1/Systems/Embedded.1/Processors/proc1
        self.matchSubpath = re.compile('^([^-]+)-([^/]+)(.*)$')
        aggregatedUrlParse = re.search(self.matchSubpath, subpath)

        self.dbgprint("DEBUG-PARSE_AGGREGATED_URL: baseUrl: {}, subpath: {}".format(baseUrl,subpath))

        if aggregatedUrlParse is None:
            self.dbgprint("DEBUG-PARSE_AGGREGATED_URL: rc=1 parseError")
            return(1,"","","")
        else:
            serviceIdPrefix = aggregatedUrlParse.group(1)
            collectionId = aggregatedUrlParse.group(2)
            subPathAfterId = aggregatedUrlParse.group(3)

        if serviceIdPrefix == "" or collectionId == "":
            return(1,"","","")

        # check if the serviceIdPrefix is in the service table
        if serviceIdPrefix not in self.rdr.backend.aggrSvcRootDb:
            return(2,"","","")
        svc = self.rdr.backend.aggrSvcRootDb[serviceIdPrefix]

        # check if the collectionId is valid for this service
        if baseUrl == "/redfish/v1/Chassis/":
            if "ChassisMembers" in svc:
                resourceCollection = svc["ChassisMembers"]
        elif baseUrl == "/redfish/v1/Systems/":
            if "SystemsMembers" in svc:
                resourceCollection = svc["SystemsMembers"]
        elif baseUrl == "/redfish/v1/Managers/":
            if "ManagersMembers" in svc:
                resourceCollection = svc["ManagersMembers"]
        else:
            return(5,"","","")

        # now search and see if the resource was discovered
        foundResource=False
        for member in resourceCollection:
            if "@odata.id" in member:
                targetRef = baseUrl + collectionId 
                memberRef = member["@odata.id"]  
                if memberRef.endswith('/'):
                    targetRef = targetRef + '/'
                # checking if subpath is the chassisId or chassisId/.  Hpe puts a / after many URIs
                if memberRef == targetRef:
                    foundResource=True
        if foundResource is not True:
            return(3,serviceIdPrefix,collectionId,"")

        #generate the bmc URL
        bmcUrl = baseUrl + collectionId +  subPathAfterId

        self.dbgprint("DEBUG-PARSE_AGGREGATED_URL.......: serviceIdPrefix: \"{}\"".format(serviceIdPrefix))
        self.dbgprint("DEBUG-PARSE_AGGREGATED_URL.......: collId:\"{}\",   bmcUrl:\"{}\"".format(collectionId, bmcUrl))

        rc=0
        return(rc, serviceIdPrefix, collectionId, bmcUrl)


    # called to form the Uri to a BMCs local schemafile store from the localized schemafile path
    # the full localized Uri is /redfish/v1/SchemaStores/<localizedSubpathToSchemafile>
    #      where <localizedSubPathToSchemafile> is of form: <svcIdPrefix>-<relPathToSchemafile>
    # the bmc path is formed by joining "/redfish/v1" to <relPathToSchemafile>
    #     bmcPathToSchemafile = os.path.join("/redfish/v1", <relativePathToSchemafile> )
    def parseLocalizedSchemafileStoreUri(self,localizedSubpathToSchemafile):
        uriMatch=re.compile("^(.+)-(.+)$")
        uriParts = re.search(uriMatch,localizedSubpathToSchemafile)
        if uriParts is not None:
            svcIdPrefix=uriParts.group(1) 
            relPathToSchemafile=uriParts.group(2) 
            bmcUri = os.path.join("/redfish/v1", relPathToSchemafile)
            return(0,svcIdPrefix,bmcUri)
        else:
            return(1,None,None)


    # called to form the Uri to a BMCs subpath from the localized /redfish/v1/LocationUris/<localizedSubpath) API
    # the full localized Uri is /redfish/v1/LocationUris/<localizedSubpath>
    #      where <localizedSubPath> is of form: <svcIdPrefix>-<relSubpath>
    # the bmc uri is formed by joining "/redfish/v1" to <relSubpath>
    #     bmcUri= os.path.join("/redfish/v1", <relSubpath> )
    def parseLocalizedLocationUri(self, localizedSubpath):
        uriMatch=re.compile("^(.+)-(.+)$")
        uriParts = re.search(uriMatch,localizedSubpath)
        if uriParts is not None:
            svcIdPrefix=uriParts.group(1) 
            relPathToSchemafile=uriParts.group(2) 
            bmcUri = os.path.join("/redfish/v1", relPathToSchemafile)
            return(0,svcIdPrefix, bmcUri)
        else:
            return(1,None,None)



    # ---------------------------------------------------------------------------
    # ==== Routines to process headers from bmc and create the Response Headers from the Aggregator

    # add headers to response based on response from BMC
    # Headers added include: 
    #    1) Odata-Version, Cache-Control, Access-Control-Allow-Origin -- based on RedDrum.conf settings
    #    2) Allow -- if returned by bmc
    #    3) Link  -- if returned by bmc
    #    4) Location -- localized if returned by bmc
    #    5) ETag -- if returned by bmc
    #    6) X-Auth-Token --- if returned by bmc (not returned for any APIs currently being proxied)
    # usage:
    #    hdrs = addLocalizeResponseHeaders(self,request, response)
    def addLocalizedResponseHeaders(self, serviceIdPrefix, request, response):
        hdrs=dict()

        # add Odata-Version
        hdrs['OData-Version'] = '4.0'

        # add Server header:   supports customizing the Server header based on RedDrum.conf
        if self.rdr.HttpHeaderServer is not None:
            hdrs['Server'] = self.rdr.HttpHeaderServer
        else:
            pass # let Apache fill-in the Server header 

        # add Cache-Control:  indicates if a response can be cached.   
        if self.rdr.HttpHeaderCacheControl is not None:
            hdrs['Cache-Control'] = self.rdr.HttpHeaderCacheControl
        else:
            pass  # use default Apache behavior

        # add Access-Control-Allow-Origin:  return Access Control Allow Origin
        if self.rdr.HttpHeaderAccessControlAllowOrigin is not None:
            if self.rdr.HttpHeaderAccessControlAllowOrigin == "FromOrigin":
                requestHeadersLower = {k.lower() : v for k,v in request.headers.items()}
                if 'origin' in requestHeadersLower:
                    hdrs['Access-Control-Allow-Origin'] = requestHeadersLower['origin']
            else:
                hdrs['Access-Control-Allow-Origin'] = self.rdr.HttpHeaderAccessControlAllowOrigin
        else:
            pass  # don't create this header--use default Apache behavior 

        # NOTE python3 Requests module stores the response keys case-insensitive so no we can access them w/o converting tolower...
        # add ContentType
        if  'Content-Type' in response.headers:
            contentType = response.headers["Content-Type"].lower()
            if "application/json" in contentType:
                # The Redfish recommendation is to always return odata.metadata=minimal and charset=utf-8 w/ application/json
                responseContentType = "application/json;odata.metadata=minimal;charset=utf-8"
                hdrs['Content-Type'] = responseContentType
            else:
                hdrs['Content-Type'] = response.headers['Content-Type']
        else:
            # if we don't specify anything, then flask will claim it it html. 
            # and some clients always expect contentType, so we will just return utf8 if there is no response
            # so safest strategy is to return utf8 if there is no response
            hdrs['Content-Type'] = "charset=utf-8"

        # add x-auth-token
        if 'X-Auth-Token' in response.headers:
            hdrs['X-Auth-Token'] = response.headers['X-Auth-Token'] 

        # add etag.   
        if "ETag" in response.headers:
            hdrs['ETag'] = response.headers["ETag"]

        # add Allow:   return Allow header from list of Allow headers passed in
        if "Allow" in response.headers:
            hdrs['Allow'] = response.headers["Allow"]

        # if the response has a Location header, then localize it and return it
        if "Location" in response.headers:
            locationUri = response.headers["Location"]
            rc, newLocationUri = self.formLocalizedLocationHeader(serviceIdPrefix, locationUri)
            if rc is 0:
                hdrs["Location"] = newLocationUri

        # if the response has Links header, then localize it
        # note that Link header format is eg:  <http: //redfish.dmtf.org/schemas/v1/Chassis.v0_1_0.json>;rel=describedby
        # not that Links may point to an external Uri eg DMTF in which case we don't localize it
        if "Link" in response.headers:
            linkHeader = response.headers['Link']
            rc,scheme,netloc,schemafilePath=self.parseLinkHeaderFromBmc(linkHeader)
            # returns rc=0 if the link header was of valid form
            if rc is 0: 
                # this is a valid link header was returned
                # now check if this is a 'local' link --it not to an external scheme and netloc
                if scheme is None and netloc is None:
                    # this is a link to a local schema file -- so we need to localize it
                    rc, newLinkHeader = self.formLocalizedLinkHeader(serviceIdPrefix, schemaFilePath)
                    if rc is 0:
                        hdrs["Link"] = newLinkHeader
                else:
                    # this is an external link to a schemafile so we don't need to localize it
                    hdrs["Link"] = linkHeader
            else:
                # the link header returned by the bmc was not valid
                # xg99 try to generate one here like we do in frontend
                pass
        return(hdrs)

    # parses link header of form "<http://redfish.dmtf.org/schemas/v1/Chassis.v0_1_0.json>; rel=describedby"
    #  --or-- if it is a path to a local schema store, form:    "</pathToStore/Chassis.v0_1_0.json>; rel=describedby"
    #  info scheme(http), netloc(redfish.dmtf.org), and path to schemafile (/schemas/v1/Chassis.v0_1_0.json)
    # rc,scheme,netloc,schemafilePath=self.parseLinkHeaderFromBmc(linkHeader)
    def parseLinkHeaderFromBmc(self, linkHeader):
        uriMatch=re.compile("^<(http[s]?:)?(//[^/]+)?(/[^>]+).*$")
        uriParts = re.search(uriMatch,linkHeader)
        if uriParts is not None:
            uriScheme=uriParts.group(1) # eg "http:" or "https:" or None
            uriNetloc=uriParts.group(2) # eg "//redfish.dmtf.org" or "//127.0.0.1" or None
            schemafilePath=uriParts.group(3) # eg "/schemas/v1/Chassis.v0_1_0.json" or "/redfish/v1/ChassisStore/x.json"
            return(0,uriScheme, uriNetloc, schemafilePath)
        else:
            return(1,None, None, None)


    # Form a localized "Link" header that points to a local Json Schemafile store
    # The localized path in the link hdr formed will be at /redfish/v1/SchemaStores/<SvcIdPrefix>-<relPathToSchemafile>
    # If a client sends a request to the RedDrum service starting with /redfish/v1/SchemaStores/<localizedSubpathToSchemafile>
    #   the frontend flask URI routes will extract <localizedSubpathToSchemafile> and call the backend routine to get the file
    #   The routine parseLocalizedSchemafileStoreUri(localizedSubpathToSchemafile) is used to transform the subpath into a bmc URI
    # NOTE: <relPathToSchemafile> should NOT start with /, if the <bmcUri> is relative to (ie below) /redfish/v1/
    #       <relPathToSchemafile> SHOULD start with "/" , if the <bmcUri> is relative to / w/o a redfish/v1 in front of it
    # Usage:
    #   rc, newLinkHeader = self.formLocalizedLinkHeaderUri(serviceIdPrefix, relPathToSchemafile)
    def formLocalizedLinkHeader(self, serviceIdPrefix, relPathToSchemafile):
        linkHeader = "</redfish/v1/SchemaStores/" + serviceIdPrefix + "-" + relPathToSchemafile + ">; rel=describedby"
        return(0,linkHeader)


    # Form a localized "Location" header from the one returned by a BMC
    # <locationUri> is either a relative URI:  /redfish/v1/<pathToFile>   --OR--  
    #               and absolute URI of form: http[s]://<netloc>/redfish/v1/<pathToFile> 
    # The routine w/ create a URI that it can unwind into a proper URI for a BMC if the client sends it back
    # Unless the URI path is recognized as a common OpenAPI-defined path) (eg /redfish/v1/Sessions/<id>)
    # the localization will return a Uri of form: /redfish/v1/LocationUris/<serviceIdPrefix>-<fullPathFromAfterNetloc>
    #  NOTE that the scheme and netloc MAY be present in Location Headers since in the past an absolute uri was required for Location
    #         or with the latest RFCs, relative URIs can be returned in Location headers (where the URI starts with /)
    #         and clients must join it to the current scheme and IP as:  scheme://<netloc>/<relativeUri>
    #  NOTE also that Flask will turn the location header into an absolute URL w/ scheme://<netloc>  as recommended by the RFCs
    #    UNLESS response.autocorrect_location_header=False  (see article searchFor: "return-a-relative-uri-location-header-with-flask"
    #    RedDrum is not returning relative Location headers 
    # Usage:
    #    rc, newLocationUri = formLocalizedLocationHeader(serviceIdPrefix, locationuri)
    #xg99 - TODO: support forming localizedLocationUri for defined OpenApi URI paths that might return Location header 
    #xg99   (eg Tasks, Accounts, Sessions,..) eg /redfish/v1/SessionService/Sessions/<svcIdPrefix>-<sessionId>
    #         
    def formLocalizedLocationHeader(self, serviceIdPrefix, locationUri):
        uriMatch=re.compile("^(http[s]?:)?(//[^/]+)?(/.*)$")
        uriParts = re.search(uriMatch,locationUri)
        if uriParts is not None:
            uriScheme=uriParts.group(1) # eg "http:" or "https:" or None
            uriNetloc=uriParts.group(2) # eg "//redfish.dmtf.org" or "//127.0.0.1" or None
            uriPath=uriParts.group(3)   # eg "/redfish/v1/Chassis/2"
            newUri = "/redfish/v1/LocationUris/" + serviceIdPrefix + "-" + uriPath
            return(0,uriPath)
        else:
            return(1,None)

    # ---------------------------------------------------------------------------
    # ==== Routines to Localize a Jsonschema file

    # Localize a Json Schema
    # This localizes an actual Jsonschema (not the Redfish SchemaFile type that points to a JsonSchema)
    # this modifies resource dict
    # NOTE:  URIs in schemafiles start with $ref.
    #        if the URI in the file does NOT start with / (eg resource.json), it is relative to the main file path
    #            that the client used to read the file (a file in the same directory), so it does NOT need to be localized
    #        if the URI starts with /, it is relative to the IP and thus DOES need to be localized
    #        if the URI points to external website (eg dmtf.redfish.org or an oem's site) it does not need to be localized
    #        it is best practice that all of the uris in a local schema store use relative links to the same directory
    #           so that there is no chance of needing to go offsite to get the file
    # xg99 need to implement the Jsonschema localization
    # USAGE: localizeJsonschema(svcIdPrefix, resource) # rc = 0 of no error
    def localizeJsonschema(self, svcIdPrefix, resource):
        # verify this is a proper jsonschema file 1st  it should have the property "$schema"
        #if "$schema" not in resource:
        #    return(1)
        # walk the dict recursively and update all "$ref" properties found
        pass
        return(None)

