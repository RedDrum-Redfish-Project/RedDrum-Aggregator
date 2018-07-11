#!python2
import telnetlib
import time
import sys

if len(sys.argv) < 2:
    sys.stdout.write("Invalid number of args\n\r")
    sys.exit(5) # exit non-zero if error

pduIp = '127.0.0.1'
oloff = 'olOff '
olon  = 'olOn '

outlet = sys.argv[1]

tn = telnetlib.Telnet(pduIp)
#tn.set_debuglevel(9)

tn.read_until("login: ",20)
tn.write('apc' + '\r\n')
tn.read_until("Password: ",20)
tn.write('apcapcapc' + '\r\n')

tn.read_until("apc>",20)

#Reseat by turning off and turning back on
tn.write(oloff + outlet + '\r\n')
tn.read_until("apc>",20)

time.sleep(1)

tn.write(olon + outlet + '\r\n')
tn.read_until("apc>",20)

# exit code 0 to shell for success
sys.exit(0)
