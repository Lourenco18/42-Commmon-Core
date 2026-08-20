*This project has been created as part of the 42 curriculum by dasantos.*

# NetPractice

## Description

NetPractice is an introductory networking exercise. Its goal is to discover and practice the basics of computer networking by configuring small simulated networks.

The project focuses on TCP/IP addressing, subnet masks, default gateways, and the role of network devices such as routers and switches. The objective is to modify the available network configuration until the required connections between devices work correctly.

The networks used by NetPractice are simulated and are not real networks. The project provides a training interface that runs locally in a web browser.

There are **10 levels**, each presenting a non-functioning network diagram with one or more objectives. For each level, some configuration fields are fixed while others must be completed or corrected. The configuration can include IP addresses, subnet masks, gateways, and routing information.

## Instructions

### Running the training interface

First, download the NetPractice project files and extract them into a directory of your choice.

Inside the extracted directory, run:

```bash
./run.sh
```

The script starts a local web server and opens the NetPractice interface in your default web browser.

If `run.sh` does not work correctly, the server can be started manually with:

```bash
python3 -m http.server 49242
```

Then open the following address in your browser:

```text
http://localhost:49242
```

A local web server is required because of technical and security constraints in some web browsers.

### Using the interface

You can enter your 42 login in the training interface to use your personal configuration.

You can also use the **evaluation** tab to generate a random configuration suitable for evaluation practice.

For each level:

1. Read the objective displayed at the top of the page.
2. Identify the fields that can be modified.
3. Configure the required IP addresses, subnet masks, gateways, and routes.
4. Click **Check again** to validate the configuration.
5. Use the logs at the bottom of the page to understand configuration errors.
6. Once the level is successfully completed, click the button to proceed to the next level.
7. Before moving to the next level, click **Get my config** and save the exported configuration file.

Only the unshaded fields are intended to be modified.

### Submission

NetPractice contains **10 levels**, and one exported configuration file must be submitted for each level.

The **10 exported configuration files must be placed at the root of the Git repository**.

Before exporting the configurations, make sure that your 42 login has been entered in the training interface. Use the **Get my config** button to export one configuration file for each completed level.

Double-check the filenames before submitting the project.

### Defense

During the defense, three random levels must be successfully completed within a limited amount of time.

External tools are not allowed during the evaluation. A simple calculator such as `bc` is tolerated, but this is the limit. The configuration and the reasoning behind it must therefore be understood well enough to solve the levels independently.

## Resources

### Networking concepts studied

The main networking concepts covered by NetPractice include:

* **TCP/IP addressing** — understanding IPv4 addresses and how devices are identified within a network.
* **Subnet masks** — determining which part of an IP address identifies the network and which part identifies the host.
* **Default gateways** — understanding how a host communicates with destinations outside its local network.
* **Routers** — understanding how routers connect different networks and forward traffic.
* **Switches** — understanding their role in connecting devices within a network.
* **OSI layers** — understanding the distinction between Layer 2 networking devices such as switches and Layer 3 devices such as routers.
* **Routing** — understanding how routing information determines where network traffic should be forwarded.

The subject specifically recommends understanding TCP/IP addressing, routers, switches, subnet masks, and default gateways in order to complete the exercises.

### References

The following resources can be used to strengthen the understanding of the concepts used in this project:

* Cisco documentation and introductory material about IPv4 addressing and subnetting.
* **RFC 791** — Internet Protocol.
* **RFC 950** — Internet Standard Subnetting Procedure.
* IPv4 subnetting references and CIDR notation guides.
* Introductory documentation about the OSI model, routers, switches, and network gateways.

### AI Usage

AI was used as a learning and productivity aid while working on this project.

It was used to:

* Explain networking concepts such as TCP/IP addressing, subnet masks, gateways, routers, switches, and OSI layers.
* Clarify subnetting and IP addressing calculations through independent examples.
* Help structure explanations and study material for the project.
* Review the README structure and compare it with the project requirements.

AI was **not used to provide precomputed solutions for the submitted NetPractice levels**. The levels are solved by understanding the network configuration and applying the networking concepts to each exercise.

All AI-generated explanations were reviewed and checked. The concepts used in the project are understood well enough to explain the reasoning and configuration independently during the defense.

This follows the project guidelines: AI-generated content should be critically reviewed, tested when appropriate, and only used when the student fully understands it and can take responsibility for it.
