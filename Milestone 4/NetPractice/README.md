*This project has been created as part of the 42 curriculum by dasantos.*

# NetPractice

## Description

NetPractice is an introductory networking exercise. Its goal is to practice the basics of
TCP/IP addressing by fixing small, simulated (non-real) networks so that all the hosts on
each level can reach one another as required.

The project provides a local training interface, opened in a web browser, containing **10
levels** of increasing difficulty. Each level shows a broken network diagram (hosts,
switches, routers, and sometimes a simulated "Internet") along with one or more objectives
(for example, "Host A must be able to reach Host B"). Some fields (IP address, subnet mask,
gateway, routes) are already fixed, and the rest have to be filled in correctly for the
network to work. The interface validates the configuration and shows logs explaining what
is still wrong (invalid IP, missing gateway, no route, etc.) until every objective for that
level is met.

The values in each level are generated pseudo-randomly (per login and per attempt), so the
exercise is really about understanding **how** to solve any configuration, not about
memorizing fixed answers — which matters in particular for the timed, AI-free evaluation.

## Instructions

### Running the training interface

1. Extract the project files into any folder of your choice.
2. Inside that folder, run the `run.sh` script. It starts a local web server and opens the
   dedicated page in your default web browser.
3. If `run.sh` does not work on your system, start the server manually and open it yourself:
   ```bash
   python3 -m http.server 49242
   ```
   Then open `http://localhost:49242` (or whichever port you chose) in your browser.

A local web server is required because of browser security restrictions on how the
interface's files are loaded — opening the HTML files directly will not work correctly.

### Using the interface

- Enter your 42 login in the field provided to generate your **personal** configuration for
  each level, or use the **"evaluation"** tab to generate a random configuration equivalent
  to what you will get during the actual evaluation.
- For each level, read the objective(s) shown at the top, then edit the non-shaded
  (editable) fields — IP addresses, subnet masks, gateways, and/or routing tables — until
  the network works.
- Click **"Check again"** to validate your configuration. The log panel at the bottom
  explains what is still wrong if the check fails.
- Once a level is solved, a button appears to move on to the next level.
- Before moving to the next level, click **"Get my config"** to export your configuration
  for that level. This is required for submission.

### Submission

This repository must contain **10 exported configuration files, one per level**, placed at
the root of the repository (as downloaded via "Get my config"). Make sure your login was
entered in the interface before exporting, and double-check that every file name is
correct before submitting.

During the defense, you will be asked to solve three randomly chosen levels live, within a
limited time, without any external tools (a basic calculator such as `bc` is tolerated).
Being able to explain, out loud, why each value you enter is correct is part of the
evaluation.

## Resources

Networking concepts studied in this project:

- **TCP/IP addressing**: how IPv4 addresses are structured and represented.
- **Subnet masks and CIDR notation**: splitting an address space into network and host
  portions, and computing network/broadcast addresses and valid host ranges.
- **Default gateways**: how a host reaches destinations outside its own subnet.
- **Routers and switches**: the difference between a Layer 2 device that keeps hosts on the
  same subnet (switch) and a Layer 3 device that interconnects different subnets and needs
  a routing table (router).
- **OSI layers**: situating switches (Layer 2) and routers (Layer 3) within the OSI model.
- **Routing tables and the default route** (`0.0.0.0/0`): how a router decides where to
  forward traffic for networks it is not directly connected to.

General references for further reading (not project-specific, for background only):

- Cisco's introductory documentation on IP addressing and subnetting.
- RFC 791 (Internet Protocol) and RFC 950 (Internet Standard Subnetting Procedure).
- General-purpose "IPv4 subnetting cheat sheets" covering CIDR-to-mask conversion and
  host-count tables.
- Introductory material on the OSI model (Layer 2 vs. Layer 3 devices).

### How AI was used

An AI assistant (Claude) was used to help build understanding of the underlying networking
concepts, not to solve the evaluation levels themselves (which are random and cannot be
solved in advance). Specifically, it was used to:

- Explain IPv4 addressing, subnet masks/CIDR notation, and the calculation of network,
  broadcast, and valid host addresses.
- Explain the roles of switches, routers, gateways, and routing tables (including the
  default route) inside the NetPractice simulator's rules.
- Produce a personal study guide with worked, self-contained numerical examples (not tied
  to any actual level's randomized values) illustrating a general step-by-step method for
  solving any level.
- Draft this `README.md` file structure based on the project's requirements.

All AI-assisted explanations were reviewed and are understood well enough to be explained
and justified independently, including during the live, AI-free evaluation.
