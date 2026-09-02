-- Corna PostgreSQL provisioning
--
-- This script is intended to be run by an existing PostgreSQL superuser
-- (normally the default "postgres" user).
--
-- It creates:
--   - corna_admin: used for migrations and schema changes.
--   - corna_app:   used by the running application.
--   - corna:       application database, owned by corna_admin.
--
-- Passwords and database/user names are passed in through psql variables.
--
-- Expected variables:
--   db_name
--   admin_user
--   admin_password
--   app_user
--   app_password
--
-- Example invocation:
--
--   psql \
--     -U postgres \
--     -v db_name=corna \
--     -v admin_user=corna_admin \
--     -v admin_password='...' \
--     -v app_user=corna_app \
--     -v app_password='...' \
--     -f provision.sql
--
-- Important:
-- CREATE DATABASE cannot run inside a transaction block, so database creation
-- is handled separately from the conditional role creation below.


-- ---------------------------------------------------------------------------
-- Roles
-- ---------------------------------------------------------------------------
-- PostgreSQL "users" are roles with LOGIN enabled.
--
-- Role creation is idempotent:
--   - if the role does not exist, create it with the supplied password;
--   - if the role already exists, leave it completely unchanged.
--
-- Rerunning provisioning must not silently rotate passwords or modify role
-- attributes. Password rotation should be an explicit operation.

SELECT format(
    'CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L',
    :'admin_user',
    :'admin_password'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = :'admin_user'
)
\gexec


SELECT format(
    'CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L',
    :'app_user',
    :'app_password'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = :'app_user'
)
\gexec


-- ---------------------------------------------------------------------------
-- Database
-- ---------------------------------------------------------------------------
-- corna_admin owns the database. This is the account Alembic should use when
-- creating or altering schema objects.
--
-- \gexec executes the generated CREATE DATABASE statement only when the
-- database does not already exist.

SELECT format(
    'CREATE DATABASE %I OWNER %I',
    :'db_name',
    :'admin_user'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = :'db_name'
)
\gexec


-- ---------------------------------------------------------------------------
-- Connect to the application database
-- ---------------------------------------------------------------------------
-- Everything below this point configures permissions inside the Corna database.

\connect :db_name


-- ---------------------------------------------------------------------------
-- Database access
-- ---------------------------------------------------------------------------
-- PUBLIC means every PostgreSQL role. Revoke the default connection permission
-- and explicitly allow only the Corna accounts.
--
-- The postgres superuser is unaffected by these restrictions.

REVOKE CONNECT ON DATABASE :"db_name" FROM PUBLIC;

GRANT CONNECT ON DATABASE :"db_name"
TO :"admin_user", :"app_user";


-- ---------------------------------------------------------------------------
-- public schema
-- ---------------------------------------------------------------------------
-- PostgreSQL installations commonly include a "public" schema.
--
-- corna_admin needs CREATE so migrations can create tables, indexes, sequences,
-- and other schema objects.
--
-- corna_app only needs USAGE so it can access objects inside the schema.

REVOKE CREATE ON SCHEMA public FROM PUBLIC;

GRANT USAGE, CREATE ON SCHEMA public
TO :"admin_user";

GRANT USAGE ON SCHEMA public
TO :"app_user";


-- ---------------------------------------------------------------------------
-- Existing tables
-- ---------------------------------------------------------------------------
-- This matters when provisioning is rerun against a database that already has
-- migrations applied.
--
-- The application may read and mutate data, but it cannot ALTER or DROP tables.

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA public
TO :"app_user";


-- ---------------------------------------------------------------------------
-- Existing sequences
-- ---------------------------------------------------------------------------
-- PostgreSQL sequences are commonly used by SERIAL / identity-backed integer
-- primary keys.
--
-- USAGE allows the application to obtain the next sequence value.
-- SELECT allows it to inspect the current value when required.

GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA public
TO :"app_user";


-- ---------------------------------------------------------------------------
-- Future tables
-- ---------------------------------------------------------------------------
-- Grants on "ALL TABLES" only affect objects that already exist.
--
-- Alembic will create future tables as corna_admin, so configure that role's
-- default privileges to automatically grant CRUD permissions to corna_app.

ALTER DEFAULT PRIVILEGES
FOR ROLE :"admin_user"
IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLES
TO :"app_user";


-- ---------------------------------------------------------------------------
-- Future sequences
-- ---------------------------------------------------------------------------
-- Apply the same rule to sequences created by future migrations.

ALTER DEFAULT PRIVILEGES
FOR ROLE :"admin_user"
IN SCHEMA public
GRANT USAGE, SELECT
ON SEQUENCES
TO :"app_user";
