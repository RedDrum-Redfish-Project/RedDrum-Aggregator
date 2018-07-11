
class RfaConfig():
    def __init__(self):
    
        # RACK CONFIG
        # -redfishAggregatorIsInsideSwitch= OneOf( True, False )
        #    set to false to model case where Aggregator is in a separate server--not inside mgt switch
        #    set to true if running on switch as container or venv
        self.redfishAggregatorIsInsideSwitch=False
    
        # DISCOVERY
        # -discoverRackServersFrom= OneOf( "LLDP", <a json resource filename in this directory> )
        #    if "LLDP", the "lldpcli show neighbors " output is used to get list of discovered servers
        #       --see also useTestLldpOutputFile property below
        #    else, discovery will try to open a file in backend directory with list of static rack servers
        #       --see example files for test below
        self.discoverRackServersFrom="discovery_simulator2.json"   # two simulated iDracs running on ports 8001,8002
        #self.discoverRackServersFrom="discovery_hwTestRack2.json" # a small rack of real hardware-2 servers
        #self.discoverRackServersFrom="discovery_hwTestRack8.json" # a small rack of real hardware-8 servers
    
        # TEST CONFIG
        # - useTestLldpOuptutFile= OneOf( True,False )
        #     if True, when discoverRackServersFrom is set to "LLDP", 
        #       the file testLldpOuptutFile.txt is used in place of querying LLDP directly
        #     if False, the LLDPd on the Mgt Switch is queryed for list of neighbors attached to ports
        self.useTestLldpOuptutFile=False
    
        # - isRackSim= OneOf( True,False)
        #     if true, the Redfish transport makes accomadations for everything to be simulated
        self.isRackSim=True
        #self.isRackSim=False
    
        # GENERAL API SETTINGS
        self.includeRackScaleOemProperties=True

        # PDU Reseat Script -- this scriptname for the top-level bash wrapper script used to reseat a server chassis
        #   one arg is passed:  SocketId
        self.pduReseatScript="python2 pduReseatScript-sim.py"
        #self.pduReseatScript="python2 pduReseatScript-apc.py"

        # CREDENTIALS File -- contains credential IDs
        self.bmcCredentialsFile="bmcCredentials-sim.json"
        #self.credentialsFile="bmcCredentials-idrac.json"
    
        # RACK ENCLOSURE RESOURCE SETTINGS -- should move somewhere else if we keep them
        self.rackModelNumber=""
        self.rackManufacturer="Dell"
        self.rackSerialNumber=None
        self.rackAssetTag=None
        self.rackChasId="Rack1"
    
        # MANAGEMENT SWITCH RESOURCE SETTINGS
        self.mgtSwitchChasId="MgtSwitch1"
        self.mgtSwitchModelNumber="Switch-ON"
        self.mgtSwitchManufacturer="Dell"
        self.mgtSwitchSerialNumber=None
        self.mgtSwitchAssetTag=None
    
        # REDFISH AGGREGATION MANAGER 
        self.aggregatorMgrId="RedDrum-Aggregator"
        self.aggregatorHostServerChasId="RedDrum-Aggregator-Host"  # chasId of separate server running aggregator
        self.aggregatorHostServerModel="R740"
        self.aggregatorHostServerManufacturer="Dell"
        self.aggregatorHostServerSerialNumber=None
        self.aggregatorHostServerAssetTag=None
