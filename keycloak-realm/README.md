## Keycloak realm export for `ostis-ann`

This directory is intended to store the **JSON export of the `ostis-ann` realm** from Keycloak.

It allows other developers to recreate the same realm configuration when they start the project
using `docker compose`.

### Exporting the `ostis-ann` realm via CLI (inside the Keycloak container)

1. Make sure the Keycloak container is running:

   ```bash
   docker compose up -d keycloak
   ```

2. Open a shell inside the Keycloak container:

   ```bash
   docker exec -it keycloak /bin/bash
   ```

3. Log in to the admin CLI (`kcadm.sh`):

   ```bash
   /opt/keycloak/bin/kcadm.sh config credentials \
     --server http://localhost:8080 \
     --realm master \
     --user "$KC_BOOTSTRAP_ADMIN_USERNAME" \
     --password "$KC_BOOTSTRAP_ADMIN_PASSWORD"
   ```

4. Export the `ostis-ann` realm as JSON to a temporary directory (the import directory is read-only):

   ```bash
   /opt/keycloak/bin/kc.sh export \
     --realm ostis-ann \
     --file /tmp/ostis-ann-realm.json
   ```

   Notes:
   - By default, this command exports realm configuration, clients, roles, groups, etc., without users.
   - To include users in the same file, add `--users same_file` to the command.
   - The `/opt/keycloak/data/import` directory is mounted as read-only, so we export to `/tmp` first.

5. Exit the container shell:

   ```bash
   exit
   ```

6. Copy the exported file from the container to the host machine:

   ```bash
   docker cp keycloak:/tmp/ostis-ann-realm.json ./keycloak-realm/ostis-ann-realm.json
   ```

   The file will now be available in the project directory:

```text
keycloak-realm/ostis-ann-realm.json
```

7. Commit this file to the repository if you want others to reuse the same realm configuration.

### How realm import is enabled on startup

In `docker-compose.yml`, the Keycloak service is configured to:

- mount this directory into the container at `/opt/keycloak/data/import` as read-only (`:ro`)
- start with the `--import-realm` flag

On the first startup (or with a clean PostgreSQL database), Keycloak will read any `*.json`
files from `/opt/keycloak/data/import` and automatically create the `ostis-ann` realm
with the exported configuration.

**Note**: The directory is mounted as read-only to prevent accidental modifications from inside
the container. To export a realm, use the CLI method described above and copy the file using `docker cp`.

> ⚠️ Important: The JSON export may contain sensitive data
> (client secrets, roles, possibly users). Review the file before publishing
> it to a public GitHub repository and remove or rotate any secrets if necessary.

