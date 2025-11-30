# OAuth Testing Guide

Quick guide for testing GitHub and Google OAuth integration in Ardha.

## Before You Start

### 1. Set Up OAuth Apps

**GitHub OAuth App:**
- URL: https://github.com/settings/developers
- Callback: `http://82.29.164.29:3000/auth/callback/github`
- Get: Client ID + Secret

**Google OAuth 2.0:**
- URL: https://console.cloud.google.com/apis/credentials
- Callback: `http://82.29.164.29:3000/auth/callback/google`
- Enable: Google+ API, People API
- Get: Client ID + Secret

### 2. Configure Environment

**Backend** (`backend/.env`):
```bash
OAUTH__GITHUB_CLIENT_ID=your_github_client_id
OAUTH__GITHUB_CLIENT_SECRET=your_github_client_secret
OAUTH__GOOGLE_CLIENT_ID=your_google_client_id
OAUTH__GOOGLE_CLIENT_SECRET=your_google_client_secret
```

**Frontend** (`frontend/.env.local`):
```bash
NEXT_PUBLIC_GITHUB_CLIENT_ID=your_github_client_id
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_google_client_id
NEXT_PUBLIC_API_URL=http://82.29.164.29:8000
NEXT_PUBLIC_APP_URL=http://82.29.164.29:3000
```

### 3. Restart Services

```bash
cd ~/ardha-projects/Ardha
docker compose build backend frontend
docker compose up -d
docker compose logs -f
```

---

## Test 1: GitHub OAuth (New User)

### Expected Flow
1. Visit http://82.29.164.29:3000/login
2. Click **"Log in with GitHub"**
3. Browser redirects to GitHub authorization page
4. Click **"Authorize Ardha"** on GitHub
5. Redirects to `/auth/callback/github?code=...&state=...`
6. Shows "Authenticating with GitHub..." spinner
7. Redirects to `/dashboard`
8. **✅ You are logged in!**

### Verify in Database
```bash
docker compose exec postgres psql -U ardha -d ardha
SELECT id, email, username, github_id, avatar_url FROM users WHERE github_id IS NOT NULL;
\q
```

**Expected**: 1 row with GitHub ID populated

---

## Test 2: Google OAuth (New User)

### Expected Flow
1. Visit http://82.29.164.29:3000/login
2. Click **"Log in with Google"**
3. Browser redirects to Google account selection
4. Select your Google account
5. Click **"Continue"** to authorize
6. Redirects to `/auth/callback/google?code=...&state=...`
7. Shows "Authenticating with Google..." spinner
8. Redirects to `/dashboard`
9. **✅ You are logged in!**

### Verify in Database
```bash
docker compose exec postgres psql -U ardha -d ardha
SELECT id, email, username, google_id, avatar_url FROM users WHERE google_id IS NOT NULL;
\q
```

**Expected**: 1 row with Google ID populated

---

## Test 3: Account Linking

This tests linking OAuth to existing email/password accounts.

### Setup
1. Create email/password account:
   - Visit http://82.29.164.29:3000/register
   - Email: `test@example.com`
   - Username: `testuser`
   - Password: `TestPass123!`
   - Full name: `Test User`
   - ✅ Register

2. Logout (top-right menu)

### Test GitHub Linking
1. Make sure your **GitHub public email** is `test@example.com`
   - Go to https://github.com/settings/emails
   - Set primary email to public

2. Visit http://82.29.164.29:3000/login
3. Click **"Log in with GitHub"**
4. Authorize Ardha
5. **✅ Should login to existing account!**

### Verify Linking
```bash
docker compose exec postgres psql -U ardha -d ardha
SELECT email, username, password_hash IS NOT NULL as has_password, github_id IS NOT NULL as has_github
FROM users WHERE email = 'test@example.com';
\q
```

**Expected**: `has_password: true`, `has_github: true` (account has both!)

### Test Dual Login
Now the user can login with EITHER:
- **Email + Password**: `test@example.com` / `TestPass123!`
- **GitHub OAuth**: Click "Login with GitHub"

Both should work! ✅

---

## Test 4: Error Handling

