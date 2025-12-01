# Chat Interface Integration Review

**Date:** 2025-01-07  
**Status:** ⚠️ Issues Found - Needs Fixes

## Executive Summary

The chat interface has several integration issues that prevent it from working properly with OpenCode:

1. ❌ **promptAsync Response Handling**: Incorrectly expecting data from 204 response
2. ⚠️ **Event Subscription Timing**: Race condition - events may arrive before subscription
3. ⚠️ **Event Subscription Lifecycle**: Only subscribes after first message
4. ✅ **Event Handling**: Correctly processes events once received
5. ✅ **Message Transformation**: Correctly transforms OpenCode format to UI format

---

## ❌ Critical Issues

### 1. promptAsync Response Handling
**Status:** ❌ **BROKEN**

**Problem:**
`promptAsync` returns HTTP 204 (No Content) - it doesn't return data. The code is trying to access `result.data` which doesn't exist.

**Current Code:**
```javascript
// mercury-coder/src/composables/useOpencode.js (line 88-101)
const result = await client.value.session.promptAsync({
  path: { id: sessionId.value },
  body: {
    parts: [{ type: 'text', text }],
    agent: options.agent || undefined,
    tools: options.tools || undefined,
    noReply: options.noReply || false
  }
})

console.log('[useOpencode] PromptAsync result:', result)
console.log('[useOpencode] Result data:', result.data)  // ❌ This will be undefined!

return result.data  // ❌ Returns undefined
```

**Evidence:**
- OpenCode server returns 204 for `/session/:id/prompt_async` (line 1027 in server.ts)
- SDK documentation shows `promptAsync` is fire-and-forget
- Official examples use `prompt()` for synchronous responses, not `promptAsync()`

**Fix:**
`promptAsync` should not return data. It's designed to return immediately and rely on events. The function should just return success/failure, not data.

---

### 2. Event Subscription Timing
**Status:** ⚠️ **RACE CONDITION**

**Problem:**
Events are subscribed AFTER sending the message, but events may start arriving immediately. This can cause messages to be missed.

**Current Code:**
```javascript
// mercury-coder/src/stores/chat.js (line 88-119)
async function sendMessage(text, options = {}) {
  // ... add user message ...
  
  // Send message through OpenCode
  await opencode.sendMessage(text, { ... })
  
  // ❌ Subscription happens AFTER message is sent
  if (!subscriptionStarted && opencode.sessionId.value) {
    events.subscribe(opencode.sessionId.value)
    subscriptionStarted = true
  }
}
```

**Issue:**
- If events arrive before subscription is set up, they're lost
- Should subscribe when session is created, not after first message
- Should subscribe to global events initially, then filter by session

**Fix:**
Subscribe to events when session is created, or subscribe to global events immediately.

---

### 3. Event Subscription Lifecycle
**Status:** ⚠️ **SUBOPTIMAL**

**Problem:**
Event subscription only starts after the first message is sent. This means:
- No events are received during session creation
- Events from the first message might be missed
- No way to receive events for existing sessions

**Current Code:**
```javascript
// Only subscribes after first message
if (!subscriptionStarted && opencode.sessionId.value) {
  events.subscribe(opencode.sessionId.value)
  subscriptionStarted = true
}
```

**Fix:**
- Subscribe to global events when chat store initializes
- Or subscribe when session is created
- Handle both global and session-specific events

---

## ✅ What's Working

### 1. Event Processing
**Status:** ✅ **CORRECT**

The event handling correctly:
- Processes `message.created` and `message.updated` events
- Handles `message.part.updated` for streaming content
- Transforms OpenCode message format to UI format
- Extracts text and tool parts correctly

### 2. Message Transformation
**Status:** ✅ **CORRECT**

The `transformMessage` function correctly:
- Extracts message info (id, role, timestamp)
- Extracts text content from parts
- Extracts tool calls
- Handles streaming state

### 3. UI Integration
**Status:** ✅ **CORRECT**

The ChatPanel component:
- Correctly uses the chat store
- Displays messages from the store
- Handles user input
- Shows loading states

---

## 🔧 Required Fixes

### Fix 1: Correct promptAsync Handling

**File:** `mercury-coder/src/composables/useOpencode.js`

