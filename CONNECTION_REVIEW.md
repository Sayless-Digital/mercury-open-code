# Connection Review: Mercury Coder ↔ OpenCode Backend

**Date:** 2025-01-07  
**Status:** ⚠️ Mostly Connected with Minor Issues

## Executive Summary

The integration between `mercury-coder` and `opencode-backend` is **mostly correct** according to the OpenCode documentation, but there are a few issues that need to be addressed:

1. ✅ **SDK Linking**: Correctly configured
2. ✅ **Backend Startup**: Properly implemented
3. ✅ **API Endpoints**: Correctly configured
4. ⚠️ **Health Check**: Using wrong endpoint
5. ✅ **SDK Usage**: Correctly implemented

---

## ✅ What's Working Well

### 1. SDK Package Linking
**Status:** ✅ **CORRECT**

- **File:** `mercury-coder/package.json`
- **Configuration:**
  ```json
  "@opencode-ai/sdk": "file:../opencode-backend/packages/sdk/js"
  ```
- **Verification:** The local SDK is properly linked from the opencode-backend directory

### 2. Backend Startup in Electron
**Status:** ✅ **CORRECT**

- **File:** `mercury-coder/electron/main.js` (lines 754-829)
- **Implementation:**
  - Correctly resolves path to `../../opencode-backend`
  - Uses bun to run the OpenCode backend
  - Starts on port 4096 with correct hostname (127.0.0.1)
  - Includes `--print-logs` flag
  - Waits for backend to be ready before proceeding

### 3. Startup Scripts
**Status:** ✅ **CORRECT**

Both `start.sh` and `start.py`:
- Check for bun installation
- Navigate to opencode-backend directory
- Install dependencies if needed
- Start OpenCode backend correctly
- Wait for backend readiness
- Start Vite frontend
- Launch Electron app

### 4. SDK Import and Usage
**Status:** ✅ **CORRECT**

- **File:** `mercury-coder/src/composables/useOpencode.js`
- **Import:** `import { createOpencodeClient } from '@opencode-ai/sdk/client'`
- **Usage:**
  - Correctly uses `createOpencodeClient` with baseUrl
  - Sets directory from project store
  - Uses proper API methods (`session.create`, `session.promptAsync`, etc.)

### 5. API Configuration
**Status:** ✅ **CORRECT**

- **Base URL:** `http://127.0.0.1:4096` (consistent across all files)
- **Port:** 4096 (matches OpenCode default)
- **Hostname:** 127.0.0.1 (correct for local development)

---

## ⚠️ Issues Found

### 1. Health Check Endpoint Mismatch
**Status:** ⚠️ **ISSUE FOUND**

**Problem:**
- `start.sh` (line 182) checks: `http://127.0.0.1:4096/health`
- `start.py` (line 262) checks: `http://127.0.0.1:4096/health`
- `electron/main.js` (line 729) checks: `http://127.0.0.1:4096/config`

**Root Cause:**
The OpenCode backend does **NOT** have a `/health` endpoint. The available endpoint is `/config` (GET).

**Evidence:**
- Searched `opencode-backend/packages/opencode` for `/health` - **no results**
- Found `/config` endpoint in `opencode-backend/packages/opencode/src/server/server.ts` (line 198)

**Impact:**
- Startup scripts may fail to detect when backend is ready
- Could cause false negatives during health checks
- Electron's check using `/config` is correct

**Recommendation:**
Update `start.sh` and `start.py` to use `/config` instead of `/health`:

```bash
# In start.sh (line 182)
if curl -s http://127.0.0.1:4096/config > /dev/null 2>&1; then

# In start.py (line 262)
req = urllib.request.Request('http://127.0.0.1:4096/config')
```

---

## 📋 Detailed Component Review

### Package Dependencies

| Component | Status | Details |
|-----------|--------|---------|
| SDK Link | ✅ | `file:../opencode-backend/packages/sdk/js` |
| SDK Package Name | ✅ | `@opencode-ai/sdk` |
| SDK Export Path | ✅ | `@opencode-ai/sdk/client` |

### Backend Startup

| Component | Status | Details |
|-----------|--------|---------|
| Path Resolution | ✅ | `../../opencode-backend` from electron/ |
| Command | ✅ | `bun run --cwd packages/opencode --conditions=browser src/index.ts serve` |
| Port | ✅ | 4096 |
| Hostname | ✅ | 127.0.0.1 |
| Logging | ✅ | `--print-logs` flag included |
| Health Check | ⚠️ | Using `/health` (should be `/config`) |

### API Usage

| Component | Status | Details |
|-----------|--------|---------|
| Base URL | ✅ | `http://127.0.0.1:4096` |
| Client Creation | ✅ | `createOpencodeClient({ baseUrl, directory })` |
| Session Management | ✅ | Uses `client.session.*` methods |
| Event Streaming | ✅ | Uses `client.global.event()` for SSE |

### Frontend Integration

| Component | Status | Details |
|-----------|--------|---------|
| Composable | ✅ | `useOpencode.js` correctly implemented |
| Events Composable | ✅ | `useOpencodeEvents.js` correctly implemented |
| Providers Composable | ✅ | `useOpencodeProviders.js` exists |
| Vite Config | ✅ | SDK included in optimizeDeps |

---

## 🔍 Verification Checklist

- [x] SDK is linked from local opencode-backend
- [x] Backend starts from correct path
- [x] Port configuration is consistent (4096)
- [x] SDK imports are correct
- [x] API methods are used correctly
- [x] Base URL is consistent
- [ ] Health check endpoint is correct ⚠️
- [x] Startup scripts handle dependencies
- [x] Electron process management is correct

---

## 🛠️ Recommended Fixes

### Priority 1: Fix Health Check Endpoint

**Files to Update:**
1. `mercury-coder/start.sh` (line 182)
2. `mercury-coder/start.py` (line 262)

**Change:**
```diff
- if curl -s http://127.0.0.1:4096/health > /dev/null 2>&1; then
+ if curl -s http://127.0.0.1:4096/config > /dev/null 2>&1; then
```

**For Python:**
```diff
- req = urllib.request.Request('http://127.0.0.1:4096/health')
+ req = urllib.request.Request('http://127.0.0.1:4096/config')
```

---

## 📚 References

- **OpenCode Documentation:** `opencode-backend/README.md`
- **Integration Notes:** `INTEGRATION_NOTES.md`
- **Main README:** `README.md`
- **SDK Package:** `opencode-backend/packages/sdk/js/package.json`
- **Server Routes:** `opencode-backend/packages/opencode/src/server/server.ts`

---

## ✅ Conclusion

The connection between `mercury-coder` and `opencode-backend` is **well-implemented** and follows the OpenCode documentation correctly. The only issue is the health check endpoint mismatch, which is a minor bug that should be fixed for proper startup detection.

**Overall Status:** ✅ **GOOD** (with one minor fix needed)

**Next Steps:**
1. Fix health check endpoint in startup scripts
2. Test startup flow end-to-end
3. Verify all API endpoints are accessible
4. Test session creation and message sending



