#!/bin/sh
# Copyright Notice:
#    Copyright 2018 Dell, Inc. All rights reserved.
#    License: BSD License.  For full license text see link: https://github.com/RedDrum-Redfish-Project/RedDrum-OpenBMC/LICENSE.txt
#
# TO TEST: run:
# include script  pduChasIdMap.sh  in same directory as pduApiScript.sh in order to do the chasId to pduSocket mapping
#  bash pduApiScript.sh  svr1 127.0.0.1:3006   PDU_SOCKET_1   DEBUG  # to echo back args 
#  bash pduApiScript.sh  svr1 127.0.0.1:3006   ""   DEBUG            # to map svr1 to pdu socket and do mapping
#  bash pduApiScript.sh  svr1 127.0.0.1:3006   ""   RESEAT           # to map svr1 to pdu socket do RESEAT

# assign args
chasId=$1
bmcNetloc=$2
pduSocketId=$3
pduCommand=$4
mapFilePath=$5

function reseat_command { 
  PDUCMD=$1
  username=$2
  password=$3
  pdu_timeout=1
  expect <<- DONE
  set timeout $pdu_timeout
  spawn $PDUCMD 
  expect {
      timeout         { send_user "timeout-during-login   " }
      "*ser Name*"    { send "${username}\r"; exp_continue }
      "*assword*"     { send "${password}\r"; exp_continue }
      "*apc>*"        
  }

  send "olOff ${pduSocketId}\r"
  expect {
      timeout         { send_user "timeout-after-olOff   " }
      "*apc>*" 
  }
  sleep 2
  send "olOn ${pduSocketId}\r"
  expect {
      timeout         { send_user "timeout-after-olOn   " }
      "*apc>*"
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
source ${mapFilePath}/pduChasIdMap.sh
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
    echo "Run RESEAT cmd" >&2  #debug to stderr
    # power off and on
    #PDUCMD="ssh ${pduNetloc}"
    PDUCMD="telnet ${pduNetloc}" 
    reseat_command "$PDUCMD" "${pduUsername}" "${pduPassword}" 1>&2
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


