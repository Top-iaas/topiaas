[![Build and push orangeml image](https://github.com/Top-iaas/topiaas/actions/workflows/BuildPublishOrangeML.yml/badge.svg)](https://github.com/Top-iaas/topiaas/actions/workflows/BuildPublishOrangeML.yml)
[![Build and push portal image](https://github.com/Top-iaas/topiaas/actions/workflows/BuildPublishPortal.yml/badge.svg)](https://github.com/Top-iaas/topiaas/actions/workflows/BuildPublishPortal.yml)
[![Build and push inkscape image](https://github.com/Top-iaas/topiaas/actions/workflows/BuildPublishInkspace.yml/badge.svg)](https://github.com/Top-iaas/topiaas/actions/workflows/BuildPublishInkspace.yml)
# topiaas
## Introduction 
Topiaas (Top Infrastructure as a Service) is a cloud platform that simplifies the process of renting and deploying applications without the need for manual provisioning. Users can easily select the applications they need along with the desired compute resources, and Topiaas handles the rest through automated orchestration. Once deployed, users are provided with a VNC page that offers low-latency access to these applications directly through their browser, making it feel almost like they are running locally.

While there might be some minor latency compared to running applications on local hardware, the convenience and flexibility of accessing resource-intesive applications on the cloud from any device, at any time, far outweighs this. Additionally, Topiaas follows a pay-as-you-go model, ensuring that users only pay for what they use. This is done by introducing billing units which are calculated by how much CPU/Memory is rented for how much time.

The entire project is opensource and can be self-hosted anywhere thanks to the cloud-agnostic nature of the architecture.
## Infrastructure

![](https://github.com/Top-iaas/topiaas/blob/fb7b14097d7abe277ef3822d3cee659b1f6c372a/assets/Topiaas%20cloud%20arch.png)

## Architecture

![](./assets/Architecture.png)

## devenv dependencies 

Make sure to have the following packages installed and configured according to your distribution: 

1. docker (make sure to have your user in docker group. follow this tutorial: https://docs.docker.com/engine/install/linux-postinstall/)
2. minikube 
3. kubectl 

