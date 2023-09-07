## Disable root

This playbook is for disabling root access on CentOS linux servers (have
not tested on Debian but I'm sure its the same).

NOTE: another user with root-ly privilages (i.e. can run `sudo`) must exist.  

`vi /etc/ssh/sshd_config` --> this may need `sudo`  
search and replace the following:  
`PasswordAuthentication no  
PermitRootLogin no`  


close and restart `sshd`:  
`sudo systemctl restart sshd`
