"""Create (or update) the LOGIN users the services connect as, inside the NOLOGIN group roles from
db/migrations/007_roles.sql. Idempotent; run as the database owner AFTER `db/setup.py migrate`.

    SPOT_APP_USER / SPOT_APP_PASSWORD   -> member of spot_app         (backend)
    SPOT_MCP_USER / SPOT_MCP_PASSWORD   -> member of spot_mcp_reader  (mcp server; system1's call logging)

Used by the compose `db-init` job. Works against Neon too (DATABASE_URL = the owner's URL); if the owner may not
CREATE ROLE there, create the users in the Neon console and re-run.
"""
import os
import sys

import psycopg
from psycopg import sql

PAIRS = [("SPOT_APP_USER", "SPOT_APP_PASSWORD", "spot_app_user", "spot_app"),
         ("SPOT_MCP_USER", "SPOT_MCP_PASSWORD", "spot_mcp_user", "spot_mcp_reader")]


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("db_login_roles: DATABASE_URL is not set", file=sys.stderr)
        return 2
    with psycopg.connect(url, autocommit=True) as conn:
        for user_var, pw_var, default_user, group in PAIRS:
            user = os.environ.get(user_var) or default_user
            pw = os.environ.get(pw_var)
            if not pw:
                print("db_login_roles: %s unset, skipping %s" % (pw_var, user))
                continue
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (group,)).fetchone():
                print("db_login_roles: group role %s missing (run migrate first)" % group, file=sys.stderr)
                return 1
            exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (user,)).fetchone()
            verb = sql.SQL("ALTER" if exists else "CREATE")
            conn.execute(sql.SQL("{} ROLE {} LOGIN PASSWORD {}").format(verb, sql.Identifier(user), sql.Literal(pw)))
            conn.execute(sql.SQL("GRANT {} TO {}").format(sql.Identifier(group), sql.Identifier(user)))
            print("db_login_roles: %s %s in %s" % ("updated" if exists else "created", user, group))
    return 0


if __name__ == "__main__":
    sys.exit(main())
