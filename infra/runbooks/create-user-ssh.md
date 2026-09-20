## Create account for user with SSH keys

This runbook creates a new user account which allows access via SSH
rather than with a password.  


Assume username == `moosey.anon`.  


`useradd -m -d /home/moosey.anon -s /bin/bash moosey.anon`  
`passwd moosey.anon <new-strong-password>`  
`mkdir -p /home/moosey.anon/.ssh`  
copy over pubic key, this will need to be done via another user or root
if `authorized_keys` file does not already exists. Otherwise manually copy
and paste.  
`scp <path-to-public-key-on-local-machine> root@<sever-name-or-ip>:/home/moosey.anon/.ssh/authorized_keys`  
`chown -R moosey.anon:moosey.anon /home/moosey.anon/`  
`chown -R moosey.anon:moosey.anon /home/moosey.anon/.ssh`  
`chmod 700 /home/moosey.anon/.ssh/`  
`chmod 600 /home/moosey.anon/.ssh/authorized_keys`  
`usermod -a -G wheel moosey.anon`  


restart `sshd`:  
`sudo systemctl restart sshd`  


Whats this doing:  
- add a new user using `useradd`. `-d` sets valie for `HOME_DIR` env variable.
    `-m` creates home directory if it does not exist. `-s` sets users login shell.  
- create `ssh` directory and add users public key to `authorized_keys`  
- set ownership and group of home directory and `ssh` directory  
- set mode of `ssh` directory and `authorized_key` file  
- `authorized_keys` file needs to be 600 otherwise `ssh` complains and wont
    work.  
- add user to `wheel` (CentOS version of `sudoers`) which gives user `sudo`
    powers.  
