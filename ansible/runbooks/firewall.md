## Firewalling CentOS 7

Goals of firewall:  
  - whitelist incoming and outgoing connections to known ports (in public zone)
  - database connections should be in internal zone with IP addr as source
  - internal webserver ports (i.e. flask) should not be in whitelist

list of default ports:
- https://docs.oracle.com/en/storage/tape-storage/sl4000/slklg/default-port-numbers.html#GUID-8B442CCE-F94D-4DFB-9F44-996DE72B2558


iptables:
- https://help.ovhcloud.com/csm/en-gb-dedicated-servers-firewall-iptables?id=kb_article_view&sysparm_article=KB0043432
- https://bencane.com/2012/09/17/iptables-linux-firewall-rules-for-a-basic-web-server/
- https://www.digitalocean.com/community/tutorials/a-deep-dive-into-iptables-and-netfilter-architecture
- https://techprojournal.com/firewalld-vs-iptables/


This is good basic setup for webserver:  
- https://www.digitalocean.com/community/tutorials/iptables-essentials-common-firewall-rules-and-commands


for general "hardening":  
- https://phoenixnap.com/kb/linux-security

for icmp:  
- https://www.cyberciti.biz/tips/linux-iptables-9-allow-icmp-ping.html

for docker (may not be needed):
- https://www.fosslinux.com/100845/iptables-and-docker-securely-running-containers-with-iptables.htm
- https://serverfault.com/questions/1025628/how-can-i-use-iptables-on-top-of-docker-to-be-able-to-connect-to-the-internet-fr
