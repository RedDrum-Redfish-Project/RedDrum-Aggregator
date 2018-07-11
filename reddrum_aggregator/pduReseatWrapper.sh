#!/bin/sh
# wrapper to call utility to reseat the server using smart PDU
# $1 is the path where the scripts are
# $2 is the script to run -- which may include a utility and script like: python2 scriptname
# $3 is the socketId
scriptPath=$1
pduReseatScript=$2
pduSocketId=$3  
cd ${scriptPath}
${pduReseatScript} ${pduSocketId}
rc=$?
exit $rc
