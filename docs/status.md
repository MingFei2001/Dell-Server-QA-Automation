# Status and open items

[Back to the README](../README.md#documentation)

## Status

- [x] Stage 1: skeleton and README v0.1 (2026-11-20). Code removed on 2026-11-20 to restart from the spec.
- [x] Stage 2: build the project files from the written spec and test (2026-11-23). Tested on a test VM against two real iDRACs. The mock iDRAC was not built.
- [x] Proof of concept complete (2026-11-23): TSR and Lifecycle log collected from five real 16G servers on firmware 7.20.60.50, four of them in parallel. All collections were started by an agent over HTTP, not from the dashboard. Dashboard use by a person is not tested (open item 13).
- [ ] Stage 3: pilot one real server on the existing VM. The test VM is the pilot VM.

## Verification record

- 2026-11-23: the images built and the app ran on the test VM. The TSR and the Lifecycle log were collected from five 16G servers on firmware 7.20.60.50, four of them in parallel, and the checksums match. Collection fails on 14G firmware 3.21.26.22 ([Redfish calls](redfish-reference.md)).
- An agent clicked through the dashboard in a browser: Add, Collect, downloads, Add messages, Remove, status per stage and live refresh. A person has not used it yet (item 13).
- `setup.sh`, including the Docker install step, was tested by the owner and works. Docker's own documentation stays the reference ([Quick start](getting-started.md#quick-start)).
- 2026-11-24: the `.env` syntax rules and the missing-file behaviour ([Configuration](configuration.md)) were tested with Docker Compose on the VM.
- The troubleshooting entries ([Troubleshooting](troubleshooting.md)) come from the design and Dell documentation. Update them after the pilot.
- Not tested on the target client servers yet.

## Open items and unverified

Verified on the test VM on 2026-11-23:

1. Docker image build and package install on Python 3.14.10. The VM had 3.3 GiB RAM at that test. On 2026-11-24 it shows 15.5 GB RAM and 4 cores. The minimum is 4 GB ([Software stack and design](architecture.md#software-stack-and-design)).
2. Ping inside the container as a non-root user works.
6. Docker install from Docker's apt repository on Ubuntu 26.04.1 works (Docker 29.10.0, Compose v5.8.0).

Partly verified:

3. Local TSR export works on firmware 7.20.60.50. It is not available on 3.21.26.22 ([Redfish calls](redfish-reference.md)). The firmware on the target client servers is not known yet. Fallback: a CIFS or NFS share, which needs a share to be provided.
5. TSR size and time: five 16G servers on firmware 7.20.60.50 each gave a 1.8 MB zip in about 12 to 13 minutes. Four ran in parallel (`MAX_PARALLEL` 4) with no slowdown and no errors. Tune `MAX_PARALLEL` and `TSR_TIMEOUT_MIN` after more runs. Confirm how many servers fit in the evidence space (about 90 GB, an estimate).

Not verified yet:

4. That `SKU` matches the box label. Compare the value the app reads with the label on the box.
7. SupportAssist EULA acceptance. It was not recorded whether the app accepted the EULA or it was already accepted.
11. Pre-integration and post-integration collections on hardware.
12. The contents of the inner TSR zip (`HWData` and `TTYLogs`).
13. Operation of the dashboard by a person in a browser: the Add input and the three Collect buttons. Collections so far were started by an agent with HTTP calls to the app. On 2026-11-23 an agent also clicked through the dashboard in a browser: Add sends its request and refreshes the table, Collect pre-integration starts a job that finishes with correctly named files, and the download links return the right headers. A person has not used it yet. After the dashboard rework the same agent tested Add messages, Remove, status per stage, disabled buttons and live refresh. A person has not used it yet.

Still to decide:

8. Data handling rules for the collected files.
9. A NAS for backup, and a backup or snapshot policy for the VM. Owner: Mingfei.
10. A legacy method for firmware without `DellLCService`, such as 3.21.26.22. Candidates are `racadm supportassist collect` and a network share export. Verify against Dell documentation first.
14. A fixed address or DHCP reservation for the VM, so the dashboard link stays the same.
