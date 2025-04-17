### NOTE
This repo is the initial implementation of the Invisinets API. The overall Invisinets project has evolved with its collaborators (Google, Microsoft, IBM, and more) to become the [Paraglider project](paragliderproject.io) with its own implementation found [here](https://github.com/paraglider-project/paraglider)

### API Endpoints
| Invisinets API | First-party API |
| --- | ----------- |
| request_eip(vm_id) | Provision a VM (can skip if you assume already there to start) and allocate it a public IP |
| request_sip() | Provision a load balancer and give it a public IP |
| bind(eip, sip) | Put the VM with the given eip in the backend pool of the sip load balancer |
| set_permit_list(eip, permit_list) | Update the rules in the security group for the VM |
| set_tag(eip, tag) | Use tagging mechanisms already offered |
| annotate(eip, middlebox) | Provision middlebox type chosen and use route tables to direct all traffic from the EIP to the middlebox |