### Test 1: User Denies Authorization

1. Visit http://82.29.164.29:3000/login
2. Click **"Log in with GitHub"**
3. On GitHub page, click **"Cancel"** or **"Deny"**
4. **Expected**: Callback page shows error:
   ```
   ❌ Authentication Failed
   GitHub authorization failed: You denied access
   [Back to Login] button
   ```

### Test 2: Invalid State (CSRF Attack Simulation)

This should NOT be possible in normal usage, but verifies security:

1. Visit http://82.29.164.29:3000/login
2. Click **"Log in with GitHub"**
3. On GitHub authorization page, copy the URL
4. **Before authorizing**, edit URL to change state parameter
5. **Expected**: Callback shows error:
   ```
   ❌ Authentication Failed
   Invalid state parameter - possible CSRF attack
   ```

### Test 3: Missing Email (GitHub Only)

1. Make all GitHub emails private:
   - Go to https://github.com/settings/emails
   - Uncheck "Keep my email addresses private"
   - Make all emails "Private"

2. Try GitHub OAuth login
3. **Expected**: Backend returns error:
   ```
   GitHub account must have a public email address
   ```

**Fix**: Make at least one email public, or backend can fetch private emails (current implementation already does this).

---

## Test 5: Concurrent OAuth Providers

### Setup
User with email `multi@example.com`

### Test Flow
1. Register with email/password: `multi@example.com`
2. Logout
3. Login with GitHub (email: `multi@example.com`)
   - **✅ Links GitHub to account**
4. Logout
5. Login with Google (email: `multi@example.com`)
   - **✅ Links Google to account**

### Verify Multi-OAuth
```bash
docker compose exec postgres psql -U ardha -d ardha
SELECT
  email,
  password_hash IS NOT NULL as has_password,
  github_id IS NOT NULL as has_github,
  google_id IS NOT NULL as has_google
FROM users
WHERE email = 'multi@example.com';
\q
```

**Expected**: `has_password: true`, `has_github: true`, `has_google: true`

User can now login with 3 methods! ✅

---

## Test 6: API Endpoint Direct Testing

### Test GitHub OAuth Endpoint

```bash
# 1. Get authorization code manually from GitHub
# Visit: https://github.com/login/oauth/authorize?client_id=YOUR_CLIENT_ID&scope=read:user%20user:email

# 2. After authorizing, copy code from callback URL

# 3. Test backend endpoint
curl -X POST http://82.29.164.29:8000/api/v1/auth/oauth/github \
  -H "Content-Type: application/json" \
  -d '{
    "code": "paste_github_authorization_code_here"
  }'
```

**Expected Response (200 OK)**:
```json
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

### Test Google OAuth Endpoint

Similar process with Google authorization code:
```bash
curl -X POST http://82.29.164.29:8000/api/v1/auth/oauth/google \
  -H "Content-Type: application/json" \
  -d '{
    "code": "paste_google_authorization_code_here"
  }'
```

---

## Automated Testing Script

Save as `test-oauth.sh`:

```bash
#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

API_URL="http://82.29.164.29:8000"
FRONTEND_URL="http://82.29.164.29:3000"

echo -e "${YELLOW}=== Ardha OAuth Integration Tests ===${NC}\n"

# Test 1: Backend health
echo -e "${YELLOW}Test 1: Backend Health Check${NC}"
response=$(curl -s -o /dev/null -w "%{http_code}" $API_URL/health)
if [ $response -eq 200 ]; then
    echo -e "${GREEN}✅ Backend is healthy${NC}\n"
else
    echo -e "${RED}❌ Backend is not responding (HTTP $response)${NC}\n"
    exit 1
fi

# Test 2: OAuth configuration check
echo -e "${YELLOW}Test 2: OAuth Configuration${NC}"
if docker compose exec -T backend printenv | grep -q "OAUTH__GITHUB_CLIENT_ID"; then
    echo -e "${GREEN}✅ GitHub OAuth configured${NC}"
else
    echo -e "${RED}❌ GitHub OAuth not configured in backend${NC}"
fi

