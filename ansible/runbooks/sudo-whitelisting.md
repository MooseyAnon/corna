## Sudo management

Its possible to give users permissions to run _select_ commands as `sudo`.
This is commonly done by editing the `/etc/sudoers` file.  

NOTE: you should only edit the `sudoers` file using `visudo` as it checks
everything is correct before saving and closing the file. Without it, it is
very easy to get something wrong and shut all users out of the system by not
letting anyone use `sudo`.  

To edit file:  
`sudo visudo -f /etc/sudoers` (`-f` flag is "file open")  

By default the first account made on the system will will be in the
`admin/wheel/sudoers` group meaning they can run any command with `sudo`.
However, `sudo` privileges must be manually configured for any user account
made after.  


Selective `sudo` powers are relatively straight forward. It is possible to
whitelist only the commands a user is allowed to run under `sudo` e.g.
say we want a user to only be able to run network related commands we do the
following:  

`mkdir /etc/sudoers.d` (we can add new config files in here and then load them
    into the main `sudoers` file)  
` touch /etc/sudoer.d/netadminperms`  

You need to give full path for each command  
`Cmnd_Alias IPTABLES=/usr/bin/iptables, ...<other-commands>` 
`Cmnd_Alias CAPTURE=/usr/bin/tcpdump`  
`Cmnd_Alias NETALL=IPTABLES, CAPTURE`  
Then assign the commands to a group (`%` if for assigning to group name)  
`%netadmin ALL=NETALL`  
Add user to group (in this case `netadmin`)  
`usermod -a -G netadmin <username>`  
this allows the user to only be able to run commands defined the
`netadminperms` file as `sudo`.  

for more info go to: https://www.youtube.com/watch?v=YSSIm0g00m4
