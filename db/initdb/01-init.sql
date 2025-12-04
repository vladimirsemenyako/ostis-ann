CREATE USER keycloak_user WITH ENCRYPTED PASSWORD 'admin';

CREATE DATABASE keycloak OWNER keycloak_user;