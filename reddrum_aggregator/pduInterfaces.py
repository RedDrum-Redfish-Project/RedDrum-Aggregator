
import sys
import os
import subprocess
from subprocess import Popen, PIPE
import json
import ipaddress

class RdAggrPDUlinuxInterfaces():
    def __init__(self,rdr):
        self.rdr = rdr
        self.x = 1

    # Send a RESEAT Command to the smart PDU that powers the Rack Servers
    # the method runs a script that uses telnet/ssh to send commands to the PDU
    # It is used to execute the server Reseat by executing a power-off and then power-on 
    #    to a PDU socket to effectively "reseat" the server
    #
    # Input parameters:
    #     chasId -- a string that identifies the server - same as switch port 
    #
    # The routine uses Popen to run the script and returns: 
    #    1) the script exit code, -- so the script should ALWAYS exit with bash command "exit <exitcode>"
    #         -- exitcode = 0 if success. 
    #         -- exitcode = non-0 results in a 500 error to the rest api
    #    2) stdout   -- used to send response data in form of a proper Json Struct.  send {} if no output
    #    3) stderr.  -- may be used for error and debug
    #
    # The routine runs a script that was specified in aggregatorConfig to reseat the server using a PDU
    #   pduSocketId was loaded from the discovery file eg discovery_hwTestRack2.json to map svrId into socketId
    #
    def reseatRackServer(self, chasId ):
        if chasId not in self.rdr.root.chassis.chassisDb:
            self.rdr.logMsg("ERROR","...reseatRackServer: invalid chasId")
            return(9)
        resDb=self.rdr.root.chassis.chassisDb[chasId]

        # get the full path to the pduReseat script --this has already been verified to exist during discovery
        wrapperScriptPath = self.rdr.backend.backendPduReseatWrapperFilePath
        arg1 = self.rdr.backend.backendPduReseatScriptApp  # the app used by pduWrapper.sh to execute the script
        # the app may by "bash", "python3", "python2", etc
        arg2 = self.rdr.backend.backendPduReseatScriptPath # the full path to the pduReseat script to run 

        # get the pduSocketId -- the string that represents a specific pdu socket id. 
        arg3 = resDb["PduSocketId"]  # the pduSocketId 

        #run the script
        proc = Popen([wrapperScriptPath,arg1,arg2,arg3],stdout=PIPE,stderr=PIPE)
        out,err=proc.communicate()
        exitcode=proc.returncode
        #print("STDERR: {}".format(err))
        #print("STDOUT: {}".format(out))

        # handle error case running script
        if exitcode != 0:
            return(exitcode, None)
        else:
            return(0,None)        

        # if later versions of scripts return output in json format to stdout:
        #  load to a json struct
        # getOutputString = str(out, encoding='UTF-8')   # convert output from bytes to utf8 string. 
        #print("OUTSTRING: {}".format(getOutputString))
        #response=json.loads(getOutputString )
        #return(exitcode,response)

