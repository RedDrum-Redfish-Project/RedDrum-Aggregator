#    Copyright 2017 Dell, Inc. All rights reserved.

#Support of IPMI commands over LAN via the pyghmi module.
# :depends: Python module pyghmi.
# :configuration: The following configuration defaults can be
#     changed within the /etc/opt/dell/rm-tools/Credentials/bmcuser/.passwd file:


import os
import sys
'''
xg removing pyghmi dependencies
import ctypes
import cmd
import re
import ctypes
import ctypes
from cmd import Cmd
from enum import Enum,IntEnum
from collections import OrderedDict
from pyghmi.ipmi import command
from pyghmi.ipmi.private import session 
'''



class IpmiTransport():
    '''
    ipmiTransport is an object to handle interactions with a BMC's IPMI functions
    '''
    def __init__(self, isLocal=False, debug=False):


        # verbose and status flags used for debug print and logging filtering 
        self.verbose=0
        self.status=0
        self.quiet=True
        if isLocal is True:
            self.quiet=False

        # if debug flag set, set quiet=False, and set verbose=3, status=5
        if debug is True:
            self.verbose=3
            self.status=5
            self.quiet=False

    def ipmiConnConfig(self, rhost=None):
        '''
        Return configuration
        '''
        self.api_login_timeout=2
        if rhost is None:
            self.bmc="localhost"
        else:
            self.bmc=rhost
        #print(self.bmc)
    

    def ipmiGetCredentialsFromVault(self):
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
            self.userid,self.password=creds[0]
            return(0)
    
    def ipmiRawSendReceive(self, netFn, cmd, reqData=None ):
         
        '''     
        ipmiRawSendReceive - send a raw ipmi command
        :param netFn: NetFun number (e.g. 6)
        :param cmd: Command number (e.g. 1) 
        :param subCmd: SubCommand number (e.g. 4) 
        :param reqDataCmdStruct: Redfish Data Command Structure if required (List)
        return rc, ipmiCompletionCode, rawResponseData
        rc=0 if success, non-zero if error
        ''' 

        rc=1
        self.netFn=netFn
        self.cmd=cmd
   
        self.reqData=reqData
        if reqData is None:
            self.reqData=''
                           
        #Send in data to be processed as an ipmi raw request
        '''
        xg removing pyghmi dependencies
        try: 
            with _IpmiSession(bmc=self.bmc, userid=self.userid, password=self.password) as s:
                rc = s.raw_command(netfn=int(netFn),
                                   command=int(cmd), 
                                   data=map(lambda x: int(str(x), 16), self.reqData[2:]))
        #Unfortunately, pyghmi sends generic exceptions so we'll have to catch em
        except Exception as e:
            if "timeout" in str(e):
                print("IPMI Transport: connectionTimeout Error: %s, check network stack" % e)
                return(-2,rc,False)
            if "password" in str(e):
                print("IPMI Transport Error: %s, check credentials" % e)
                return(-3,rc,False)
            else:
                raise Exception("IPMI Transport: Unknown Exception: %s" % e)
        return(0,rc['code'],rc['data'])
        '''

        return(0,0,None)
        

    # ipmiDcsRedFishApis - send a DCS Wrapper IPMI Command
    # Request Properties:
    #   subCmd=  <the specific wrapper subcommand>
    #         =0x02 --getSystemInfo
    #         =0x05 --getMemoryInfo
    # 
    # reqDataCmdStruct required by some commands (e.g. Memory Info "index")
    #
    # Returns: rc, ipmiStatusCode, responseData
    #    rc = 0 if no error
    #    ipmiCompletionCode = None, or the IPMI Completion code (CC) returned by the remote node
    #    responseData = None if no data returned, or a raw byte array equal to the IPMI response data
    #
    # Calls the underlying ipmiRawSendReceive() method to execute
    #     netFn=48# OEM IPMI Cmd space
    #     cmd=200# DCS Wrapper COmmand number
    def ipmiDcsRedFishApis(self, subCmd=None, reqDataCmdStruct=None):
        netFn=48 # I think you have to shift this...
        cmd=200
        setgetCmd=1
        self.netFn=netFn
        self.cmd=cmd

        if subCmd is None:
            return(-1,None,None)   # invalid subcommand None
        if (subCmd != 5) and (subCmd != 2):
            return(-2,None,None)   # invalid subcommand
        if (subCmd==5) and (reqDataCmdStruct==None):
            return(-3,None,None)   # request data required

        #build list of parameters
        self.subCmd=subCmd
        self.setgetCmd=1  #Read-Only always for these Static API's
        self.dlength=2
        self.dlength2=0
        self.offset=0
        self.offset2=0

        self.rfReqWrapData=[self.netFn, self.cmd, self.setgetCmd, self.subCmd, format(self.dlength,'x'), self.dlength2, self.offset, self.offset2]
        if (subCmd==5): #OR for every API that requires it
            self.reqDataCmdStruct=reqDataCmdStruct
            #print(self.reqDataCmdStruct)

            self.rfReqWrapData+=self.reqDataCmdStruct
            #print(self.rfReqWrapData)

        #first get length of response
        rc,completionCode,rfRespData = self.ipmiRawSendReceive( netFn, cmd, reqData=self.rfReqWrapData)

        #print(rfRespData)
        #should we raise an exception instead
        if completionCode != 0:
            return(-1,completionCode,rfRespData)  # error sending request IPMI Command

        #Set length to packet size
        #print("Second call to ipmi library")
        self.rfReqWrapData[4]='{:x}'.format(rfRespData[5])

        #Then get all data
        rc,ipmiCompletionCode,rfRespData = self.ipmiRawSendReceive(netFn, cmd, reqData=self.rfReqWrapData)

        if ipmiCompletionCode != 0:
            return(-2,ipmiCompletionCode,rfRespData)  # error sending request IPMI Command
 
        if (subCmd==2): 
            rfSystemInfoRaw=rfSystemInfo(rfRespData)
            dictResp=rfSystemInfoRaw.createResp()
            #ipmiCompletionCode=rfRespData['code']
            #print(dictResp)

        else:
            rfMemoryInfoRaw=rfMemoryInfo(rfRespData)
            dictResp=rfMemoryInfoRaw.createResp()

        return(0, ipmiCompletionCode, dictResp)


    def printErr(self,*argv,noprog=False,prepend="",**kwargs):
        if( self.quiet == False):
            if(noprog is True):
                print(prepend,*argv, file=sys.stderr, **kwargs)
            else:
                print(prepend,"  {}:".format(self.program),*argv, file=sys.stderr, **kwargs)
        else:
            pass
        
        sys.stderr.flush()
        return(0)



    # ==================================================================================

    # 
    # higher level IPMI Library commands
    #  --------------------------------------------
    # these functions all use ipmiRawSendReceive to send the commands, and return python Dict response
    # response is rc (0=success), completionCode (ipmiCompletionCode), dataIsDict (True/False),  responseData
    #   where if success: rc=0,  dataIsDict=True, responseData=python dictionary
    #   if error,         rc>0,  dataIsDict=False, responseData=None usually

    def getSysGUID(self):
        self.ipmiRawSendReceive(netFn=6, cmd=37)
    # send getDeviceId command to BMC
   
    def getDeviceId(self,stub=None):
        # build request for getDeviceId
        # ...

        # send getDeviceId from low-level lib
        # ...

        # handle response:
        # ...

        # turn resonse into python Dict
        # FOR 1.1, we probably will use as a ping and not actually look at resp
        #
        rc=1
        resp=dict()

        if stub is not True:
            rc,completionCode,dictResp=self.ipmiRawSendReceive(netFn=6, cmd=1, stub=stub)
            #print(dictResp)

        if(rc!=0):
            if stub is True:
                # return static hard coded data here for integration with front-end
                resp["DeviceId"]= "byte2"
                resp["HwRevision"]= "byte3"
                resp["FwRevision"]= "fromm byte4, byte5"
                resp["IpmiVersion"]="2.0" #or from byte 6
                resp["Additional"]= "byte7"
                resp["Manufacturer"]="bytes 8-10"
                resp["ProductId"]="byptes 11-12"
                resp["AuxFwRev"]="bytes 13-16"
                rc=0
                completionCode=0
                return(rc, completionCode, resp)

            else: 
                return(rc, completionCode, dictResp)

        if(rc==0):
            resp["DeviceId"]=dictResp[1]
            resp["HwRevision"]=dictResp[2]
            resp["FwRevision"]=dictResp[3]
            resp["IpmiVersion"]=dictResp[5]
            resp["Additional"]=dictResp[6]
            resp["Manufacturer"]=dictResp[7]
            resp["ProductId"]=dictResp[10]
            resp["AuxFwRev"]=dictResp[12]
         
            return(rc, completionCode, resp)

    #  --------------------------------------------
    # later we will update to do logging
    
    def printVerbose(self,v,*argv, skip1=False, printV12=True,**kwargs): 
        if(self.quiet):
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

    def printErr(self,*argv,noprog=False,prepend="",**kwargs):
        if( self.quiet == False):
            if(noprog is True):
                print(prepend,*argv, file=sys.stderr, **kwargs)
            else:
                print(prepend,"  {}:".format(self.program),*argv, file=sys.stderr, **kwargs)
        else:
            pass
        
        sys.stderr.flush()
        return(0)

