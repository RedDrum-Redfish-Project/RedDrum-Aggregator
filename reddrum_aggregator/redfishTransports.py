# Copyright Notice:
#    Copyright 2017 Dell, Inc. All rights reserved.

# Redfish Transport
import os
import re
import requests
import json
import sys
import socket
import time
from urllib.parse import urljoin, urlparse, urlunparse
from requests.auth import HTTPBasicAuth, AuthBase


class RfSessionAuth(AuthBase):
    def __init__(self,authToken):
        self.authToken=authToken

    def __call__(self, r):
        r.headers['X-Auth-Token']=self.authToken
        return(r)


class RedfishTransport():
    def __init__(self, rhost=None, isSimulator=False, debug=False, credentialsPath=None):

        # default timeouts, headers, and nextlinks used by THIS transport
        self.MaxNextLinks=10                # max number of requests allowed with NextLink
        self.dfltPatchPostPutHdrs = {'OData-Version': '4.0', 'Content-Type': 'application/json', 'Accept': 'application/json'  }
        self.dfltGetDeleteHeadHdrs = {'Accept': 'application/json', 'OData-Version': '4.0' }
        self.waitTime=3
        self.waitNum=1
        self.timeout=10         # http transport timeout in seconds, stored as int here
        self.unauthenticatedApiScheme="http"  # xg-the scheme to use for unauthenticated APIs --http should always work

        # default scheme, authType, and username/password
        self.scheme="http"      # the default scheme to use for this transport:  (https for idrac,    http for MC )
        self.auth="None"        # AuthN to use:    ("None" for MC,  "Session" or "Basic" for idrac)
        self.user="root"        # get from credential vault, (this is the default)
        self.password="calvin"  # get from credential vault, (this is the default)
        self.SessionLoginUrl="/redfish/v1/SessionService/Sessions" # URI where Sessions collection is for session login
        self.program = "baseRMRedfishTransport"

        # set paths to credential vault for this transport
        self.credentialsPath=None
        #self.credentialsPath="/etc/opt/dell/rm-tools/Credentials/mcroot/.passwd  # MC root password
        #self.credentialsPath="/etc/opt/dell/rm-tools/Credentials/bmcuser/.passwd # BMC password

        # session auth parameters stored here for when Session Auth is used
        self.sessionId=None
        self.sessionLink=None
        self.authToken=None
        self.cleanupOnExit=True   # if true, the session will be deleted whenever self.rfCleanup(rft) is called

        # root paths for the session
        self.rhost=None          # specify this in transport if using a common rhost for this transport
        self.rootPath="/redfish/v1/"

        # verbose and status flags used for debug print and logging filtering 
        self.verbose=0
        self.status=0
        self.quiet=True
        if isSimulator is True:
            self.quiet=False
        # if debug flag set, set quiet=False, and set verbose=3, status=5
        if debug is True:
            self.verbose=3
            self.status=5
            self.quiet=False

        # disable urllib print warning
        requests.packages.urllib3.disable_warnings()

        # measured execution time
        self.elapsed=None

        # calculate self.rhost based on passed-in rhost
        rfConnectionInit(rhost=rhost)
        
        # load the credential file into the user, password property at self.user, self.password
        rfGetCredentialsFromVault(self)


    def rfConnectionInit(self, rhost=None):
        # if rhost was passed-in when the transport was instantiated, then use the passed-in rhost IPaddress/port
        # otherwise, use the default rhost in the transport 
        if rhost is not None:
            self.rhost = rhost
        scheme_tuple=[self.unauthenticatedApiScheme, self.rhost, self.rootPath, "","",""]
        self.rootUrl=urlunparse(scheme_tuple)      # <scheme>://<netloc>/redfish/v1/

    def rfGetCredentialsFromVault(self):
        # if the path to the credential vault is not none,
        # then we need to set the user and password equal to the value in the credential vault
        # Note that some transports use AuthNone so the path is None
        # And other transports may just use the default username/password in self.user, self.password
        if self.credentialsPath is not None:
            #  the password file has data of form:    <username>:<password>,  one entry per line.
            # first verfiy we have a credential file
            if os.path.isfile( self.credentialsPath ) is not True:
                return(-1)
            with open( self.credentialsPath, "r") as f:
                creds = [x.strip().split(':') for x in f.readlines()]

            # just get the 1st user for now
            self.user,self.password=creds[0]
            return(0)


    def  rftCheckIfAuthenticatedApi(rft,method,url):
        if( method == "GET"):
            if( (url=="/redfish/v1") or (url=="/redfish/v1/") or (url=="/redfish/v1/odata") or (url=="/redfish/v1/$medatata") ):
                return( False )
        elif( method == "POST"):
            if( url == rft.SessionLoginUrl ):
                return( False )
        return (True)

    #'''
    # main transport function
    # handles the following processing within this function:
    #  --- set default scheme based on command type 
    #  --- joins passed-in UrlPath with calculated scheme/netloc/ 
    #  --- auto-sets headers based on: authenticationType, method, etag, dataType for the command
    #  --- supports Redfish Session Auth--automatically logs-in with session auth if transport set for session auth
    #  --- processes Requests exceptions correctly
    #  --- if response returned NextLink, loop to get all of the data
    #  --- auto-loads response into Dict with exception handling 
    #  --- printing/logging  error messages from Requests or json.loads, and setting return codes
    #  --- can call the Requests function with additional kwargs data
    #  --- returning standard tuple: rc,r,j,d  (retrunCode, requests response,  loadJsonData, data)
    #
    #       rc,r,j,d =(returnCode(int: 0=ok), RequestsResponse, isJsonData(True/False), data (type: None|dict|text))
    #
    def rfSendRecvRequest( rft, method, urlPath, reqData=None, scheme=None, auth=None,
                           loadJsonData=True, verify=False, headersInput=None,  **kwargs ):

        # check if this is an AUthenticated API based on path   urlPath = "/redfish/v1/odata" for example
        isAuthenticatedApi=rft.rftCheckIfAuthenticatedApi(method,urlPath)

        # get scheme based on target
        if scheme is None:
            if( method=="GET") and isAuthenticatedApi is False:
                # always use http for unauthenticated APIs
                scheme = rft.unauthenticatedApiScheme
            else:
                # else use the default scheme for the transport
                scheme=rft.scheme
        elif scheme == "http":
            scheme="http"
        elif scheme == "https":
            scheme="https"
        else: 
            scheme = "http"

        # get the root service URL that was created the first time the transport ran against the remote host
        urlp = urlparse(rft.rootUrl)   # where rft.rootUrl is http://<netloc>/redfish/v1 
        
        # create the base URL with proper scheme://<netloc>/<uri> using urlunparse 
        scheme_tuple=[scheme, urlp.netloc, urlp.path, "","",""]  # here urlp.path and netloc is from the root service
        urlBase=urlunparse(scheme_tuple)
        
        # join the baseURL and urlPath passed in
        # if urlPath starts with /, then it replaces the /redfish/v1 from the root service
        url=urljoin(urlBase,urlPath) 
        
        #define headers.
        # the transport will use defaults specified in the Transport defaults properties dfltXYZHdrs depending on method XYZ.
        # if headers were passed in by a command function in property headersInput, then add them or modify default with those values
        # And also: if addl headers were specified in the commandline -H <hdrs> option, add them to the defaults above

        # ex self.dfltPatchPostPutHdrs  = {"content-type": "application/json", "Accept": "application/json", "OData-Version": "4.0" }
        # ex self.dfltGetDeleteHeadHdrs = {"Accept": "application/json", "OData-Version": "4.0" }

        # get default headers based on the method being called
        if( (method == 'PATCH') or (method == 'POST') or (method == 'PUT') ):
            hdrlist=rft.dfltPatchPostPutHdrs
        else:  # method is GET, DELETE, HEAD
            hdrlist=rft.dfltGetDeleteHeadHdrs

        # make copy of the dict.  Otherwise Requests is sometimes not adding addl headers.  a byte vs string bug in requests
        hdrs=dict(hdrlist)

        # if a list of headers was sent in as an input parameter, then add them (or update defaults with new values)
        if( headersInput is not None):  # headers passed in from a calling function overrides defaults
            for key in headersInput:
                hdrs[key]=headersInput[key]

        # get rid of Accept-Encoding which Requests is auto-creating 
        hdrs['Accept-Encoding']=None
                
        #calculate the authentication method
        authType=None
        authMsg=None

        validAuthValues=("Basic","Session","None")
        if auth is not None:
            if auth not in validAuthValues:
                rft.printErr("Transport: invalid auth value: {}".format(auth))
                auth = "Basic"

        if auth is None:
            # if no Auth value was passed-in, then use the default auth for this transport
            auth = rft.auth

        if( (isAuthenticatedApi is True) and (auth=="Basic")):
            authType=HTTPBasicAuth(rft.user, rft.password)
            authMsg="Basic"

        elif( (isAuthenticatedApi is True) and (auth=="Session")):
            if( rft.authToken is None):   # ie: we dont already have a token that was passed in or previously loggedin
                rc,r,j,d=rft.rfSessionLogin(rft)  #cleanup=true tells the transport to logout at end of cmd
                #this will save the authToken at rft.token, and sessionLink at rft.sessionLink
                if( rc != 0):  # error logging in
                    return(rc,r,j,d)
            # now we should have a valid auth token. create an instance of this auth
            authType=RfSessionAuth(rft.authToken)
            authMsg="Session"

        else:  # Auth is None or its an unauthenticated API so we are going to use AuthNone 
            authType=None
            authMsg="None"
        
        # now send request to rhost, with retries based on -W <waitNum>:<waitTime> option.
        # handle exceptions including timeouts.
        success=None
        r=None
        respd=None
        nextLink=True
        for attempt in range(0,rft.MaxNextLinks):
            try:
                rft.printVerbose(3,"Transport:SendRecv:    {} {}".format(method,url))
                t1=time.time()
                r = requests.request(method, url, headers=hdrs, auth=authType, verify=verify, data=reqData,
                                     timeout=(rft.waitTime,rft.timeout),**kwargs)  # GET ^/redfish
                t2=time.time()
                rft.elapsed = t2 - t1
                # print request headers
                rft.printStatus(3,r=r,authMsg=authMsg)

            except requests.exceptions.ConnectTimeout:
                # connect timeout occured.  try again w/o sleeping since a timeout already occured
                rft.printVerbose(5,"Tranport: connectTimeout, try again")
                return(5,r,False,None)
            except (socket.error):
                # this exception needed as requests is not catching socket timeouts
                #  especially "connection refused" eg web server not started
                # issue: https://github.com/kennethreitz/requests/issues/1236
                # Nothing timed out.  this is a connect error. So wait and retry
                rft.printVerbose(5,"Tranport: socket.error,  wait and try again")
                time.sleep(rft.waitTime)
                return(6,r,False,None)
            except (requests.exceptions.ReadTimeout):
                # read timeout occured. This shouldn't happen, so fail it
                rft.printErr("Transport: Fatal timeout waiting for response from rhost")
                return(7,r,False,None)
            except (requests.exceptions.ConnectionError):
                # eg DNS error, connection refused.  wait and try again
                rft.printVerbose(5,"Tranport: ConnectionError, wait and try again")
                time.sleep(rft.waitTime)
                return(8,r,False,None)
            except requests.exceptions.RequestException as e:
                # otherl requests exceptions.  return with error
                rft.printErr("Transport: Fatal exception trying to connect to rhost. Error:{}".format(e))
                return(9,r,False,None)
            else:  # if no exception
                rc=0
                # print the response status (-ssss)
                rft.printStatus(4,r=r,authMsg=authMsg)
                rft.printStatus(5,r=r,authMsg=authMsg)
                rft.printStatus(5,r=r)  # print the response data (-ssssss)
                
                if( r.status_code >= 400):
                   # xg TODO: handle case of authentication error
                    # if using Session auth, delete the session token and try again, the session may have timed-out
                    #    but check credential vault for new user/passwd in case that has changed
                    # if using Basic A uth, get user/passwd again from credential vault and try again
                    rft.printStatusErr4xx(r.status_code)
                    return(r.status_code,r,False,None)
                if( r.status_code == 302):
                    rft.printErr("Transport: Redirected: status_code: {}".format(r.status_code))
                    return(302,r,False,None)
                if( r.status_code==204):
                    success=True
                    return(rc,r,False,None)
                elif( (r.status_code==200) and (method=="HEAD") ):
                    success=True
                    return(rc,r,False,None)
                elif((r.status_code==200) or (r.status_code==201) ):  
                    if( loadJsonData is True):
                        try:
                            d=json.loads(r.text)
                        except ValueError:
                            rft.printErr("Transport: Error loading Data: uri: {}".format(url))
                            respd=None
                            rc=10
                            return(rc,r,False,None)
                    else:
                        d=r.text #xml data or flag to load json to dict was not set true
                        return(rc,r,jsonData,d)

                    #if here, no error, and its json data
                    if( (respd is None) and ( not "Members@odata.nextLink" in d)):
                        # normal case where single response w/ no next link
                        return(rc,r,loadJsonData,d)
                    elif( (respd is None ) and ("Members@odata.nextLink" in d)):
                        #then this is the 1st nextlink
                        respd=d
                        url=urljoin(urlBase2,d["Members@odata.nextLink"])
                        #dont return--keep looping
                    elif( not respd is None )and ("Members@odata.nextLink" in d):
                        # this is 2nd or later response-that has a nextlink
                        respd["Members"]= respd["Members"] + d["Members"]
                        url=urljoin(urlBase2,d["Members@odata.nextLink"])
                    elif( not respd is None )and (not "Members@odata.nextLink" in d):
                        # this final response to a multi-response request, and it has not nextlink
                        respd["Members"]= respd["Members"] + d["Members"]
                        return(rc,r,loadJsonData,respd)
                elif( r.status_code!=200):
                    success=False
                    rft.printErr("Transport: processing response status codes")
                    return(11,r,False,None)




    #login to rhost and get a session Id
    #authToken,sessionId=rft.rfSessionLogin()
    def rfSessionLogin(self,rft,cmdTop=False,cleanupOnExit=True):
        rft.printVerbose(4,"Transport: in SessionLogin")

        if( rft.SessionLoginUrl is None ):
            # get the root service
            rc,r,j,d=rft.rfSendRecvRequest('GET', rft.rootPath )
            if(rc!=0):
                rft.printErr("Error: SessionLogin: could not read service root to login session")
                return(rc,None,False,None)

            # get the URL of the Sessions  collection from the root service response
            if( d is  None ):
                rft.printErr("Error: SessionLogin: root service did not return response")
                return(rc,None,False,None)
            if( ("Links" in d) and ("Sessions" in d["Links"]) and ("@odata.id" in d["Links"]["Sessions"]) ):
                loginUri=d["Links"]["Sessions"]["@odata.id"]
                #save the sessionLoginUrl for next time
                rft.SessionLoginUrl=loginUri
            else:
                rft.printErr("Error: SessionLogin root service response does not have sessions collection")
                return(4,None,False,None)
        else:
            loginUri=rft.SessionLoginUrl

        # create the Credential structure:  { "UserName": "<username>", "Password": "<passwd>" }
        credentials={"UserName": rft.user, "Password": rft.password }
        loginPostData=json.dumps(credentials)

        # now we have a login uri,  login
        # POST the user credentials to the login URI, and read the SessionLink and SessionAuthToken from header
        rc,r,j,d=rft.rfSendRecvRequest('POST', rft.rootUrl, urlPath=loginUri, reqData=loginPostData)
        if(rc!=0):
            rft.printErr("Error: Session Login Failed: Post to Sessions collection failed")
            return(rc,None,False,None)        # save the sessionId and SessionAuthToken

        # SessionAuthToken is in header:     X-Auth-Token: <token>
        # the SessionLink is in header:      Location: <sessionLinkUrl>
        # the sessionId is read from the response: d["Id"]
        if( not "X-Auth-Token" in r.headers ):
            rft.printErr("Error: Session Login Failed: Post to Session collection did not return Session Token")
            return(4,None,False,None)
        if( not "Location" in r.headers ):
            rft.printErr("Error: Session Login Failed: Post to Session Collection did not return Link to session in Location hdr")
            return(4,None,False,None)

        #save auth token, sessionId, and sessionLink in transport database
        rft.authToken=r.headers["X-Auth-Token"]
        if( ( d is not None) and ( "Id" in d )):
                rft.sessionId=d["Id"]
        else:
            rft.printErr("Error: Session Login either didn't return the new session or property Id was missing ")
            return(4,None,False,None)
        rft.sessionLink=r.headers["Location"]
        rft.cleanupOnExit=cleanupOnExit
        
        rft.printStatus(3,r=r,addSessionLoginInfo=True)

        return(rc,r,j,d)
    

    
    def rfSessionDelete(self,rft,cmdTop=False,sessionLink=None):
        rft.printVerbose(4,"Transport: in Session Delete (Logout)")

        #if session link was passed-in (logout cmd) use that,  otherwise, use the saved value in the transport
        if(sessionLink is None):
            # delete this session saved in rft.sessionId, rft.sessionLink
            # delete in rft
            self.printVerbose(5,"rfSessionDelete: deleting session:{}".format(rft.sessionId))
            rft.printVerbose(4,"Transport: delete session: id:{},  link:{}".format(rft.sessionId, rft.sessionLink))
            sessionLink=rft.sessionLink
            
        # now we have a login uri,  login
        # POST the user credentials to the login URI, and read the SessionLink and SessionAuthToken from header
        rc,r,j,d=rft.rfSendRecvRequest('DELETE', rft.rootUrl, urlPath=sessionLink)
        if(rc!=0):
            rft.printErr("Error: Logout: Session Delete Failed: Delete to Sessions collection failed")
            rft.printErr("  sessionId:{}".format(sessionLink))
            return(rc,None,False,None)

        # save the sessionId and SessionAuthToken to None
        self.sessionId=None
        self.sessionLink=None
        rc=0
        return(rc,r,False,None)

    
    def rfCleanup(self,rft):       
        #if we created a temp session in this cmd, logout
        self.printVerbose(5,"rfCleanup:Cleaningup session: {}".format(self.sessionId))
        if((rft.cleanupOnExit is True ) and (rft.sessionId is not None) ):

            #delete the session
            rc,r,j,d=rft.rfSessionDelete(rft)
            #nothing else to do for now
            return(rc)
        else:
         return(0)


    # later we will update to do logging
    def printVerbose(self,v,*argv, skip1=False, printV12=True,**kwargs): 
        if(self.quiet is True):
            return(0)
        if( (v==1 or v==2) and (printV12 is True) and (self.verbose >= v )):
            if(skip1 is True):  print("#")
            print("#",*argv, **kwargs)
        elif( (v==1 or v==2) and (self.verbose >4 )):
            if(skip1 is True):  print("#")
            print("#",*argv, **kwargs)            
        elif((v==3 ) and (printV12 is True) and (self.verbose >=v)):
            if(skip1 is True):  print("#")
            print("#REQUEST:",*argv,file=sys.stdout,**kwargs)
        elif((v==4 or v==5) and (self.verbose >=v)):
            if(skip1 is True):  print("#")
            print("#DB{}:".format(v),*argv,file=sys.stdout,**kwargs)
        elif( v==0):  #print no mater value of verbose, but not if quiet=1
            if(skip1 is True):  print("")
            print(*argv, **kwargs)
        else:
            pass

        sys.stdout.flush()
        #if you set v= anything except 0,1,2,3,4,5 it is ignored


    # later we will update to do logging
    def printStatus(self, s, r=None, hdrs=None, authMsg=None, addSessionLoginInfo=False): 
        if(self.quiet is True ):
            return(0)
        if(   (s==1 ) and (self.status >= s ) and (r is not None) ):
            print("#STATUS: Last Response: r.status_code: {}".format(r.status_code))
        elif( (s==2 ) and (self.status >= s ) and (r is not None) ):
            print("#STATUS: Last Response: r.url: {}".format(r.url))
            print("#STATUS: Last Response: r.elapsed(responseTime): {0:.2f} sec".format(self.elapsed))
        elif( (s==3 ) and (self.status >= s ) and (r is not None) ):
            if( addSessionLoginInfo is True):
                print("#____AUTH_TOKEN:  {}".format(self.authToken))
                print("#____SESSION_ID:  {}".format(self.sessionId))
                print("#____SESSION_URI: {}".format(self.sessionLink))
            else:
                print("#REQUEST:  {}     {} ".format(r.request.method, r.request.url))
                print("#__Request.Headers:  {}".format(r.request.headers))
                print("#__Request AuthType: {}".format(authMsg))
                print("#__Request Data: {}".format(r.request.body))
                print("#__Response.status_code: {},         r.url: {}".format(r.status_code,r.url))
                print("#__Response.elapsed(responseTime): {0:.2f} sec".format(self.elapsed))
        elif( (s==4 ) and (self.status >= s ) and (r is not None) ):
            print("#__Response.Headers: {}".format(r.headers))
        elif( (s==5 ) and (self.status >= s )  ):
            print("#__Response. Data: {}".format(r.text))
        else:
            pass
            #if you set v= anything except 1,2,3,4,5 it is ignored
        sys.stdout.flush()
        



    # later we will update to do logging
    def printErr(self,*argv,noprog=False,prepend="",**kwargs):
        if(self.quiet is True):
            return(0)
        else:
            if(noprog is True):
                print(prepend,*argv, file=sys.stderr, **kwargs)
            else:
                print(prepend,"  {}:".format(self.program),*argv, file=sys.stderr, **kwargs)
        
            sys.stderr.flush()
            return(0)


    # later we will update to do logging
    def printStatusErr4xx(self, status_code,*argv,noprog=False, prepend="",**kwargs):
        if(self.quiet):
            return(0)
        if status_code is None:
            status_code=0
        if( status_code < 400 ):
            self.printErr("status_code: {}".format(status_code))
        else:
            if( status_code == 400 ):
                errMsg="Bad Request"
            elif( status_code == 401 ):
                errMsg="Unauthorized"
            elif( status_code == 402 ):
                errMsg="Payment Required ?"
            elif( status_code == 403 ):
                errMsg="Forbidden--user not authorized to perform action"
            elif( status_code == 404 ):
                errMsg="Not Found"
            elif( status_code == 405 ):
                errMsg="Method Not Allowed"
            elif( status_code == 406 ):
                errMsg="Not Acceptable"
            elif( status_code == 407 ):
                errMsg="Proxy Authentication Required"
            elif( status_code == 408 ):
                errMsg="Request Timeout"
            elif( status_code == 409 ):
                errMsg="Conflict"
            elif( status_code == 410 ):
                errMsg="Gone"
            elif( status_code == 411 ):
                errMsg="Length Required"
            elif( status_code == 412 ):
                errMsg="Precondition Failed"
            elif( status_code == 413 ):
                errMsg="Request Entity Too Large"
            elif( status_code == 414 ):
                errMsg="Request-URI Too Long"
            elif( status_code == 415 ):
                errMsg="Unsupported Media Type"
            elif( status_code == 416 ):
                errMsg="Requested Range Not Satisfiable"
            elif( status_code == 417 ):
                errMsg="Expectation Failed"
            elif( status_code < 500 ):
                errMsg=""
            elif( status_code >=500 ):
                errMsg="Internal Server Error"
            elif( status_code >=501 ):
                errMsg="Not Implemented"
            else:
                errMsg=""
            self.printErr("Transport: Response Error: status_code: {} -- {}".format(status_code, errMsg ))
            
        sys.stdout.flush()
        return(0)



    #parse the @odata.type property into {namespace, version, resourceType}  following redfish syntax rules
    # returns: namespace, version, resourceType.
    # If error parsing, returns None,None,None
    def parseOdataType(self,rft,resource):
        if not "@odata.type" in resource:
            rft.printErr("Transport:parseOdataType: Error: No @odata.type in resource")
            return(None,None,None)

        resourceOdataType=resource["@odata.type"]
    
        #the odataType format is:  <namespace>.<version>.<type>   where version may have periods in it 
        odataTypeMatch = re.compile('^#([a-zA-Z0-9]*)\.([a-zA-Z0-9\._]*)\.([a-zA-Z0-9]*)$')  
        resourceMatch = re.match(odataTypeMatch, resourceOdataType)
        if(resourceMatch is None):
            rft.printErr("Transport:parseOdataType: Error parsing @odata.type")
            return(None,None,None)
        namespace=resourceMatch.group(1)
        version=resourceMatch.group(2)
        resourceType=resourceMatch.group(3)
    
        return(namespace, version, resourceType)



