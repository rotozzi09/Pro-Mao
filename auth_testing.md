# ProMão authentication testing

1. Register a client or provider through the UI and verify the role is saved.
2. Verify the response sets an httpOnly access_token cookie.
3. Refresh the page and verify `/api/auth/me` restores the session.
4. Log out and verify protected request creation returns 401.
5. Login with the registered credentials and verify the dashboard loads.
6. Click Google and verify the redirect uses the current browser origin; after callback, verify the `session_id` is exchanged server-side and a session cookie is created.
7. Provider: add a catalog item with and without product inclusion, upload a photo, and verify it remains pending authorization.
8. Client: verify pending portfolio photos can be authorized and only authorized photos are returned publicly.
9. Provider: publish a proposal against an open client request with price, ETA and conditions.