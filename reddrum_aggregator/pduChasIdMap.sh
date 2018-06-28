#!/bin/sh
# the 1st three entries identify the PDU netloc, user, passwd
XPDU_netloc=192.168.9.1
XPDU_username="apc"
XPDU_password="apc"
# the remaining entries map chasId to PDUsocket ID
#    the chasId env var has prefix "XSVR_"
#    the pduSocketId is the value--no prefix
# ie below:   chasId: svr1   --> maps to --> pduSocketId: PDU_SOCKET_1
XSVR_svr1=PDU_SOCKET_1
XSVR_svr2=PDU_SOCKET_3
