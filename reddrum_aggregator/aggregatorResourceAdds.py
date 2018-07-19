
from .aggregatorConfig import RfaConfig

class RfaResourceAdds():
    def __init__(self,rdr ):
        self.rfaCfg=RfaConfig()  # aggregatorConfig data
        self.beData=rdr.backend
        self.magic="12345"

    # ****************  ADD RESOURCE APIs  ********************

    # ADD "Rack Level Enclosure" Chassis
    # returns rackId, chasRackResource
    def addRfaRackChassis(self):
        rackId = self.rfaCfg.rackChasId
        resp=dict()
        resp["IsTopLevelChassisInAggrRack"]=True
        resp["ChassisType"]="Rack"
        resp["Name"]="Redfish_Aggretator_Rack"
        resp["Description"]="Rack-Level Enclosure for of Redfish Aggregator Servers and Mgt Switch "
        resp["Manufacturer"]=self.rfaCfg.rackManufacturer
        resp["Model"]=self.rfaCfg.rackModelNumber
        resp["SerialNumber"]=self.rfaCfg.rackSerialNumber
        resp["AssetTag"]=self.rfaCfg.rackAssetTag
        resp["BaseNavigationProperties"]=[ ] # xg6 no rack-lvl Power or Thermal res for now
        resp["hasOemRackScaleLocation"]=self.rfaCfg.includeRackScaleOemProperties
        resp["Patchable"]=[ ] # xg6 AssetTag not writable for now
        resp["Volatile"]=["PowerState" ]
        resp["PowerState"]="On"  # xg6 rack PowerState is static On for now
        resp["DiscoveredBy"]="StartupDiscovery"
        resp["ManagedBy"]=[self.rfaCfg.aggregatorMgrId ]
        resp["Contains"]=[]  # update using self.updateRfaRackChassisContainsList() method below
        return(rackId, resp)

    # update Rack-Level Chassis Enclosure Contains List to include all rack-servers in rack 
    def updateRfaRackChassisContainsList(self, chassisDb):
        rackId = self.rfaCfg.rackChasId
        containsList=list()
        for chasid in chassisDb:
            if chasid != rackId:
                containsList.append(chasid)
        if "Contains" in chassisDb[rackId]:
            chassisDb[rackId]["Contains"]=containsList

    def updateRfaAggrMgrManagersForChassisList(self,chassisDb, managersDb):
        aggMgrId = self.rfaCfg.aggregatorMgrId
        managersForChassisList=list()
        for chasid in chassisDb:
            # if the aggregation manager is in the ManagedBy list for this chassis , add it in
            if aggMgrId in chassisDb[chasid]["ManagedBy"]:
                managersForChassisList.append(chasid)
        if "ManagerForChassis" in managersDb[aggMgrId]:
            managersDb[aggMgrId]["ManagerForChassis"]=managersForChassisList

    def updateRfaAggrMgrManagersForServersList(self, systemsDb, managersDb):
        aggMgrId = self.rfaCfg.aggregatorMgrId
        managersForServerList=list()
        for sysid in systemsDb:
            # if the aggregation manager is in the ManagedBy list for this system , add it in
            if aggMgrId in systemsDb[sysid]["ManagedBy"]:
                managersForServerList.append(sysid)
        if "ManagerForServers" in managersDb[aggMgrId]:
            managersDb[aggMgrId]["ManagerForServers"]=managersForServerList

    # ADD "Management Switch" Chassis
    # returns chasId, chasMgtSwitchResource
    def addRfaMgtSwitchChassis(self ):
        rackId = self.rfaCfg.rackChasId
        chasId = self.rfaCfg.mgtSwitchChasId
        resp=dict()
        resp["IsMgtSwitchChassisInAggrRack"]=True
        resp["ChassisType"]="RackMount"
        resp["Name"]="Management Switch"
        resp["Description"]="Rack-Level Management Switch Enclosure"
        resp["Manufacturer"]=self.rfaCfg.mgtSwitchManufacturer  #xg6 getting from cfg file for now
        resp["Model"]=self.rfaCfg.mgtSwitchModelNumber  #xg6 getting from cfg file for now
        resp["SerialNumber"]=self.rfaCfg.mgtSwitchSerialNumber  #xg6 getting from cfg file for now
        resp["AssetTag"]=self.rfaCfg.mgtSwitchAssetTag  #xg6 getting from cfg file for now
        resp["BaseNavigationProperties"]=[ ] # xg6 no MgtSwitch Power or Thermal res for now
        resp["hasOemRackScaleLocation"]=self.rfaCfg.includeRackScaleOemProperties
        resp["Patchable"]=[ ] # xg6 AssetTag not writable for now
        resp["Volatile"]=["PowerState" ] # no ledState or writable assetTag for now
        resp["PowerState"]="On"  # xg6 mgtSwitch PowerState is static On for now
        resp["DiscoveredBy"]="StartupDiscovery"
        resp["ManagedBy"]=[self.rfaCfg.aggregatorMgrId ]
        resp["Contains"]=[]  # update using self.updateRfaRackChassisContainsList() method below
        resp["ContainedBy"]= rackId
        resp["PoweredBy"]= [chasId]
        if self.rfaCfg.redfishAggregatorIsInsideSwitch is True:
            resp["ManagersInChassis"]= [ self.rfaCfg.aggregatorMgrId ]
        else:
            resp["ManagersInChassis"]= [ ]

        #resp["ActionsResetAllowableValues"]=["On","ForceOff","GracefulShutdown","ForceRestart","GracefulRestart"]
        #     xg6 doesn't support reset for now

        return(chasId, resp)

    # ADD "RedfishAggregator" Manager
    # returns mgrId, mgrAggregatorResource
    def addRfaRedfishAggregatorManager(self ):
        rackId = self.rfaCfg.rackChasId
        aggrMgrId = self.rfaCfg.aggregatorMgrId
        resp=dict()
        resp["IsAggregatorManager"]=True
        resp["Netloc"]="127.0.0.1"
        resp["Name"]="Rack Aggregation Manager"
        resp["Description"]="Aggregation Manager Hosting Rack-Level Redfish Service"
        resp["ManagerType"]="AuxiliaryController"
        resp["FirmwareVersion"]="v0.9.5"
        resp["Status"]={"State": "Enabled", "Health": "OK" }
        resp["ManagerInChassis"]=rackId
        resp["ManagerForChassis"]=[]  # this will be updated after discovering all of the Rack Chassis
        resp["ManagerForServers"]=[]  # this will be updated after discovering all of the Rack Chassis
        resp["GetDateTimeFromOS"]=True
        resp["GetUuidFromServiceRoot"]=True
        resp["GetServiceEntryPointUuidFrom"]="ServiceRoot"   # ServiceRoot | UUID 
        #resp["SerialConsole"]={"ServiceEnabled": True, "MaxConcurrentSessions": 100, "ConnectTypesSupported": ["SSH"]}
        resp["CommandShell"]={"ServiceEnabled": True, "MaxConcurrentSessions": 100, "ConnectTypesSupported": ["SSH"]}
        resp["ActionsResetAllowableValues"]=["GracefulRestart","ForceRestart"] # xg we need to support this

        # properties that can be written.   
        resp["Patchable"]=["DateTime", "DateTimeLocalOffset"]   # Recommended in BaseServerProfile  xg need to support

        resp["BaseNavigationProperties"]=["NetworkProtocol", "EthernetInterfaces" ]
        aggrManagerNetworkProtocols = {
            "Name":  "Aggregation Manager Network Protocols",
            "HTTP":  {"Port": 80, "ProtocolEnabled":  True},
            "HTTPS": {"Port": 443,"ProtocolEnabled": True },
            "SSH":   {"Port": 22, "ProtocolEnabled": True },
            #"NTP":   {}, 
            "HostName": "",
            "FQDN": "",
            "Status": {"State": "Enabled", "Health": "OK"}
          }
        resp["NetworkProtocols"]= aggrManagerNetworkProtocols

        mgmtLan1={
            "Name": "eth0", "SpeedMbps": None, "HostName": "", "FQDN": "",
            "InterfaceEnabled": True, "FullDuplex": True, "AutoNeg": True,
            "MACAddress": None, "PermanentMACAddress": None, "IPv4Addresses": None
        }
        resp["EthernetInterfaces"]={"eth0": mgmtLan1 }
        resp["DiscoveredBy"]="Discovery"
        return(aggrMgrId, resp)

    # ADD "RedfishAggregator HostServer" Chassis -- (only used if RfAggregator is running on a separate server)
    def addRfaRedfishAggregatorHostServerChassis(self ):
        rackId = self.rfaCfg.rackChasId
        aggrMgrId = self.rfaCfg.aggregatorMgrId
        #chasId = self.rfaCfg.mgtSwitchChasId
        chasId = self.rfaCfg.aggregatorHostServerChasId
        resp=dict()
        resp["IsAggrHostServerChassisInAggrRack"]=True
        resp["ChassisType"]="RackMount"
        resp["Netloc"]="127.0.0.1"
        resp["Name"]="Redfish Aggregator RackMount Host Server Chassis"
        resp["Description"]="The host server implementing the Redfish Aggregator Manager indide the rack"
        resp["Manufacturer"]=self.rfaCfg.aggregatorHostServerManufacturer  #xg6 getting from cfg file for now
        resp["Model"]=self.rfaCfg.aggregatorHostServerModel   #xg6 getting from cfg file for now
        resp["SerialNumber"]=self.rfaCfg.aggregatorHostServerSerialNumber  #xg6 getting from cfg file for now
        resp["AssetTag"]=self.rfaCfg.aggregatorHostServerAssetTag  #xg6 getting from cfg file for now
        resp["BaseNavigationProperties"]=[ ] # xg6 no MgtSwitch Power or Thermal res for now
        resp["hasOemRackScaleLocation"]=self.rfaCfg.includeRackScaleOemProperties
        resp["Patchable"]=[ ] # xg6 AssetTag not writable for now
        resp["Volatile"]=["PowerState" ] # no ledState or writable assetTag for now
        resp["PowerState"]="On"  # xg6 mgtSwitch PowerState is static On for now
        resp["DiscoveredBy"]="StartupDiscovery"
        resp["ManagedBy"]=[aggrMgrId]
        #resp["Contains"]=[]  
        resp["ContainedBy"]= rackId
        resp["PoweredBy"]= [ chasId ]
        resp["ManagersInChassis"]= [ aggrMgrId ] # not counting the bmc for this chassis xg?
        resp["ActionsResetAllowableValues"]=["On","ForceOff","GracefulShutdown","ForceRestart","GracefulRestart"]
        return(chasId, resp)


    # ADD RackServer Chassis
    def addRfaRackServerChassis(self, svrId, svrNetloc, svrPduSockId, svrCredsId ):
        rackId = self.rfaCfg.rackChasId
        aggMgrId = self.rfaCfg.aggregatorMgrId
        bmcMgrId=svrId
        chasId=svrId
        resp=dict()
        resp["IsRackServerChassis"]=True
        resp["Netloc"]=svrNetloc
        resp["CredentialsId"]=svrCredsId
        resp["PduSocketId"]=svrPduSockId
        resp["ChassisType"]="RackMount"  # xg6 or is it mono
        resp["Name"]="Rack Server"
        resp["Description"]="Rack Server Chassis Enclosure"
        resp["Manufacturer"]="Dell"
        resp["Model"]=None
        resp["Status"]={"State": "Enabled", "Health": "OK" } #initialize as Enabled OK
        resp["BaseNavigationProperties"]=["Thermal", "Power"]
        resp["ActionsResetAllowableValues"]=["On","ForceOff","GracefulShutdown","ForceRestart","GracefulRestart"]
        resp["hasOemRackScaleLocation"]=self.beData.includeRackScaleOemProperties
        resp["ContainedBy"]=rackId
        resp["CooledBy"]=[chasId]
        resp["PoweredBy"]=[ chasId ]
        managedByList = [ bmcMgrId, aggMgrId ]
        resp["ManagedBy"]=managedByList
        resp["Patchable"]=["IndicatorLED"]
        resp["Volatile"]=["PowerState", "IndicatorLED", "PhysicalSecurity"]
        resp["DiscoveredBy"]="Dynamic"
        resp["ComputerSystems"]=[svrId]
        resp["ActionsOemSledReseat"]=True
        resp["Oem"]={}
        return(chasId,resp)


    # ADD RackServer System
    def addRfaRackServerSystem(self, svrId, svrNetloc, svrCredsId  ):
        rackId = self.rfaCfg.rackChasId
        chasId = svrId
        aggMgrId = self.rfaCfg.aggregatorMgrId
        bmcMgrId=svrId
        resp=dict()
        resp["IsRackServerSystem"]=True
        resp["Netloc"]=svrNetloc
        resp["CredentialsId"]=svrCredsId
        resp["Name"]="Rack Computer System"
        resp["Description"]="Rack Server Computer System Node"
        resp["SystemType"]="Physical"
        resp["Chassis"]=[chasId]
        managedByList = [ bmcMgrId, aggMgrId ]
        resp["ManagedBy"]=managedByList

        # the following are defaults and on first call to the system the backend may update these
        resp["Manufacturer"]="Dell"  # default
        resp["BaseNavigationProperties"]=["Processors","EthernetInterfaces","SimpleStorage","Memory"] 
        resp["ActionsResetAllowableValues"]=["On","ForceOff","GracefulShutdown","GracefulRestart","ForceRestart"]
        resp["Volatile"]=["PowerState", "IndicatorLED"]
        resp["Patchable"]=["IndicatorLED" ]
        resp["BootSourceVolatileProperties"]=[]
        resp["BootSourcePatchableProperties"]= []
        resp["BootSourceAllowableValues"]=[]
        resp["ProcessorSummary"]={"Count": None,"Model": None,"Status": {"State": None,"Health": None} }
        resp["MemorySummary"]={"TotalSystemMemoryGiB": None,"Status": {"State": None,"Health": None}}
        resp["Model"]=None
        resp["SerialNumber"]=None
        resp["UUID"]=None
        resp["AssetTag"]=None
        resp["BiosVersion"]=None
        #resp["HostName"]=getResp["HostName"]
        resp["Status"]={"State": None, "Health": None }

        # add additional mgtNetwork properties
        # G5-defined Management Network Parameters
        resp["MgtNetworkNetloc"]=svrNetloc
        resp["OemDellG5MgtNetworkInfo"]={}
        resp["OemDellG5MgtNetworkInfo"]["MgtNetworkIP"]=svrNetloc
        resp["OemDellG5MgtNetworkInfo"]["MgtNetworkMAC"]=None
        resp["OemDellG5MgtNetworkInfo"]["MgtNetworkEnableStatus"]="ENABLED"

        # add Dell oem data
        resp["OemDell"]=True

        # the following are defaults and on first call to the system the backend may update these
        # hard coded Rackscale properties xg
        if self.beData.includeRackScaleOemProperties:
            resp["OemRackScaleSystem"]= { "ProcessorSockets": 2, "MemorySockets": 16, "DiscoveryState": "Basic" }
        return(svrId,resp)

    # ADD RackServer Manager
    def addRfaRackServerManager(self, svrId, svrNetloc, svrCredsId  ):
        rackId = self.rfaCfg.rackChasId
        chasId = svrId
        aggMgrId = self.rfaCfg.aggregatorMgrId
        bmcMgrId=svrId
        resp=dict()
        resp["IsRackServerManager"]=True
        resp["Netloc"]=svrNetloc
        resp["CredentialsId"]=svrCredsId
        resp["Name"]="Rack Computer System"
        resp["Description"]="Rack Server Computer System Node"
        resp["SystemType"]="Physical"
        resp["Chassis"]=[chasId]
        managedByList = [ bmcMgrId, aggMgrId ]
        resp["ManagedBy"]=managedByList
        resp["ManagerType"]="BMC"
        resp["Manufacturer"]="Dell"  # default

        # the following are defaults and on first call to the system the backend may update these
        resp["Model"]=None
        resp["ManagerInChassis"]=chasId    # note: not required in BaseServerProfile
        resp["ManagerForChassis"]=[chasId]
        resp["ManagerForServers"]=[svrId]
        resp["Status"]={"State": None, "Health": None }
        resp["ProcessorSummary"]={"Count": None,"Model": None,"Status": {"State": None,"Health": None} }
        resp["MemorySummary"]={"TotalSystemMemoryGiB": None,"Status": {"State": None,"Health": None}}
        resp["Model"]=None
        resp["SerialNumber"]=None
        resp["UUID"]=None
        resp["AssetTag"]=None
        resp["BiosVersion"]=None
        #resp["HostName"]=getResp["HostName"]
        resp["Status"]={"State": None, "Health": None }

        resp["SerialConsole"]= {"ServiceEnabled": None,
                                "ConnectTypesSupported": None }
        resp["CommandShell"] = {"ServiceEnabled": None,
                                "ConnectTypesSupported": None }

        resp["ActionsResetAllowableValues"]=["GracefulRestart","ForceRestart"]
        #resp["BaseNavigationProperties"]=["NetworkProtocol","EthernetInterfaces","LogServices"] # in BaseServerProfile
        resp["BaseNavigationProperties"]=["NetworkProtocol","EthernetInterfaces"] # in BaseServerProfile

        resp["GetDateTimeFromOS"]=False
        #resp["ServiceEntryPointUUID"]=None  
        resp["DateTime"]=None  
        resp["DateTimeLocalOffset"]=None  

        # properties that can be written.   
        resp["Patchable"]=["DateTime", "DateTimeLocalOffset"]   # Recommended in BaseServerProfile

        # get these properties from Dbus discovery
        resp["FirmwareVersion"]=None
        resp["UUID"]=None

        # ***ManagerNetworkProtocols
        managerNetworkProtocols = {
            "Name":  "Rack Server BMC Network Protocols",
            "HTTP":  {"Port": 80, "ProtocolEnabled": True},
            "HTTPS": {"Port": 443,"ProtocolEnabled": True },
            "SSH":   {"Port": 22, "ProtocolEnabled": True },
            #"NTP":   {},   # no NTP in BaseServer Profile
            "HostName": "",
            "FQDN": "",
            "Status": {"State": "Enabled", "Health": "OK"}
        }
        resp["NetworkProtocols"]= managerNetworkProtocols

        # *** EthernetInterfaces
        ipv4info=[{"Address": None, "SubnetMask": None, "Gateway": None, "AddressOrigin": None}]
        ethDeviceInfo = {
                "Name": "", "SpeedMbps": None, "HostName": "", "FQDN": "", "LinkStatus": None,
                "InterfaceEnabled": None, "FullDuplex": True, "AutoNeg": True,
                "MACAddress": None, "PermanentMACAddress": None, "IPv4Addresses": ipv4info
        }
        resp["EthernetInterfaces"] = { "eth0": ethDeviceInfo }
        resp["Status"]={"State": None, "Health": None }

        # add additional mgtNetwork properties
        # G5-defined Management Network Parameters
        resp["MgtNetworkNetloc"]=svrNetloc
        resp["OemDellG5MgtNetworkInfo"]={}
        resp["OemDellG5MgtNetworkInfo"]["MgtNetworkIP"]=svrNetloc
        resp["OemDellG5MgtNetworkInfo"]["MgtNetworkMAC"]=None
        resp["OemDellG5MgtNetworkInfo"]["MgtNetworkEnableStatus"]="ENABLED"

        # the following are defaults and on first call to the system the backend may update these
        # hard coded Rackscale properties xg
        if self.beData.includeRackScaleOemProperties:
            resp["OemRackScaleSystem"]= { "ProcessorSockets": 2, "MemorySockets": 16, "DiscoveryState": "Basic" }

        #add oemTarget support
        resp["AddOemActions"]=True

        return(bmcMgrId,resp)