if docker compose exec -T backend printenv | grep -q "OAUTH__GOOGLE_CLIENT_ID"; then
    echo -e "${GREEN}✅ Google OAuth configured${NC}\n"
else
    echo -e "${RED}❌ Google OAuth not configured in backend${NC}\n"
fi

# Test 3: Frontend OAuth client IDs
echo -e "${YELLOW}Test 3: Frontend OAuth Configuration${NC}"
if [ -f frontend/.env.local ]; then
    if grep -q "NEXT_PUBLIC_GITHUB_CLIENT_ID" frontend/.env.local; then
        echo -e "${GREEN}✅ GitHub client ID in frontend${NC}"
    else
        echo -e "${RED}❌ Missing NEXT_PUBLIC_GITHUB_CLIENT_ID in frontend/.env.local${NC}"
    fi

    if grep -q "NEXT_PUBLIC_GOOGLE_CLIENT_ID" frontend/.env.local; then
        echo -e "${GREEN}✅ Google client ID in frontend${NC}\n"
    else
        echo -e "${RED}❌ Missing NEXT_PUBLIC_GOOGLE_CLIENT_ID in frontend/.env.local${NC}\n"
    fi
else
    echo -e "${RED}❌ frontend/.env.local not found${NC}\n"
fi

# Test 4: OAuth routes accessible
echo -e "${YELLOW}Test 4: OAuth Routes${NC}"
github_response=$(curl -s -o /dev/null -w "%{http_code}" -X POST $API_URL/api/v1/auth/oauth/github -H "Content-Type: application/json" -d '{"code":"test"}')
if [ $github_response -eq 400 ] || [ $github_response -eq 500 ]; then
    echo -e "${GREEN}✅ GitHub OAuth endpoint exists (returned $github_response for invalid code)${NC}"
else
    echo -e "${RED}❌ GitHub OAuth endpoint issue (HTTP $github_response)${NC}"
fi

google_response=$(curl -s -o /dev/null -w "%{http_code}" -X POST $API_URL/api/v1/auth/oauth/google -H "Content-Type: application/json" -d '{"code":"test"}')
if [ $google_response -eq 400 ] || [ $google_response -eq 500 ]; then
    echo -e "${GREEN}✅ Google OAuth endpoint exists (returned $google_response for invalid code)${NC}\n"
else
    echo -e "${RED}❌ Google OAuth endpoint issue (HTTP $google_response)${NC}\n"
fi

# Test 5: Frontend pages exist
echo -e "${YELLOW}Test 5: Frontend OAuth Pages${NC}"
login_response=$(curl -s -o /dev/null -w "%{http_code}" $FRONTEND_URL/login)
if [ $login_response -eq 200 ]; then
    echo -e "${GREEN}✅ Login page accessible${NC}"
else
    echo -e "${RED}❌ Login page not accessible (HTTP $login_response)${NC}"
fi

github_callback_response=$(curl -s -o /dev/null -w "%{http_code}" $FRONTEND_URL/auth/callback/github)
if [ $github_callback_response -eq 200 ]; then
    echo -e "${GREEN}✅ GitHub callback page exists${NC}"
else
    echo -e "${RED}❌ GitHub callback page missing (HTTP $github_callback_response)${NC}"
fi

google_callback_response=$(curl -s -o /dev/null -w "%{http_code}" $FRONTEND_URL/auth/callback/google)
if [ $google_callback_response -eq 200 ]; then
    echo -e "${GREEN}✅ Google callback page exists${NC}\n"
else
    echo -e "${RED}❌ Google callback page missing (HTTP $google_callback_response)${NC}\n"
fi

echo -e "${YELLOW}=== Test Summary ===${NC}"
echo -e "All automated tests complete!"
echo -e "\n${YELLOW}Next Steps:${NC}"
echo -e "1. Set up OAuth apps (see docs/oauth-setup.md)"
echo -e "2. Add credentials to .env files"
echo -e "3. Restart services: docker compose restart backend frontend"
echo -e "4. Test manually:"
echo -e "   - Visit $FRONTEND_URL/login"
echo -e "   - Click 'Log in with GitHub'"
echo -e "   - Click 'Log in with Google'"
