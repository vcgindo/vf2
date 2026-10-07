# Temporary fixture CAPTCHA policy on3006

Human authorization: controller turn `01a1149a-d80d-74a0-8e3c-6be987f5e6f9`,
7October2026. This exception is only for existing Stage2 fixture users2 and3
on the owned localhost3006 synthetic smoke/demo instance.

The original CAPTCHA is a client-only gate. No server CAPTCHA validation existed.
The new POST `/api/user/captcha-policy/` returns only an uncached boolean; it
does not log in, issue a token or change accounts. The frontend retains the
canvas/input and normal validation unless the server grants this exception.
Password login, rate limiting, inactive/deleted-account checks, session creation
and permissions use the unchanged login endpoint.

Both settings are required on the owned `user-service`:

```
VF_LOCAL_FIXTURE_CAPTCHA_EXEMPTION=1
VF_LOCAL_INSTANCE=freshvcf-daily3006
```

The policy also requires `BASE_CLIENT_URL=http://localhost:3006`, exact request
Origin, backend Host `localhost` (the existing proxy removes the port), runtime
database/schema `daily_3006`/`identity`, and the exact active, non-admin,
non-deleted `(id,email)` pair registered for each fixture. Headers are additional
guards; the actual network boundary remains127.0.0.1:3006 with no backend host
port. Errors, malformed responses and missing settings retain the CAPTCHA.
Other origins never consult the policy. No positive result is cached.

To restore enforcement, set `VF_LOCAL_FIXTURE_CAPTCHA_EXEMPTION=0` or remove it
from **only** `D:/freshvcf-build/daily-3006/compose.json`'s user-service environment,
then run:

```
docker compose -f D:/freshvcf-build/daily-3006/compose.json up -d --no-deps user-service
```

The next login submission falls back to the retained CAPTCHA without a frontend
rebuild. The previous frontend/user-service image identities are retained in
the activation receipt for full rollback. Existing authenticated sessions keep
their normal lifecycle. Never apply these settings to3005 or other instances.

Focused proof covers server guards, frontend error/default behavior, unchanged
submitted credential snapshot, duplicate-submit prevention, and actual browser
login. This exception is not CAPTCHA parity or whole-application acceptance.
