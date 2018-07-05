#!/bin/sh
# Copyright Notice:
#    Copyright 2018 Dell, Inc. All rights reserved.
#    License: BSD License.  For full license text see link: https://github.com/RedDrum-Redfish-Project/RedDrum-OpenBMC/LICENSE.txt
#
# TO TEST: run:
# include script  pduChasIdMap.sh  in same directory as pduApiScript.sh in order to do the chasId to pduSocket mapping
#                       <chasId> <bmcNetloc>      <socketId>    <pduCmd> <mapFilePath> <runEnv>
#  bash pduApiScript.sh  svr1    127.0.0.1:3006   PDU_SOCKET_1   DEBUG   ""            ""  # debug and specify socketId
#  bash pduApiScript.sh  svr1    127.0.0.1:3006   ""             DEBUG   ""                # debug and map socketId
#  bash pduApiScript.sh  svr1    127.0.0.1:3006   ""             RESEAT  ""                # reseat and map socketId

# assign args
chasId=$1
bmcNetloc=$2
pduSocketId=$3
pduCommand=$4
mapFilePath=$5
runEnv=$6  # Simulator or Rack
if [ "${runEnv}" == "Simulator" ]; then
   userPrompt="login:"
   passwdPrompt="assword:"
   cmdPrompt="apc>"
else
   userPrompt="ser Name"
   passwdPrompt="assword"
   cmdPrompt="apc>"
fi

function reseat_command { 
  PDUCMD=$1
  username=$2
  password=$3
  pdu_timeout=5
  expect <<- DONE
  set timeout $pdu_timeout
  spawn $PDUCMD 
  # first: wait for userPrompt, then send username
  expect {
      timeout              { send_user "timeout-waiting for user login prompt" }
      "*${userPrompt}*"    
  }
  send "${username}\r"

  # second: wait for passwdPrompt, then send password
  expect {
      timeout                { send_user "timeout-waiting for password prompt" }
      "*${passwdPrompt}*"    
  }
  send "${password}\r"; 

  # third: wait for cmdPrompt, then send olOff
  expect {
      timeout                { send_user "timeout-waiting for cmdPrompt after sending login" }
      "*${cmdPrompt}*"        
  }
  send "olOff ${pduSocketId}\r"

  # fourth: wait for cmdPrompt, then send ofOn
  expect {
      timeout         { send_user "timeout-waiting for cmdPrompt after sending olOff   " }
      "*${cmdPrompt}*"        
  }
  sleep 2
  send "olOn ${pduSocketId}\r"

  # fifth
  expect {
      timeout         { send_user "timeout-waiting for cmdPrompt after sending olOn   " }
      "*${cmdPrompt}*"        
  }
DONE
}


# if both chasId and pduSocketId are null, we have an error
if [ "${chasId}" == "" -a "${pduSocketId}" == "" ]; then
        echo "ERROR both chasId and pduSocketId are empty" >&2  # print debug msg to stderr
        exit 5
fi

# source the pdu map file to get pdu outlet to server mappings as well as pdu netloc
if [ "${mapFilePath}" == "" ]; then
    mapFilePath="."
fi
source ${mapFilePath}/pduChasIdMap.sh ${runEnv}
pduNetloc=${XPDU_netloc}
pduUsername=${XPDU_username}
pduPassword=${XPDU_password}

#if pduSocketId is null, map the socketId to the svrId
if [ "${pduSocketId}" == "" ]; then
        # use a separate PDU database to map the pduSocket to 
        echo "Mapping chasId to pduSocketId" >&2  #debug to stderr
        mapSvrId="XSVR_${chasId}"
        pduSocketId=${!mapSvrId}
        echo "chasId: ${chasId}, pduSocketId: ${pduSocketId}" >&2 #debug to stderr
fi 
#pduCommand="DEBUG"

# now process the different commands
if [ "${pduCommand}" == "RESEAT" ]; then
    echo "_Run RESEAT cmd" >&2  #debug to stderr
    # power off and on
    #PDUCMD="ssh ${pduNetloc}"
    PDUCMD="telnet ${pduNetloc}" 
    reseat_command "$PDUCMD" "${pduUsername}" "${pduPassword}" 1>&2
    echo _DONE >&2
    # return empty dict to stdout and exit with exit code 0 if no error
    echo "{}"
    exit 0

elif [ "${pduCommand}" == "DEBUG" ]; then
    echo "Run DEBUG cmd" >&2  #debug to stderr
    echo "{"
    echo "    \"ChasId\":      \"${chasId}\","
    echo "    \"PduSocketId\": \"${pduSocketId}\","
    echo "    \"PduCommand\":  \"${pduCommand}\","
    echo "    \"BmcNetloc\":  \"${bmcNetloc}\","
    echo "    \"PduNetloc\":  \"${pduNetloc}\""
    echo "}"
    exit 0
    
else
    echo "INVALID COMMAND" >&2  #debug to stder
    echo "{}"
    exit 6
fi


