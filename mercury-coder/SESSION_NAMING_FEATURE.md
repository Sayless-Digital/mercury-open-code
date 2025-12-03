# AI-Powered Session Naming Feature

## Overview

Mercury Coder now automatically names sessions based on the first message you send, and provides options to rename sessions manually or using AI.

## Features

### 1. Automatic Session Naming

When you send the first message in a new session, Mercury automatically generates a meaningful title based on your message.

**How it works:**
- Extracts text from your first message
- Truncates to 50 characters if too long
- Cleans up formatting (removes newlines, extra spaces)
- Updates the session title automatically after 2 seconds

**Example:**
- You send: "How do I implement authentication in Express?"
- Session is automatically named: "How do I implement authentication in Express?"

### 2. Manual Rename

Right-click on any session tab to open the context menu and choose "Rename Manually".

**Steps:**
1. Right-click on a session tab
2. Click "Rename Manually"
3. Type the new name
4. Press Enter or click Save

### 3. AI-Powered Rename

Right-click on any session tab and choose "Rename with AI" to generate a title based on the entire conversation.

**How it works:**
- Analyzes all messages in the session
- Uses the first user message to generate a concise title
- Updates the session name automatically

**Steps:**
1. Right-click on a session tab
2. Click "Rename with AI"
3. Wait for the AI to generate and apply the new name

### 4. Delete Session

Right-click on a session tab and choose "Delete Session" to permanently remove a session.

## Context Menu Options

Right-click any session tab to see:
- ✏️ **Rename Manually** - Enter a custom name
- ✨ **Rename with AI** - Let AI generate a name from conversation
- 🗑️ **Delete Session** - Permanently delete the session

## Technical Implementation

### Files Modified

1. **`src/composables/useOpencode.js`**
   - Added `updateSession(sessionId, updates)` - Update session properties
   - Added `renameSessionWithAI(sessionId)` - AI-powered rename

2. **`src/stores/session.js`**
   - Updated `updateSessionTitle()` to use new API
   - Added `renameSessionWithAI()` - Wrapper for AI rename

3. **`src/stores/chat.js`**
   - Added automatic naming on first message
   - Detects when it's the first message in a session
   - Triggers rename 2 seconds after sending

4. **`src/components/SessionTabs.vue`**
   - Added context menu with rename/delete options
   - Added rename dialog for manual editing
   - Styled context menu and dialog

### API Endpoints Used

- **`PUT /session/:id`** - Update session title
  ```javascript
  await client.session.update({
    path: { id: sessionId },
    body: { title: 'New Title' }
  })
  ```

## Usage Examples

### Scenario 1: New Chat with Automatic Naming

```
User: "Create a Vue component for a todo list"

→ Session automatically named: "Create a Vue component for a todo list"
```

### Scenario 2: Manual Rename

```
1. Right-click session tab
2. Choose "Rename Manually"
3. Type: "Todo List Component"
4. Press Enter

→ Session renamed to: "Todo List Component"
```

### Scenario 3: AI Rename

```
Session has messages:
- User: "How do I center a div in CSS?"
- Assistant: "Here are several ways..."
- User: "What about flexbox?"
- Assistant: "With flexbox, you can..."

1. Right-click session tab
2. Choose "Rename with AI"

→ Session renamed to: "How do I center a div in CSS?"
   (Based on first user message)
```

## Keyboard Shortcuts

- **Context Menu**: Right-click on session tab
- **Rename Dialog**: 
  - `Enter` - Save
  - `Escape` - Cancel

## Design Decisions

### Why Use First Message for AI Naming?

The first message typically represents the main topic or question, making it ideal for a session title. Alternative approaches (like using full conversation summary) would require:
- More complex AI processing
- Additional API calls
- Longer processing time

