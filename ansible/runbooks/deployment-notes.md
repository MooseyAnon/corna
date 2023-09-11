### Deployment Notes

Regardless of deployment approach some thought needs to be given to the costs
of each approach.

#### rsync
The big overhead here is copying changes and updates to the server. While it
is possible to only copy files that have been changed it makes sense to copy
everything over each time to maintain synchronization with the local copy.
The `--delete-after` and `--delete-excluded` flags ensure that anything that is
not a part of the `rsync` command on the remote sever are deleted to match
exactly what is in the local machines filesystem.  


While this is good, it means if any machine specific bugs come up during
deployment and are fixed on the server they must be exactly replicated on the
local machine otherwise they will be overwritten.


#### docker
While the docker deployment is largely trivial (as long as its builds
push/pulling will work), we need to create and manage a private docker registry
which comes with its own overhead. Firstly, this literally costs money. While
its not a bank breaking amount it needs to be considered. Secondly, managing
any API keys/passwords for the registry comes with its own pain if, for example
we need to rebuild the reg. Having said that, most cloud providers offer
managed private registry options so it shouldn't be too bad.  


#### SSL management
Regardless of deployment method we need to think about SSL certs and how we
get them on the server/container.  


If we go down the `rsync` route (which still involves building docker
containers on the remote host), we need to ensure that we copy over the SSL
certs to the right directory with the right permissions _and_ make sure that
the certs are within the docker build context otherwise we cant run `CP` at
docker build time. This means that the SSL certs need to live with the source
code on the remote host and not in the usual `/etc/nginx` directory.  

The larger problem for both options though, is that the certs will probably
live inside the vault. This is because we cant check in the private key but
also having it lying around the local file system isn't particularly safe
either.  

If we do deployments using `rsync` but via an ansible role this alleviates the
problem because ansible has access to the vault (which we have made
programmatic), however we could still face the aforementioned problem of the
docker build context.  

If we go down the docker route we would probably have to wrap `docker build` in
a bash script which first gets the needed value from the vault and then passes
that to `docker build`. For this to work we will need to change the vault
manager file into a command line script, to make it easy to access values.


#### Vault password
Various parts of the corna service needs access to the vault for sensitive
information (passwords etc). The vault is gated by a password. This password
needs to be accessible regardless of method of deployment.

With the `rsync` method we need to copy to the users home directory (
probably `/home/cornausr`) and set correct owner and perms (`600`).  

If using docker, we can pass the password in at build time via docker
`ARG`. Although this allows for potential leaks (if build is inspected)
as long as builds are done locally, for the time being, this should be
relatively secure.


more info:  
- https://vsupalov.com/docker-arg-env-variable-guide/
- https://devops.stackexchange.com/questions/3902/passing-secrets-to-a-docker-container
- https://earthly.dev/blog/docker-secrets/
