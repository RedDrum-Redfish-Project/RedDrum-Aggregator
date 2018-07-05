#!/bin/sh
runEnv=$1  # "Simulator" or "Rack"
# the 1st three entries identify the PDU netloc, user, passwd
#XPDU_netloc=192.168.9.1
if [ "${runEnv}" == "Simulator" ]; then
  # simulator settings
  XPDU_netloc=127.0.0.1
  XPDU_username="apc"
  XPDU_password="apcapcapc"
else
  # Hardware Rack PDU settings
  XPDU_netloc=192.168.21.29
  XPDU_username="apc"
  XPDU_password="apc"
fi
# the remaining entries map chasId to PDUsocket ID
#    the chasId env var has prefix "XSVR_"
#    the pduSocketId is the value--no prefix
# ie below:   chasId: svr1   --> maps to --> pduSocketId: 1
XSVR_svr1=1
XSVR_svr2=2
XSVR_svr3=3
XSVR_svr4=4
XSVR_svr5=5
XSVR_svr6=6
XSVR_svr7=7
XSVR_svr8=8
XSVR_svr9=9
XSVR_svr10=10
XSVR_svr11=11
XSVR_svr12=12
XSVR_svr13=13
XSVR_svr14=14
XSVR_svr15=15
XSVR_svr16=16
XSVR_svr17=17
XSVR_svr18=18
XSVR_svr19=19
XSVR_svr20=20