```javascript
async function sendMessage(text, options = {}) {
  if (!sessionId.value) {
    await createSession()
  }

  try {
    loading.value = true
    error.value = null

    console.log('[useOpencode] Sending message to session:', sessionId.value)
    console.log('[useOpencode] Message text:', text)
    console.log('[useOpencode] Options:', options)

    // promptAsync returns 204 (no content) - it's fire-and-forget
    // Events will arrive via the event stream
    await client.value.session.promptAsync({
      path: { id: sessionId.value },
      body: {
        parts: [{ type: 'text', text }],
        agent: options.agent || undefined,
        tools: options.tools || undefined,
        noReply: options.noReply || false
      }
    })

    // promptAsync doesn't return data - success means request was accepted
    console.log('[useOpencode] Message sent successfully (events will arrive via stream)')
    return { success: true }
  } catch (err) {
    error.value = err.message
    console.error('[useOpencode] Send message error:', err)
    throw err
  } finally {
    loading.value = false
  }
}
```

### Fix 2: Subscribe to Events Early

**File:** `mercury-coder/src/stores/chat.js`

```javascript
export const useChatStore = defineStore('chat', () => {
  const opencode = useOpencode()
  const events = useOpencodeEvents()
  
  const messages = ref([])
  const loading = computed(() => opencode.loading.value)
  const error = computed(() => opencode.error.value)
  const sessionId = computed(() => opencode.sessionId.value)
  
  // Subscribe to global events immediately (or when session is created)
  watch(() => opencode.sessionId.value, (newSessionId) => {
    if (newSessionId) {
      console.log('[ChatStore] Session created, subscribing to events:', newSessionId)
      // Subscribe to session-specific events
      events.subscribe(newSessionId)
    }
  }, { immediate: true })
  
  // Also subscribe to global events to catch any missed events
  onMounted(() => {
    console.log('[ChatStore] Subscribing to global events')
    events.subscribe() // Global subscription
  })
  
  // ... rest of code
})
```

### Fix 3: Alternative - Use prompt() Instead

If you want synchronous responses, use `prompt()` instead of `promptAsync()`:

```javascript
// Alternative: Use prompt() for synchronous response
const result = await client.value.session.prompt({
  path: { id: sessionId.value },
  body: {
    parts: [{ type: 'text', text }],
    agent: options.agent || undefined,
    tools: options.tools || undefined,
    noReply: options.noReply || false
  }
})

// prompt() returns the message data
if (result.data) {
  return result.data
}
```

**Note:** `prompt()` waits for the response, while `promptAsync()` returns immediately and relies on events.

---

## 📋 Comparison with Official Implementation

### Official OpenCode Desktop Pattern

```typescript
// Official desktop uses prompt() for synchronous responses
sdk.client.session.prompt({
  path: { id: sessionID },
  body: {
    parts: [{ type: "text", text: inputText }],
    agent: local.agent.current().name,
    model: local.model.current(),
  },
})

// Events are subscribed globally and filtered by directory/session
globalSDK.event.on(props.directory, async (event) => {
  emitter.emit(event.type, event)
})
```

### Our Current Pattern

```javascript
// We use promptAsync (fire-and-forget)
await client.value.session.promptAsync({ ... })

// Events subscribed after message sent (race condition)
if (!subscriptionStarted && opencode.sessionId.value) {
  events.subscribe(opencode.sessionId.value)
}
```

---

## 🎯 Recommended Approach

### Option 1: Use prompt() (Simpler)
- Synchronous response
- No event subscription needed for basic chat
- Easier to debug
- Matches official examples

### Option 2: Use promptAsync() + Events (More Advanced)
- Asynchronous, real-time updates
- Better for streaming
- Requires proper event subscription setup
- More complex but more powerful

**Recommendation:** Start with Option 1 (`prompt()`), then add event streaming later if needed.

---

## ✅ Conclusion

The chat interface has **3 critical issues** that need to be fixed:

1. ❌ **promptAsync response handling** - Returns undefined
2. ⚠️ **Event subscription timing** - Race condition
3. ⚠️ **Event subscription lifecycle** - Subscribes too late

**Recommended Fix:**
- Use `prompt()` instead of `promptAsync()` for simpler, more reliable chat
- Or fix `promptAsync()` handling and subscribe to events early

**Status:** ❌ **NOT WORKING** (needs fixes)

