## PostgreSQL

This is a runbook for simple postgres config. This is currently done directly
in the database server but should be easily moved to ansible.  


Assumed database user is mooseyanon.  


NOTE: to connect to the DB from the server `postgres` must be installed on it,
however we install it as part of docker so we do not need to do it on the
server directly.  


create user with permission to create a db  and pwd  
`CREATE USER mooseyanon WITH CREATEDB ENCRYPTED PASSWORD <password>;`  
create database  
`CREATE DATABASE <some-db-name> WITH ENCODING = 'UTF8' OWNER = mooseyanon;`  


deleting:  
drop table  
`DROP DATABASE IF EXISTS <table name>;`  
delete user  
`DROP USER IF EXISTS <username>;`  
