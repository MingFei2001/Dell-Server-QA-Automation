# Redfish calls

[Back to the README](../README.md#documentation)

The base path is `/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellLCService`.

| Purpose | Call | Note |
|---|---|---|
| Serial number and model | `GET /redfish/v1/Systems/System.Embedded.1` | Fields `SKU` and `Model` |
| iDRAC version and firmware | `GET /redfish/v1/Managers/iDRAC.Embedded.1` | Fields `Model` (for example `16G Monolithic`, which gives the iDRAC version: 12G iDRAC7, 13G iDRAC8, 14G to 16G iDRAC9, 17G iDRAC10) and `FirmwareVersion`. Read-only. |
| Check the action exists | `GET <base>` | Response lists `SupportAssistCollection` |
| EULA status | `POST <base>/Actions/DellLCService.SupportAssistGetEULAStatus` | Before the first export. Accepted when the response field `Interface` is not null (Dell's script). |
| Accept the EULA | `POST <base>/Actions/DellLCService.SupportAssistAcceptEULA` | Only if not accepted |
| Start TSR | `POST <base>/Actions/DellLCService.SupportAssistCollection` | Body: `{"ShareType": "Local", "DataSelectorArrayIn": ["HWData", "TTYLogs"]}`. Returns 202 with the job address in the `Location` header. |
| Poll the job | `GET` the job address | Under `/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/`. Finished when the response `Location` header contains `sacollect.zip`. `JobState` `Failed` or `CompletedWithErrors` is a failure. |
| Download the TSR | `GET` the address in that `Location` header | `sacollect.zip` |
| Start Lifecycle log export | `POST <base>/Actions/DellLCService.ExportLCLog` | Body: `{"ShareType": "Local"}`. Returns 201 or 202 with a `Location` header. |
| Download the Lifecycle log | `GET` the address in the `Location` header | `lclog.xml` |

Source: Dell's official scripts `SupportAssistCollectionLocalREDFISH.py` and `ExportLCLogREDFISH.py`. Dell's API guide page for `ExportTechSupportReport` lists only CIFS and NFS shares. The local download route comes from the script.

Firmware compatibility:

| Firmware | Result |
|---|---|
| iDRAC9 16G, 7.10.30.00 | Works. Tested from the dashboard by the owner on 2026-11-25. |
| iDRAC9 16G, 7.20.60.50 | Works. The TSR and the Lifecycle log are saved and the checksums match. |
| iDRAC9 14G, 3.21.26.22 | Not supported. `DellLCService` returns 404 at the path above and at `/redfish/v1/Dell/Managers/iDRAC.Embedded.1/DellLCService`. The app reports `Failed: action not supported`. |

The target is firmware 7.00.00 and above. Other versions are not checked ([Status and open items](status.md)).
