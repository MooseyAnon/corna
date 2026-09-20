## Configuration order

This runbook sets out the order of the steps needed to fully configure
a corna webserver.  

steps (in order):
- install and update packages (minus docker) (/intall-packages.md)
- create user - bother admin and basic "cornauser" (/create-user-ssh.md)
- disable root (/disable-root.md)
- install docker + add users to docker group (/docker.md)
- firewall (/firewall.md)
