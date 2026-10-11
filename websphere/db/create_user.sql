-- Optional: creates the database user that owns the Practice Shop tables.
-- Run as a DBA (for example SYSTEM). On a multitenant database connect to the pluggable database first,
-- for example:   ALTER SESSION SET CONTAINER = ORCLPDB1;
-- Change the password before running. WebSphere needs the same user name and password (step 2 of the guide).

CREATE USER shop IDENTIFIED BY "Change_this_password_1"
  DEFAULT TABLESPACE users
  TEMPORARY TABLESPACE temp
  QUOTA 100M ON users;

GRANT CREATE SESSION, CREATE TABLE TO shop;
