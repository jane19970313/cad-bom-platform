# Public access and deployment

CAD2BOM can be opened by other people, but the frontend and API must be reachable from their browsers. A browser-side `localhost` URL always points to that visitor's own computer.

## LAN / single-server setup

Assume the machine running CAD2BOM is reachable as `192.168.1.50`. Replace that example with the server's actual LAN IP or public hostname.

### 1. Backend environment

In `backend/.env`, configure the frontend origins exactly (scheme, hostname, and port):

```env
ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000","http://192.168.1.50:3000"]
```

Do not use `allow_origins=["*"]` with credentialed authentication cookies. If the frontend is served from more than one known address, list each origin.

### 2. Frontend environment

In `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://192.168.1.50:8000/api/v1
```

Restart/rebuild Next.js after changing a `NEXT_PUBLIC_*` value. When this variable is omitted during LAN development, the client now derives the API host from the hostname used to open the site and targets port 8000.

### 3. Bind both servers to the network interface

Backend:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Frontend development server:

```bash
cd frontend
npm run dev -- --hostname 0.0.0.0
```

For a production Next.js build, use `npm run build` and then `npm run start -- --hostname 0.0.0.0`.

Allow inbound TCP traffic to ports 3000 and 8000 in the host firewall/router for a direct LAN test. For public internet deployment, prefer a reverse proxy with HTTPS rather than exposing the development server.

## Production / HTTPS

Set `NEXT_PUBLIC_API_BASE_URL` to the externally reachable HTTPS API URL, for example `https://api.example.com/api/v1`, and set `CORS_ORIGINS` to the exact frontend origin, for example `["https://app.example.com"]`. Set `ENVIRONMENT=production` so refresh cookies use the Secure attribute. The frontend build must be produced with the correct public API URL.

The database and Redis should remain on the server/private network; they do not need to be exposed to visitors.

## Authentication flow

- A visitor can open the site without an account.
- The header presents **Sign in** and **Create account** while the account is unauthenticated or being checked.
- A new registration is automatically signed in and sent to the dashboard.
- Existing users sign in and return to the dashboard.
- An expired authenticated session still redirects to sign-in; an anonymous visitor is not treated as a user with an expired session.
