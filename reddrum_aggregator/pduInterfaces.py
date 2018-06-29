
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

    # Send Command to the smart PDU that powers the Rack Servers
    # the method runs a script that uses telnet/ssh to send commands to the PDU
    # It is used to execute the server Reseat by executing a power-off and then power-on 
    #    to a PDU socket to effectively "reseat" the server
    # Other PDU commands may be added to power-on, power-off, or read-power from the socket
    # If the script takes a long time to run, it should return and run a subshell in background
    #
    # Input parameters:
    #     chasId -- a string that identifies the server - same as switch port 
    #     chasBmcNetloc -- string that is the netloc (IPaddr[:<port>] to the server's BMC
    #     pduSocketId -- a string that MAY be used by the script to id a specific pdu socket
    #     pduCommand  -- a string that indicates the command to the PDU.  pduCommands include:
    #         "RESEAT" -- power-off then power-on the server
    #          ...
    #   If pduSocketId is not specified then an empty string ("") is passed to the script
    #        and the script must lookup the pdu based on chasId and chasBmcNetloc
    #   pduSocketId and chasId cannot both be None/""
    #
    # The routine uses Popen to run the script and returns: 
    #    1) the script exit code, -- so the script should ALWAYS exit with bash command "exit <exitcode>"
    #         -- exitcode = 0 if success. 
    #         -- exitcode = non-0 results in a 500 error to the rest api
    #    2) stdout   -- used to send response data in form of a proper Json Struct.  send {} if no output
    #    3) stderr.  -- may be used for error and debug
    def reseatRackServer(self, chasId, bmcNetloc, pduSocketId, pduCommand):
        exitcode = 5
        response={}
        print("AAAAAAAAAAAAAA")

        if chasId is None and pduSocketId is None:
            return(exitcode,response)
        if pduCommand is None:
            return(exitcode,response)

        if pduSocketId is None:
            pduSocketId = ""
        if chasId is None:
            chasId = ""
        if bmcNetloc is None:
            bmcNetloc = ""

        print("AAAAAAAAAAAAAA")

        #return(exitcode,protoInfo)
        scriptPath = os.path.join(self.rdr.backend.backendScriptsPath, "pduApiScript.sh")
        arg1 = chasId # string that represents the chassis Id -- same as switch port num
        arg2 = bmcNetloc # string that represents the netloc eg: 127.0.0.1:3333 or 192.0.3.3 
        arg3 = pduSocketId # string that represents a specific pdu socket id. 
        arg4 = pduCommand  # string that represents a specific command sent to the PDU script. 
        arg5 = self.rdr.backend.backendScriptsPath # path to dir with scripts

        print("AAAAAAAAAAAAAA")
        #run the script
        proc = Popen([scriptPath,arg1,arg2,arg3,arg4,arg5],stdout=PIPE,stderr=PIPE)
        out,err=proc.communicate()
        exitcode=proc.returncode
        print("STDERR: {}".format(err))
        print("STDOUT: {}".format(out))

        print("BBBBBBBBBBBBBB")
        # handle error case running script
        if exitcode != 0:
            response={}
            return(exitcode,response)

        print("BBBBBBBBBBBBBB")
        
        # else process the output
        #  getObmcProtocolInfo.sh outputs a json response structure with properties 
        #  load to a json struct
        getOutputString = str(out, encoding='UTF-8')   # convert output from bytes to utf8 string. 
        print("OUTSTRING: {}".format(getOutputString))
        response=json.loads(getOutputString )
        return(exitcode,response)

