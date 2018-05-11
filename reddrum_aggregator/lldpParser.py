
class RfaLldpApis():
    def __init__(self):

        self.magic=1


    # parse an input file that has form of the output of:  lldpcli show neighbors
    # and creates a rackServersDiscoveryDict of form:
    #     { "Environment": "FromLldpCliShowNeighbors",
    #     "RackServers": [
    #        { "Id": "svr1", "IPv4Address": "192.168.1.101"  },
    #        { "Id": "svr2", "IPv4Address": "192.168.1.101"  }
    #        ] }
    # returns rc, rackServersDiscoveryDict.
    # if error, rc is non-zero
    def parseLldpShowNeighbors(self):
        resp=dict()
        rc=-9
        return(rc,resp)