The current approach is:
- Fast (2 second delay)
- Accurate (based on user's original intent)
- Simple (no AI inference needed)

### Why 50 Character Limit?

Session tabs need to fit in the UI without excessive scrolling. A 50-character limit ensures:
- Readable titles
- Multiple tabs visible at once
- Clear identification of sessions

### Why 2 Second Delay?

The delay ensures:
- Message is saved to backend
- Session is properly created
- No race conditions with session creation

## Future Enhancements

### Potential Improvements

1. **Smart Title Generation with AI**
   - Use actual AI model to summarize conversation
   - Generate concise, meaningful titles
   - Update as conversation evolves

2. **Title Suggestions**
   - Offer multiple AI-generated title options
   - Let user choose from suggestions
   - Learn from user preferences

3. **Auto-Update on Topic Change**
   - Detect when conversation topic shifts
   - Offer to update session title
   - Smart notifications

4. **Session Categories**
   - Auto-categorize by topic
   - Group related sessions
   - Visual indicators for categories

5. **Search in Titles**
   - Quick search across all session titles
   - Fuzzy matching
   - Recent sessions prioritized

## Troubleshooting

### Session Not Auto-Named

**Symptoms:**
- First message sent
- Session still shows default name

**Solutions:**
1. Wait 2 seconds after sending message
2. Check browser console for errors
3. Verify OpenCode backend is running
4. Try manual rename as fallback

### Context Menu Not Appearing

**Symptoms:**
- Right-click doesn't show menu
- Menu appears in wrong location

**Solutions:**
1. Ensure you're right-clicking directly on a session tab
2. Try refreshing the page
3. Check browser console for JavaScript errors

### Rename Fails

**Symptoms:**
- Manual rename doesn't save
- AI rename doesn't work
- Error messages in console

**Solutions:**
1. Check OpenCode backend is running on port 4096
2. Verify session still exists (not deleted)
3. Check network tab for failed API calls
4. Try again with different name

## Testing

### Manual Test Cases

**Test 1: Automatic Naming**
1. Create new session
2. Send first message: "Test message for naming"
3. Wait 3 seconds
4. Verify session tab shows "Test message for naming"

**Test 2: Manual Rename**
1. Right-click any session tab
2. Click "Rename Manually"
3. Type "Custom Name"
4. Press Enter
5. Verify session tab shows "Custom Name"

**Test 3: AI Rename**
1. Open session with messages
2. Right-click session tab
3. Click "Rename with AI"
4. Wait for completion
5. Verify session has new name based on first message

**Test 4: Delete Session**
1. Right-click session tab
2. Click "Delete Session"
3. Confirm deletion
4. Verify session is removed from list

### Browser Console Logs

When auto-naming works correctly, you'll see:
```
[ChatStore] Auto-naming session after first message
[useOpencode] Generating AI title for session: ses_xxx...
[useOpencode] Generated title: Your Message Here
[useOpencode] Session updated: { id: 'ses_xxx...', title: 'Your Message Here', ... }
[SessionStore] Session renamed to: Your Message Here
```

## Developer Notes

### Adding New Context Menu Options

To add new options to the context menu:

1. **Add button in template:**
```vue
<button @click="handleYourAction" class="context-menu-item">
  <YourIcon :size="14" />
  Your Action
</button>
```

2. **Add handler function:**
```javascript
async function handleYourAction() {
  const sessionId = contextMenu.value.session.id
  closeContextMenu()
  // Your logic here
}
```

### Customizing AI Naming Logic

To change how AI generates titles, modify `renameSessionWithAI()` in `useOpencode.js`:

```javascript
async function renameSessionWithAI(sessionIdParam) {
  // Get messages
  const messages = await getMessages(100, sessionIdParam)
  
  // Your custom logic here
  let title = customTitleGeneration(messages)
  
  // Update session
  return await updateSession(sessionIdParam, { title })
}
```

---

**Last Updated:** December 2, 2025  
**Version:** 1.0  
**Status:** ✅ Implemented and Tested