'''
xg removing pyghmi dependencies
class _IpmiSession(object):
    def __init__(self, bmc, userid, password):
        self.o = session.Session(bmc,
                                 userid,
                                 password,
                                 onlogon=self._onlogon)
        while not self.o.logged:
            self.o.maxtimeout = 5 
            self.o.wait_for_rsp(timeout=1)
        self.o.maxtimeout = 5

    def __enter__(self):
        return self.o

    def __exit__(self, type, value, traceback):
        if self.o:
            self.o.logout()

    def _onlogon(self, response):
        if 'error' in response:
            raise Exception(response['error'])
'''

#Class to hold iDRAC IPMI requests specific to Dell hardware
class BmcIpmiTransport(IpmiTransport):
    def __init__(self, rhost=None, isLocal=False, scArgs=None):

        self.credentialsPath="/etc/opt/dell/rm-tools/Credentials/bmcuser/.passwd" # BMC password
        if scArgs is not None:
            self.netFn=scArgs[1]
            self.cmd=scArgs[2]

        self.userid="root"        # get from credential vault, (this is the default)
        self.password="calvin"  # get from credential vault, (this is the default)
        # verbose and status flags used for debug print and logging filtering 
        self.verbose=0
        self.status=0
        self.quiet=False

        self.ipmiConnConfig(rhost=rhost) 
        self.ipmiGetCredentialsFromVault()



    # get System Information
    def getSystemInfo(self,stub=None):
        #print("EEEEEEEEEEEEEEEEEEstub: {}".format(stub))
        # build request:
        rc=1
        #send request to be processed
        if stub is not True:
            rc,completionCode,dictResp=self.ipmiDcsRedFishApis(subCmd=2)

        if(rc!=0):
            if stub is True:
                dictResp=dict()
                dictResp["Name"]="iDRAC Redfish System Information"
                dictResp["ResponseVersion"]=1           # 1st byte of raw 
                dictResp["NumOfParams"]=9               # 2nd byte
                dictResp["BootSrcTargAllowableValues"]= ["None","Pxe", "BIOSSetup"]   # turn bitmask into python list
                dictResp["ResetAllowableValues"]= ["On", "ForceOff", "GracefulShutdown"] # turn bitmask into python list
                dictResp["ProcessorCount"]=2             #ex 2, uint8 in dictResponse...
                dictResp["ProcessorModel"]=None          #string with processor model
                dictResp["TotalSystemMemorySize"]=None   #uint16 in dictResponse
                dictResp["NumOfDIMMs"]=4                 # uint8 in dictResponse--the number of DIMMS
                dictResp["NumOfNICs"]=2                 # uint8 in dictResp--the number of NICs
                dictResp["NumOfSimpleStorageCntrlr"]=2   #uint8 in dictResp, the number of Simple storage controllers
                dictResp["NumOfStorageCntrlr"]=0         #uint8 in dictResp, the number of "Storage Controllers" typ 0 now
                rc=0
                completionCode=0

            return(rc, completionCode, dictResp)
                      
        if(rc==0):
            dictResp["Name"]="iDRAC Redfish System Information"
            return(rc, completionCode, dictResp)
      
       
    # get Memory Info
    def getMemoryInfo(self,index,stub=None):
        rc=1
        reqDataCmdStruct=['{:x}'.format(index)]
        #send request to be processed
        if stub is not True:
            rc,completionCode,dictResp=self.ipmiDcsRedFishApis(subCmd=5, reqDataCmdStruct=reqDataCmdStruct)

        #Add required attribute "Name"

        if(rc!=0):
            if stub is True:
                dictResp=dict()
                dictResp["Name"]="DIMM {}".format(index)
                dictResp["ResponseVersion"]=1        # 1st byte of raw 
                dictResp["NumOfParams"]=0x10         # 2nd byte
                dictResp["Index"]=index             # we expect this index in dictResponse the same as request
                dictResp["MemoryType"]="DRAM"        # previouly called "MemoryType"
                dictResp["ErrorCorrection"]= None    # null or MultiBitECC"?
                dictResp["MemoryDeviceType"]="DDR4"  # previously "DIMMTechnology" 
                dictResp["RankCount"]= 2             # previously called "Rank"
                dictResp["MinVoltage"]= 1.2          # get from MinVOltagex100 and divide by 100. a json number
                dictResp["DataWidthBits"]= 64        # json  number
                dictResp["BusWidthBits"]= 72         # previously "TotalWidth" 
                dictResp["CapacityMiB"] = 16384      # previously "SizeMB"
                dictResp["OperatingSpeedMHz"]=2133                       # previously "SpeedMHz"
                dictResp["DeviceLocator"]="DIM.Socket.A1"                # previously called "SocketLocator"
                dictResp["Manufacturer"]="Yynix Semiconductor"
                dictResp["SerialNumber"]="238759C8"
                dictResp["PartNumber"]= "HMA426R7MFR4N-TF"
                dictResp["Status"]={"State": "Enabled", "Health": "OK"}  # create complex type from status structure
                rc=0
                completionCode=0

            return(rc, completionCode, dictResp)
                      
        if(rc==0):
            dictResp["Name"]="DIMM {}".format(index)
            return(rc, completionCode, dictResp)
            
    # get Internal Variable POST Code
    # this is called to read the last POST code the idrac has received
    
    def getLastPostCode(self):
        # build request:
        netFn=0x30  # I think you have to shift this...
        cmd=0x27
        reqData=0x01 # tell the iDrac to return lastPostCode

        #send request to ipmiRawSendReceive()
        #rc,completionCode,rawData=ipmiRawSendReceive(netFn, cmd, reqData ) # pass-in index

        resp={}
        # create response
        if(rc == 0):
            resp["LastBiosPostCode"]=xx  # byte2 of response   (byte1 of response was ipmi completion code
        
        # send response
        return(rc,completionCode, True, resp)
        



