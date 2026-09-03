# ProMão authentication testing

1. Register a client or provider through the UI and verify the role is saved.
2. Verify the response sets an httpOnly access_token cookie.
3. Refresh the page and verify `/api/auth/me` restores the session.
4. Log out and verify protected request creation returns 401.
5. Login with the registered credentials and verify the dashboard loads.
6. The Google button is a PREPARED FLOW and should show an explanatory message until Google OAuth credentials are configured.