# Memory System

Memory system for the coding agent with vector embeddings support.

## Features

- **Conversation Storage**: All chat messages are saved
- **Memory Extraction**: Important information is automatically extracted
- **Vector Search**: Semantic search using Chroma and sentence-transformers
- **Keyword Search**: Fallback text matching
- **Hybrid Search**: Combines both for best results

## Setup

### Dependencies

```bash
pip install chromadb sentence-transformers transformers
```

### Troubleshooting

If you get import errors:

1. **Transformers version conflict**:
   ```bash
   pip install --upgrade transformers
   pip install --force-reinstall sentence-transformers
   ```

2. **Check if vector store is enabled**:
   ```python
   from memory import MemoryManager
   manager = MemoryManager()
   print(manager.vector_store.is_enabled())
   ```

3. **Fallback**: The system will automatically use keyword search if vector search isn't available.

## Usage

```python
from memory import MemoryManager

manager = MemoryManager()

# Save conversation
manager.save_conversation(
    project_path="/path/to/project",
    session_id="session_123",
    user_message="I prefer TypeScript",
    assistant_response="Got it!"
)

# Retrieve context
context = manager.get_context_for_query(
    query="use TypeScript",
    project_path="/path/to/project"
)
```

## Database Files

- `backend/memory.db` - SQLite database (conversations, memories, task summaries)
- `backend/vector_db/` - Chroma vector database (embeddings)

## Configuration

Set environment variable to change embedding model:
```bash
export EMBEDDING_MODEL=all-mpnet-base-v2  # Better quality, slower
# or
export EMBEDDING_MODEL=all-MiniLM-L6-v2   # Faster (default)
```