# generic BMC Redfish Transport class -- which supports idrac and openBMC
#xg99
class BmcRedfishTransport(RedfishTransport):
    def __init__(self, rhost=None, isSimulator=False, debug=False, credentialsPath=None):
        # default timeouts, headers, and nextlinks used by THIS transport
        self.MaxNextLinks=10                # max number of requests allowed with NextLink
        self.dfltPatchPostPutHdrs = {'OData-Version': '4.0', 'Content-Type': 'application/json', 'Accept': 'application/json'  }
        self.dfltGetDeleteHeadHdrs = {'Accept': 'application/json', 'OData-Version': '4.0' }
        self.waitTime=3
        self.waitNum=1
        self.timeout=5 #http transport timeout in seconds, stored as int here
        self.unauthenticatedApiScheme="https"  # the scheme to use for unauthenticated APIs --http should always work
        if isSimulator is True:
            self.unauthenticatedApiScheme="http"  # when testing with Simulator or local, the iDrac mockup Server is http

        # default scheme, authType, and username/password
        self.scheme="https"      # the default scheme to use for this transport:  (https for idrac,    http for MC )
        if isSimulator is True:
            self.scheme="http"      # when testing with Simulator or local, the iDrac mockup Server is http
        self.auth="Basic"        # AuthN to use:    ("None" for MC,  "Session" or "Basic" for idrac)
        self.user="root"        # get from credential vault, (this is the default)
        self.password="calvin"  # get from credential vault, (this is the default)
        self.SessionLoginUrl="/redfish/v1/SessionService/Sessions" # URI where Sessions collection is for session login
        self.program = "BmcRedfishTransport"
        # set paths to credential vault for this transport
        #self.credentialsPath="/etc/opt/dell/rm-tools/Credentials/bmcuser/.passwd" # BMC password
        self.credentialsPath=credentialsPath

        # if running isSimulator with Simulator, we use default passwords--there is no credential vault
        if isSimulator is True:
            self.credentialsPath=None

        # session auth parameters stored here for when Session Auth is used
        self.sessionId=None
        self.sessionLink=None
        self.authToken=None
        self.cleanupOnExit=True   # if true, the session will be deleted whenever self.rfCleanup(rft) is called

        # root paths for the session
        self.rhost=None          # specify this in transport if using a common rhost for this transport
        self.rootPath="/redfish/v1/"

        # verbose and status flags used for debug print and logging filtering 
        self.verbose=0
        self.status=0
        self.quiet=True
        if isSimulator is True:
            self.quiet=False
        # if debug flag set, set quiet=False, and set verbose=3, status=5
        if debug is True:
            self.verbose=3
            self.status=5
            self.quiet=False

        # disable urllib print warning
        requests.packages.urllib3.disable_warnings()

        # measured execution time
        self.elapsed=None

        # calculate self.rhost based on passed-in rhost
        self.rfConnectionInit(rhost=rhost)

        # load the credential file into the user, password property at self.user, self.password
        self.rfGetCredentialsFromVault()


# end

