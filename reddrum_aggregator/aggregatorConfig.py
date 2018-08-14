
class RfaConfig():
    def __init__(self):
    
        # RACK CONFIG
        # -redfishAggregatorIsInsideSwitch= OneOf( True, False )
        #    set to false to model case where Aggregator is in a separate server--not inside mgt switch
        #    set to true if running on switch as container or venv
        self.redfishAggregatorIsInsideSwitch=False
    
        # DISCOVERY
        # * The Discovery .json files are now in subdir ./DISCOVERY
        # * this property points to the discovery file that will be used in ./DISCOVERY
        # * to customize the discovery file, you can either:
        #   1) create your new discovery file from one of the templates in ./DISCOVERY and point to is here, -or-
        #   2) leave this property pointing at the discovery-dlft.json target and copy your new customized file to 
        #      discovery-dflt.json
        self.discoverRackServersFrom="discovery-dflt.json"   
        #Ex: self.discoverRackServersFrom="discovery-2servers.json" 
    
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

        # PDU Reseat App and Script -- this property identifies the App and Script that pduWrapper.sh will execute 
        #  in order to reseat a server via a PDU.  
        #   * pduReseatScriptApp is passed to pduWrapper.sh as argv1
        #   * pduReseatScript    is passed to pduWrapper.sh as argv2
        #   * pduWrapper.sh executes the Script using the App.   If App is none or "", it assumes bash
        #   * the pdu scripts are now in subdir ./PDU_SCRIPTS.  
        #   * as we support additional PDUs, we will accumulate additional pdu script templates
        #   * to point at a new customized pdu script, you can either:
        #     1) change the script name below to point to your new script in ./PDU_SCRIPTS, -or-
        #     2) leave the target here set to the default pdu script: pduReseatScript-dflt.py and
        #        then copy or link your new custom script to ./PDU_SCRIPTS/pduReseatScript-dflt.py 
        #   * if your new script is not a python2 script, you must change the command here to run the currect client
        self.pduReseatScriptApp="python2"
        self.pduReseatScript="pduReseatScript-dflt.py"
        #ex:  self.pduReseatScript="python2 pduReseatScript-xyz.py"

        # CREDENTIALS File -- contains credential IDs
        #   * the credential files are now in ./CREDENTIALS.
        #   * several example credentials files are also in ./CREDENTIALS
        #   * if you need to customize the credentials file, you can create a new one from the templates and either:
        #     1) point to the new file here, -or-
        #     2) leave this property pointing at the generic credential file ./CREDENTIALS/bmcCredentials-dflt.json
        #        and copy your new file to bmcCredentials-dflt.json
        self.bmcCredentialsFile="bmcCredentials-dflt.json"
        #Ex: self.bmcCredentialsFile="bmcCredentials-idrac.json"
    
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
