# OAuth Integration Setup Guide

This guide explains how to set up GitHub and Google OAuth authentication for Ardha.

## Overview

Ardha supports social login via:
- **GitHub OAuth** - Login with GitHub account
- **Google OAuth** - Login with Google account

Both providers support:
- ✅ New user registration via OAuth
- ✅ Linking OAuth to existing email accounts
- ✅ Secure state parameter for CSRF protection
- ✅ Automatic token refresh (where supported)

---

## Prerequisites

Before setting up OAuth:
1. **Ardha backend** running at your domain/IP (e.g., `http://82.29.164.29:8000`)
2. **Ardha frontend** running at your domain/IP (e.g., `http://82.29.164.29:3000`)
3. GitHub and/or Google accounts for creating OAuth apps

---

## Part 1: GitHub OAuth Setup

### Step 1: Create GitHub OAuth App

1. Go to https://github.com/settings/developers
2. Click **"New OAuth App"** (or "New GitHub App" for production)
3. Fill in the application details:

```
Application name: Ardha (or "Ardha Dev" for development)
Homepage URL: http://82.29.164.29:3000
Authorization callback URL: http://82.29.164.29:3000/auth/callback/github
```

**For Production:**
```
Homepage URL: https://yourdomain.com
Authorization callback URL: https://yourdomain.com/auth/callback/github
```

4. Click **"Register application"**
5. You'll see:
   - **Client ID** - Copy this
   - **Generate a new client secret** button - Click it and copy the secret

⚠️ **Important**: The client secret is shown only once! Save it securely.

### Step 2: Configure Backend (GitHub)

1. Open `backend/.env`
2. Add your GitHub OAuth credentials:

```bash
# GitHub OAuth
OAUTH__GITHUB_CLIENT_ID=your_actual_github_client_id_here
OAUTH__GITHUB_CLIENT_SECRET=your_actual_github_client_secret_here
```

**Note**: Use double underscores (`__`) for nested config (Pydantic Settings format).

### Step 3: Configure Frontend (GitHub)

