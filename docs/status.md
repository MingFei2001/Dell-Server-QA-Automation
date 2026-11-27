# Status and open items

[Back to the README](../README.md#documentation)

## Status

- [x] Stage 1: skeleton and README v0.1 (2026-11-20). Code removed on 2026-11-20 to restart from the spec.
- [x] Stage 2: build the project files from the written spec and test (2026-11-23). Tested on a test VM against two real iDRACs. The mock iDRAC was not built.
- [x] Proof of concept complete (2026-11-23): TSR and Lifecycle log collected from five real 16G servers on firmware 7.20.60.50, four of them in parallel.
- [x] Stage 3: real server test (2026-11-25). The owner tested a real 16G server (iDRAC firmware 7.10.30.00) from the dashboard and calls the project a success. No further testing is planned before use.

## Verification record

- 2026-11-23: the images built and the app ran on the test VM. The TSR and the Lifecycle log were collected from five 16G servers on firmware 7.20.60.50, four of them in parallel, and the checksums match. Collection fails on 14G firmware 3.21.26.22 ([Redfish calls](redfish-reference.md)).
- An agent clicked through the dashboard in a browser: Add, Collect, downloads, Add messages, Remove, status per stage and live refresh.
- 2026-11-25: the owner collected a TSR and a Lifecycle log from a real 16G server on firmware 7.10.30.00 from the dashboard. A successful TSR export needs the SupportAssist EULA to be accepted, so the EULA step is verified by that run.
- `setup.sh`, including the Docker install step, was tested by the owner and works. Docker's own documentation stays the reference ([Quick start](getting-started.md#quick-start)).
- 2026-11-24: the `.env` syntax rules and the missing-file behaviour ([Configuration](configuration.md)) were tested with Docker Compose on the VM.
- The troubleshooting entries ([Troubleshooting](troubleshooting.md)) come from the design and Dell documentation. Update them when a real problem shows up.

## Open items

Item numbers are kept from earlier versions so that references stay valid.

Closed:

1. Docker image build and package install on Python 3.14.10. The VM has 15.5 GB RAM and 4 cores. The minimum is 4 GB ([Software stack and design](architecture.md#software-stack-and-design)).
2. Ping inside the container as a non-root user works.
3. Local TSR export works on firmware 7.10.30.00 and 7.20.60.50. It is not available on 3.21.26.22 (item 10).
4. The `SKU` and the box label. Closed by the owner's verdict of 2026-11-25. No separate label comparison is on record.
6. Docker install from Docker's apt repository on Ubuntu 26.04.1 works (Docker 29.10.0, Compose v5.8.0).
7. SupportAssist EULA acceptance. A successful TSR export needs it, so it is done.
8. Data handling rules. Dropped: the collected files stay on the lab network and carry no risk. Take care only when publishing code.
11. Pre-integration and post-integration collections on hardware. Closed by the owner's verdict.
12. The contents of the inner TSR zip. Closed by the owner's verdict.
13. Operation of the dashboard by a person. Done on 2026-11-25.

Still open:

9. A NAS for backup. The nightly rsync stays disabled until one exists. VM snapshots are taken by hand, or by a Proxmox schedule if the owner sets one up. They are not a requirement, because the container can be rebuilt from the repository. Owner: Mingfei.
10. Legacy firmware: racadm not tested, out of scope. Collect manually if such a device appears. Notes in [Legacy firmware](redfish-reference.md#legacy-firmware).
14. A fixed address or DHCP reservation for the VM, so the dashboard link stays the same.

Later, when more servers are on hand:

5. Tune `MAX_PARALLEL` and `TSR_TIMEOUT_MIN`. Five 16G servers on firmware 7.20.60.50 each gave a 1.8 MB zip in about 12 to 13 minutes, four in parallel with no slowdown. Check how many servers fit in the evidence space (about 90 GB, an estimate).
