## Docker deployment

This is a relatively trivial deployment.

Steps:  
  - create private docker registry
  - build containers locally and push them up to the registry
  - `rsync` over the docker compose file
  - pull and run via docker compose