1. Create `frontend/.env.local` (if doesn't exist)
2. Add GitHub client ID:

```bash
# GitHub OAuth (public client ID only - safe to expose)
NEXT_PUBLIC_GITHUB_CLIENT_ID=your_actual_github_client_id_here

# API URLs (adjust to your deployment)
NEXT_PUBLIC_API_URL=http://82.29.164.29:8000
NEXT_PUBLIC_APP_URL=http://82.29.164.29:3000
```

**Note**: Only add the CLIENT_ID to frontend (never the secret!).

---

## Part 2: Google OAuth Setup

### Step 1: Create Google OAuth 2.0 Client

1. Go to https://console.cloud.google.com/apis/credentials
2. Create a project (if you don't have one):
   - Click **"Select a project"** → **"New Project"**
   - Name: "Ardha" → **Create**

3. Enable required APIs:
   - Go to **"APIs & Services"** → **"Library"**
   - Search for "Google+ API" → **Enable**
   - Search for "People API" → **Enable**

4. Create OAuth 2.0 credentials:
   - Go to **"Credentials"** → **"Create Credentials"** → **"OAuth client ID"**
   - If prompted, configure OAuth consent screen first (see below)

5. Configure OAuth client:

```
Application type: Web application
Name: Ardha

Authorized JavaScript origins:
  - http://82.29.164.29:3000

Authorized redirect URIs:
  - http://82.29.164.29:3000/auth/callback/google
```

**For Production:**
```
Authorized JavaScript origins:
  - https://yourdomain.com

Authorized redirect URIs:
  - https://yourdomain.com/auth/callback/google
```

6. Click **"Create"**
7. Copy **Client ID** and **Client Secret**

### Step 2: Configure OAuth Consent Screen (Required)

Before creating credentials, Google requires consent screen configuration:

1. Go to **"OAuth consent screen"**
2. Choose user type:
   - **Internal**: For Google Workspace only (if applicable)
   - **External**: For public access (choose this for Ardha)

3. Fill in app information:
```
App name: Ardha
User support email: your-email@example.com
Developer contact: your-email@example.com

Scopes: (add these)
  - userinfo.email
  - userinfo.profile
  - openid
```

4. Add test users (for development):
   - Add your email and any testers
   - Only these users can use OAuth until app is verified

5. Save and continue

### Step 3: Configure Backend (Google)

1. Open `backend/.env`
2. Add your Google OAuth credentials:

```bash
# Google OAuth
OAUTH__GOOGLE_CLIENT_ID=your_actual_google_client_id_here
OAUTH__GOOGLE_CLIENT_SECRET=your_actual_google_client_secret_here
```

### Step 4: Configure Frontend (Google)

1. Open `frontend/.env.local`
2. Add Google client ID:

```bash
# Google OAuth (public client ID only)
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_actual_google_client_id_here
```

---

## Part 3: Restart Services

After configuring OAuth credentials, restart both services:

```bash
cd ~/ardha-projects/Ardha

# Rebuild and restart backend (to load new .env)
docker compose build backend
docker compose up -d backend

# Rebuild and restart frontend (to load new .env.local)
docker compose build frontend
docker compose up -d frontend

# Check logs for errors
docker compose logs backend --tail 50
docker compose logs frontend --tail 50
```

---

## Part 4: Testing OAuth Integration

### Test GitHub OAuth

1. **Visit login page**: http://82.29.164.29:3000/login

2. **Click "Log in with GitHub"**:
   - Should redirect to GitHub authorization page
   - URL should be: `https://github.com/login/oauth/authorize?client_id=...&state=...`
   - Check that state parameter exists (CSRF protection)

3. **Authorize Ardha on GitHub**:
   - Click **"Authorize [your-app-name]"**
   - GitHub redirects to: `http://82.29.164.29:3000/auth/callback/github?code=...&state=...`

4. **Processing callback**:
   - Should see "Authenticating with GitHub..." spinner
   - Then redirect to `/dashboard`
   - You should be logged in! ✅

5. **Verify in database**:
```bash
docker compose exec postgres psql -U ardha -d ardha
SELECT id, email, username, github_id FROM users WHERE github_id IS NOT NULL;
\q
```

### Test Google OAuth

1. **Visit login page**: http://82.29.164.29:3000/login

2. **Click "Log in with Google"**:
   - Should redirect to Google authorization page
   - URL should be: `https://accounts.google.com/o/oauth2/v2/auth?client_id=...&state=...`

3. **Select Google account**:
   - Choose your Google account
   - Click **"Continue"** or **"Allow"**
   - Google redirects to: `http://82.29.164.29:3000/auth/callback/google?code=...&state=...`

4. **Processing callback**:
   - Should see "Authenticating with Google..." spinner
   - Then redirect to `/dashboard`
   - You should be logged in! ✅

5. **Verify in database**:
```bash
docker compose exec postgres psql -U ardha -d ardha
SELECT id, email, username, google_id FROM users WHERE google_id IS NOT NULL;
\q
```

### Test Account Linking

This tests whether OAuth can link to existing email/password accounts:

1. **Create email/password account**:
   - Visit http://82.29.164.29:3000/register
   - Register with email: `test@example.com`
   - Password: `TestPass123!`
   - Username: `testuser`
   - Full name: `Test User`
   - ✅ Account created

2. **Logout** (top-right menu)

3. **Login with GitHub** (if your GitHub email is `test@example.com`):
   - Click "Log in with GitHub"
   - Authorize Ardha
   - ✅ Should link to existing account!

4. **Verify linking**:
```bash
docker compose exec postgres psql -U ardha -d ardha
SELECT email, username, github_id FROM users WHERE email = 'test@example.com';
# Should show github_id populated!
\q
```

---

## Part 5: Troubleshooting

### Issue: "GitHub OAuth is not configured"

**Symptom**: Backend returns 500 error with message "GitHub OAuth is not configured on this server"

**Solution**:
1. Check `backend/.env` has OAuth credentials
2. Verify environment variable format: `OAUTH__GITHUB_CLIENT_ID` (double underscore)
3. Restart backend: `docker compose restart backend`
4. Check logs: `docker compose logs backend --tail 50`

### Issue: "Failed to fetch" or CORS error

**Symptom**: Browser console shows "Failed to fetch" when calling OAuth endpoints

**Solution**:
1. Verify backend is running: `curl http://82.29.164.29:8000/health`
2. Check CORS is configured to allow frontend origin
3. Verify `NEXT_PUBLIC_API_URL` in frontend/.env.local
4. Rebuild frontend: `docker compose build frontend && docker compose up -d frontend`

### Issue: "Invalid state parameter"

**Symptom**: Callback page shows "Invalid state parameter - possible CSRF attack"

**Solution**:
1. This is a security feature - ensure you're not manually tampering with URLs
2. Clear browser cache and cookies
3. Try OAuth flow again from the beginning
4. Check browser console for sessionStorage errors

### Issue: "GitHub account must have public email"

**Symptom**: GitHub OAuth fails with email requirement error

**Solution**:
1. Go to https://github.com/settings/emails
2. Make at least one email public, OR
3. Update GitHub OAuth scope to request private emails (backend code already handles this)

### Issue: "Access denied" error

**Symptom**: OAuth provider shows in callback URL: `?error=access_denied`

**Solution**:
- User clicked "Cancel" or "Deny" on authorization page
- This is expected behavior - user cancelled authentication
- Callback page will show friendly error message

### Issue: Google OAuth only works for test users

**Symptom**: Google OAuth works for you but not other users

**Solution**:
1. Your Google OAuth app is in "Testing" mode
2. Only test users (added in OAuth consent screen) can use it
3. To allow all users:
   - Go to OAuth consent screen
   - Click **"Publish App"**
   - Submit for Google verification (required for production)

---

## Part 6: Production Deployment

### Security Checklist for Production

- [ ] Use HTTPS for all URLs (frontend and backend)
- [ ] Update OAuth redirect URIs to HTTPS URLs
- [ ] Restrict CORS origins to your actual domain
- [ ] Use secure cookies (httpOnly, secure, sameSite)
- [ ] Enable rate limiting on OAuth endpoints
- [ ] Monitor OAuth usage and errors
- [ ] Rotate OAuth secrets regularly
- [ ] Never commit `.env` files to Git

### Production Environment Variables

**Backend (`backend/.env`):**
```bash
# Security
OAUTH__GITHUB_CLIENT_ID=prod_github_client_id
OAUTH__GITHUB_CLIENT_SECRET=prod_github_client_secret
OAUTH__GOOGLE_CLIENT_ID=prod_google_client_id.apps.googleusercontent.com
OAUTH__GOOGLE_CLIENT_SECRET=prod_google_client_secret

# URLs (HTTPS in production!)
APP_ENV=production
DEBUG=false
```

**Frontend (`frontend/.env.local`):**
```bash
# OAuth (production client IDs)
NEXT_PUBLIC_GITHUB_CLIENT_ID=prod_github_client_id
NEXT_PUBLIC_GOOGLE_CLIENT_ID=prod_google_client_id.apps.googleusercontent.com

# URLs (HTTPS in production!)
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_APP_URL=https://yourdomain.com
```

---

## Part 7: API Reference

### Backend Endpoints

**GitHub OAuth:**
```bash
POST /api/v1/auth/oauth/github
Content-Type: application/json

Request:
{
  "code": "authorization_code_from_github"
}

Response (200 OK):
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "githubuser",
    "full_name": "GitHub User",
    "avatar_url": "https://avatars.githubusercontent.com/..."
  }
}
```

**Google OAuth:**
```bash
POST /api/v1/auth/oauth/google
Content-Type: application/json

Request:
{
  "code": "authorization_code_from_google"
}

Response (200 OK):
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "googleuser",
    "full_name": "Google User",
    "avatar_url": "https://lh3.googleusercontent.com/..."
  }
}
```

### Frontend OAuth Hook

```typescript
import { useOAuth } from "@/hooks/use-oauth";

function LoginPage() {
  const { loginWithGitHub, loginWithGoogle } = useOAuth();

  return (
    <>
      <button onClick={loginWithGitHub}>
        Login with GitHub
      </button>
      <button onClick={loginWithGoogle}>
        Login with Google
      </button>
    </>
  );
}
```

---

## Part 8: Database Schema

OAuth authentication uses the User model's built-in OAuth fields:

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    password_hash VARCHAR(255),  -- NULL for OAuth-only users

    -- OAuth provider IDs (unique, indexed)
    github_id VARCHAR(100) UNIQUE,
    google_id VARCHAR(100) UNIQUE,

    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    last_login_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for OAuth lookups
CREATE INDEX idx_users_github_id ON users(github_id);
CREATE INDEX idx_users_google_id ON users(google_id);
```

**No additional tables needed!** OAuth IDs are stored directly on the User model.

---

## Part 9: OAuth Flow Diagrams

### GitHub OAuth Flow

```
User clicks "Login with GitHub"
    ↓
Frontend generates state parameter (CSRF protection)
    ↓
Frontend redirects to:
https://github.com/login/oauth/authorize
  ?client_id=XXX
  &redirect_uri=http://82.29.164.29:3000/auth/callback/github
  &scope=read:user user:email
  &state=random_secure_string
    ↓
User authorizes app on GitHub
    ↓
GitHub redirects to callback with code:
http://82.29.164.29:3000/auth/callback/github
  ?code=authorization_code
  &state=random_secure_string
    ↓
Frontend callback page verifies state
    ↓
Frontend sends code to backend:
POST /api/v1/auth/oauth/github { "code": "..." }
    ↓
Backend exchanges code for GitHub access token
    ↓
Backend fetches user info from GitHub API
    ↓
Backend creates/updates user in database:
  - If github_id exists → login existing user
  - If email exists → link GitHub to account
  - If neither → create new user
    ↓
Backend returns JWT tokens + user data
    ↓
Frontend stores tokens and redirects to /dashboard
```

### Google OAuth Flow

```
User clicks "Login with Google"
    ↓
Frontend generates state parameter
    ↓
Frontend redirects to:
https://accounts.google.com/o/oauth2/v2/auth
  ?client_id=XXX
  &redirect_uri=http://82.29.164.29:3000/auth/callback/google
  &response_type=code
  &scope=openid email profile
  &state=random_secure_string
  &access_type=offline
  &prompt=consent
    ↓
User selects Google account and authorizes
    ↓
Google redirects to callback with code:
http://82.29.164.29:3000/auth/callback/google
  ?code=authorization_code
  &state=random_secure_string
    ↓
Frontend callback page verifies state
    ↓
Frontend sends code to backend:
POST /api/v1/auth/oauth/google { "code": "..." }
    ↓
Backend exchanges code for Google access token
    ↓
Backend fetches user info from Google API
    ↓
Backend creates/updates user in database
    ↓
Backend returns JWT tokens + user data
    ↓
Frontend stores tokens and redirects to /dashboard
```

---

## Part 10: Security Considerations

### State Parameter (CSRF Protection)

The state parameter prevents CSRF attacks:

```typescript
// Frontend generates random state
const state = crypto.getRandomValues(new Uint8Array(32));
sessionStorage.setItem('oauth_state', state);

// Include in authorization URL
const authUrl = `https://github.com/login/oauth/authorize?state=${state}&...`;

// Verify on callback
const callbackState = new URLSearchParams(window.location.search).get('state');
if (callbackState !== sessionStorage.getItem('oauth_state')) {
  throw new Error('CSRF attack detected!');
}
```

### Secure Token Storage

- **Access tokens**: Stored in frontend localStorage (short-lived, 15min)
- **Refresh tokens**: Stored in httpOnly cookies (7 days, not accessible to JavaScript)
- **OAuth secrets**: Never sent to frontend (server-side only)

### Account Linking Logic

When a user authenticates with OAuth:

1. **Check github_id/google_id**: If exists, login that user
2. **Check email**: If exists but no OAuth ID, link OAuth to account
3. **Create new**: If email doesn't exist, create new user

**Example**:
```
User "john@example.com" exists (password account)
User logs in with GitHub (email: john@example.com)
→ Links GitHub to existing account (sets github_id)
→ User can now login with either password OR GitHub
```

---

## Part 11: Common Issues & Solutions

### "Missing client_id" Error

**Issue**: OAuth provider shows error about missing or invalid client_id

**Cause**: Frontend environment variable not loaded

**Fix**:
```bash
# Verify .env.local exists
ls -la frontend/.env.local

# Check it contains client IDs
cat frontend/.env.local

# Rebuild frontend (environment variables baked into build)
docker compose build frontend
docker compose up -d frontend
```

### "Redirect URI mismatch" Error

**Issue**: OAuth provider rejects redirect with URI mismatch

**Cause**: Callback URL in OAuth app doesn't match actual callback URL

**Fix**:
1. Check exact callback URL in browser when error occurs
2. Go to OAuth app settings (GitHub/Google)
3. Ensure redirect URI EXACTLY matches (including http/https, port, path)
4. Common mistake: `http` vs `https`, or missing `/auth/callback/github`

### Testing with localhost vs Public IP

**Localhost (127.0.0.1) vs Public IP (82.29.164.29)**:

If using localhost:
```bash
# Frontend .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000

# OAuth app callback URLs
http://localhost:3000/auth/callback/github
http://localhost:3000/auth/callback/google
```

If using public IP:
```bash
# Frontend .env.local
NEXT_PUBLIC_API_URL=http://82.29.164.29:8000
NEXT_PUBLIC_APP_URL=http://82.29.164.29:3000

# OAuth app callback URLs
http://82.29.164.29:3000/auth/callback/github
http://82.29.164.29:3000/auth/callback/google
```

**Important**: OAuth apps can't use both! Create separate OAuth apps for localhost vs deployment.

---

## Part 12: Quick Start Checklist

### GitHub OAuth Quick Setup

- [ ] Create GitHub OAuth app at https://github.com/settings/developers
- [ ] Copy Client ID and Secret
- [ ] Add to `backend/.env`: `OAUTH__GITHUB_CLIENT_ID` and `OAUTH__GITHUB_CLIENT_SECRET`
- [ ] Add to `frontend/.env.local`: `NEXT_PUBLIC_GITHUB_CLIENT_ID`
- [ ] Restart backend: `docker compose restart backend`
- [ ] Rebuild frontend: `docker compose build frontend && docker compose up -d frontend`
- [ ] Test: Visit http://82.29.164.29:3000/login → Click "Login with GitHub"

### Google OAuth Quick Setup

- [ ] Create Google Cloud project at https://console.cloud.google.com
- [ ] Enable Google+ API and People API
- [ ] Configure OAuth consent screen
- [ ] Create OAuth 2.0 Client ID
- [ ] Copy Client ID and Secret
- [ ] Add to `backend/.env`: `OAUTH__GOOGLE_CLIENT_ID` and `OAUTH__GOOGLE_CLIENT_SECRET`
- [ ] Add to `frontend/.env.local`: `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
- [ ] Restart backend: `docker compose restart backend`
- [ ] Rebuild frontend: `docker compose build frontend && docker compose up -d frontend`
- [ ] Test: Visit http://82.29.164.29:3000/login → Click "Login with Google"

---

## Support

For issues or questions:
- Check logs: `docker compose logs backend` and `docker compose logs frontend`
- Review [GitHub OAuth docs](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps)
- Review [Google OAuth docs](https://developers.google.com/identity/protocols/oauth2)
- Open an issue on GitHub: https://github.com/ardhaecosystem/Ardha

---

**Version**: 1.0
**Last Updated**: November 30, 2025
**Maintained By**: Ardha Development Team
