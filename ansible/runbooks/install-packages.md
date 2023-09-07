## Install packages for CentOS 7

This is a runbook for installing necessary packages for CentOS. This needs
to be done as root.  


Ensure everything is up to date:  
`sudo yum check-update -y && sudo yum upgrade -y && sudo yum clean all -y`  

packages:
  - epel-release
  - nginx
  - rsync
  - jq
  - python3-devel
  - python3.6
  - vim
  - wget
  - curl
