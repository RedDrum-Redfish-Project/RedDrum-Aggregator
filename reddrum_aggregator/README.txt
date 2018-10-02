
This is the Backend RedDrum implementation for the Aggregator

**NOTE: The aggregator must be paired with the "V2" branch of RedDrum-Frontend (which is the master branch)

This "v2.0" Aggregator is now a "near Transparent" aggregator:
  -- 1) The members array for the main resource "Collections" (Systems, Chassis, Managers) are saved
        after discovery so that the GET "/redfish/v1/<Collection>" response is fast
        The response of the collections is built from this discovered and saved/cached data

  -- 2) The responses for resources below the collections is not cached however.
        So any GET, Patch, Post/Delete that targets a resource below the main collections results in a
        transparent request to the aggregated server, and the response from the server is then
        "processed" [or 'localized'] such that any URI links returned by the aggregated BMC has been modified
        so that they main collection IDs are unique across the entire aggregation

The benefit of the "near Transparent" aggregation:
    -- All of the Oem data and APIs supported by an aggregated server are automatically supported.
       Even Oem Post actions get automatically supported.
    -- The aggregator does not have to change as new properties are features are added for a BMC

Redfish Resources that v2.0 Aggregator Backend supports true aggregation of:
  -- All APIs under the /Chassis collection,
  -- All APIs under the /Managers collection,
  -- All APIs under the /Systems  collection
  -- The Link header URIs that point to locally stored [possibly Oem or Modified] schemas on aggregated BMCs
     -- but links inside a locally stored schema file that is relative to the BMC's IP is not being localized
        (but internal links that are relative to the file they are in are OK, or links to external sites are ok)

What is NOT YET supported fully by the B2.0 Aggregator: (Work ToDo):
     -- Fully localizing links inside locally stored schema files returned by a BMC that are relative to the BMC's IP
     -- TaskService/Tasks collection  (although a task Uri returned by server in Location header will work correctly)
     -- UpdateService APIs
     -- EventService/Events aggregation and subscribing to events coming from aggregated servers
     -- JsonSchemas and Registries Collection support for locally stored or Oem schemas used by aggregated servers
     -- $metadata and Odata service doc responses that contain all resource supported by all aggregated servers

The RedDrum-Frontend will Continue to provide the following:
  -- ServiceRoot Implementation -- that contains the main resource collections 
  -- AccountService implementation
     -- The privilege mapping is done consistently by the frontend for all aggregated servers
     -- All authentication and authorization is consistently done by the Frontend
  -- SessionService implementation
     -- Redfish Session Auth is implemented totally in the frontend
  -- Redfish ServiceRoot level APIs  
     -- EventService -- some service-level processing will remain in frontend, but backend support is required 
     -- TaskService  -- some service-level processing will remain in frontend, but backend support is required 
     -- UpdateService-- some service-level processing will remain in frontend, but backend support is required 
  -- schema collections
     -- /redfish/v1/$Metadata
     -- /redfish/v1/odata
  
Header Support:
  -- The Aggregator Frontend provides the Request Header processing.
  -- The Aggregator Backend provides general Response Header processing eg Server, Odata-Version, etc
  -- The Backend uses BMC responses but filters some headers (eg Content-Type) to insure conformance with the spec
  -- If the Link header returned by an aggregated BMCs points to a local schema store on the BMC, the
     link header is processed [or localized] such that if a client does a GET to the link, it would be
     proxied to the bmc and the locally stored schema on that BMC would return the data


Local Aggregator Resources Created by the Backend:
  -- The RedDrum-Aggregator implements the following resource in backend-code:
     (these can be configured to be included or not in the aggregatorConfig.py file
     1) -- The Aggregator Manager  -- the external manager that runs the aggregator service
     2) -- The [Rack Enclosure] Chassis -- the overall enclosure of aggregated servers
     3) -- The Aggregation Management Switch -- switch that connects the Aggregation Manager to all of the BMCs
     4) -- The optional Aggregation Manager Host -- the chassis that contains the aggregation manager service if it is not 
          running inside the management switch
  -- These "local resource" are implemented in separate code Classis in the backend
  -- Properties eg AssetTag are stored in persistent files by the Aggregation Manager



