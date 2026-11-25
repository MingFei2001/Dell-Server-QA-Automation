# Getting started

[Back to the README](../README.md#documentation)

## Quick start

VM: Ubuntu Server 26.04 LTS on a hypervisor ([Software stack and design](architecture.md#software-stack-and-design)), minimum 4 GB RAM, 4 cores, 128 GB storage.

Docker install: follow the official Docker documentation for Ubuntu: <https://docs.docker.com/engine/install/ubuntu/>. It is the source of truth. `setup.sh` runs that install for you if Docker is missing.

Steps:

1. Create `.env` from `.env.example` ([Configuration](configuration.md)).
2. Run `docker compose up -d --build`.
3. Open `http://<server-ip>:5001` from a lab PC.

On a fresh Ubuntu VM, clone the repository (or unzip the package) and run `bash setup.sh`. The script installs Docker if missing, creates `.env` from `.env.example` (asks for the iDRAC user, password and port), sets the `data/` owner, starts the container and prints the dashboard URL. An existing `.env` is kept. Set `IDRAC_USER`, `IDRAC_PASS` and `PORT` in the environment to run it without prompts. The script needs internet access for the Docker install and the image pull.

## Your first hour

1. Read [Architecture](architecture.md), [Status](status.md) and [Decisions](decisions.md): scope, stack and reasons, status and open items, decisions.
2. Get the project: `git` repository, branch `main`. Ask the owner for the VM address and SSH key. They are not stored here.
3. Copy the project to a Linux VM and run `bash setup.sh` ([Quick start](getting-started.md#quick-start)).
4. Open the dashboard, add an iDRAC, press Collect under General, and open the files with the `Files` link.
5. Check a file: `sha256sum -c <file>.sha256` in its folder ([Evidence layout](usage.md#evidence-layout)).
6. To change code: edit `main.py` locally, back up first ([Operations](operations.md)), copy it to the VM and run `docker compose up -d --build`.

## iDRAC access

- Address: `https://<idrac-ip>`
- User: `root`
- Password: `calvin`
- These are the Dell defaults. The customer owns the servers, so WWT does not change them. They are set in `.env`.
- A server with a different login can be added with its own user and password ([Using the dashboard](usage.md#using-the-dashboard)). That login lives in app memory only.
- The iDRAC certificate is self-signed. The app does not verify it. This is accepted on the lab network.
