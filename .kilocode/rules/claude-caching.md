# Claude Sonnet 4.5 Prompt Caching

## When Using Claude Sonnet 4.5

### Cache Structure (4 Breakpoints)
1. **Tool definitions** (rarely change)
2. **Memory Bank** (5K tokens) - brief.md, product.md, context.md, etc.
3. **Project Context** (30K tokens) - relevant files, patterns
4. **Conversation** (15K tokens) - previous messages

### Session Strategy
- Keep sessions focused on related tasks
- Complete OpenSpec proposals within 5-minute cache window
- Group architecture decisions together
- Update memory bank at end of session

### Expected Savings
- First request: $0.19 (cache write)
- Subsequent: $0.02 each (cache read)
- **78-90% cost reduction!**
