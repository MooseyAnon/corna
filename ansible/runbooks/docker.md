## Docker

Runbook for docker installation on CentOS 7, installation info comes from
docker website[1]:  

[1] https://docs.docker.com/engine/install/centos/  

unintall old version:  
`sudo yum remove docker \  
    docker-client \  
    docker-client-latest \  
    docker-common \  
    docker-latest \  
    docker-latest-logrotate \  
    docker-logrotate \  
    docker-engine  
`


install docker repo:  
`sudo yum install -y yum-utils`  
`sudo yum-config-manager --add-repo \  
    https://download.docker.com/linux/centos/docker-ce.repo`  


install docker  
`sudo yum install \  
    docker-ce \  
    docker-ce-cli \  
    containerd.io \  
    docker-buildx-plugin \  
    docker-compose-plugin  
`


start docker service  
`sudo systemctl start docker`  


user needs to be added to docker group in order to run docker commands without
`sudo`


create docker group (although it should exist after installing docker)  
`sudo groupadd docker`  
add user to group  
`sudo usermod -aG docker $USER`  
---- logout and then log back in -----  
test  
`docker run hello-world`  


### extra notes

#### build stage
docker build context and coping files into containers during build stage (we
do this for SSL certs):

for docker to copy a file it must be in the build context (
i.e. were `docker build` is called from) so to copy the ssl certs
into the container they must first be copied to a local dir (this is
very annoying).

for nginx to be able to read the ssl certs and recognise it as a trusted
cert the perms (locally) need to be `644`.

remember to open port 443 in the container!!


#### networking
getting containers talking:

in order to get two (or more)containers to talk, they must share a docker
network bridge. This bridge needs to be manually created. Once the bridge is
created you need to give the containers names while connecting them to the bridge.

This name is then accessible inside other containers on the same bridge. The
docker bridge dns is able to resolve to name to the correct container. This is
due to each container having its own IP addr assigned to it from the network
bridge, as such localhost or 127.0.0.1 are not the same inside the docker
container and the OS. So even though localhost could be used to access a
containers exposed port at OS level, containers on the network bridge must use
its name.

Furthermore, containers on the same network bridge do not access each other via
their exposed port but the port a webservices uses inside its container.
e.g. if inside the container flask uses port `8080` and port `8000` gets
exposed during the `docker run` command (and from inside the container i.e
`EXPOSE` is used?), other containers on the same network bridge would use the
`8080` port number not `8000`.

One obvious benefit of this is that you then do not need to expose ports for
containers that are not supposed to be interacted with from the outside e.g.
you would only expose `nginx` and not the flask webservice containers.

Docker compose simplifies this process of managing multiple containers and
their network namespaces.

Docker networking only works on the containers on the same host, load balancing
across hosts would require a different solution (usually k8s).
