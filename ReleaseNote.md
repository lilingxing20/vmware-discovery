## 2.0.0-3
---
### Feature
- sync instance
- sync portgroup
- sync template


</br>

### bug
---
- clean up some invalid code.
- flake8 formatting code.
- when sync vmware instance mechine, only rely on the specified default flavor, not to create new flavor.
- when sync vmware instance mechine template to glance image server, add image name prefix.
- when sync vmware instance mechine, only rely on the specified default network, create port, update ip.
- Restore to remove the virtual machine record registration.
- Fixed a bug, and flake8 formatting code.
