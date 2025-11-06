# Multi-Model Routing Strategy for Ardha

## Model Selection Decision Tree

### Use Claude Sonnet 4.5 (45% budget - $27/month)
**When to use:**
- OpenSpec operations: `/openspec:proposal`, `/openspec:apply`, `/openspec:archive`
- Architecture decisions and system design
- Memory bank initialization and updates
- Complex refactoring across multiple files
- Security reviews and vulnerability analysis
- Code reviews requiring deep context understanding
- API contract design and OpenAPI spec generation

**Model**: `anthropic/claude-sonnet-4.5`
**Cost**: $3 input / $15 output per 1M tokens
**Caching**: ✅ Enabled (90% discount on cached reads)
**Capacity**: ~1.8M output tokens/month

**Commands that trigger Claude Sonnet 4.5:**
```
initialize memory bank
update memory bank
create OpenSpec proposal
review this architecture
design API contract
security review
```

---

### Use GLM 4.6 (35% budget - $21/month)
**When to use:**
- Feature implementation (new endpoints, services, components)
- Bug fixes (non-critical, well-defined)
- Code refactoring (single file or module)
- Database query optimization
- Adding business logic
- Creating repository/service layer code
- Frontend component development
- State management implementation

**Model**: `z-ai/glm-4.6`
**Cost**: ~$0.50 input / $1.50 output per 1M tokens (estimated)
**Caching**: Check if supported
**Capacity**: ~14M output tokens/month

**Commands that trigger GLM 4.6:**
```
implement this feature
add new endpoint
create component
refactor this function
fix this bug
optimize this query
add service method
```

---

### Use Grok Code Fast 1 (15% budget - $9/month)
**When to use:**
- Quick bug fixes (typos, simple logic errors)
- Adding type hints
- Code formatting and linting fixes
- Simple utility functions
- Configuration file updates
- Package.json / pyproject.toml updates
- Basic CRUD operations
- Simple test scaffolding

**Model**: `x-ai/grok-code-fast-1`
**Cost**: ~$0.30 input / $0.90 output per 1M tokens (estimated)
**Caching**: Check if supported
**Capacity**: ~10M output tokens/month

**Commands that trigger Grok:**
```
fix this typo
add type hints
format this code
create simple utility
update config
add basic CRUD
simple test
```

---

### Use Gemini 2.0 Flash (5% budget - $3/month)
**When to use:**
- Documentation generation (README, API docs, docstrings)
- Comment generation for complex code
- Test case generation (unit tests)
- Migration script documentation
- Changelog generation
- Error message improvements
- Code example generation
- Tutorial writing

**Model**: `google/gemini-2.0-flash-001:free` (prefer free tier)
**Cost**: $0.075 input / $0.30 output per 1M tokens (or FREE)
**Caching**: ✅ Enabled
**Capacity**: ~10M output tokens/month (or unlimited if free)

**Commands that trigger Gemini:**
```
document this function
add docstrings
generate tests
write README
create changelog
add comments
explain this code
write tutorial
```

---

## Model Selection Guidelines

### Default Fallback
If uncertain which model to use: **Start with GLM 4.6** (mid-tier)

**Correct model string**: `z-ai/glm-4.6`

### When to Override
You can explicitly request a model:
```
[Use Claude Sonnet] Design the authentication architecture
[Use GLM] Implement the login endpoint
[Use Grok] Fix the import statement
[Use Gemini] Document the API endpoints
```

### Cost Monitoring
Track model usage weekly:
- Claude Sonnet: Should stay ~45% of spend
- GLM 4.6: Should stay ~35% of spend
- Grok: Should stay ~15% of spend
- Gemini: Should stay ~5% of spend

If any category exceeds budget, switch to cheaper models.

---

## Prompt Caching Strategy by Model

### Claude Sonnet 4.5 (Primary Caching)
- Cache structure: 4 breakpoints
- Cache memory bank + project context (5K tokens)
- Cache conversation history (15K tokens)
- Target cache hit rate: >70%

### GLM 4.6 / Grok / Gemini
- Use caching if supported
- If not supported, keep sessions short
- Minimize context to essential files only

---

## Session Discipline by Model

### Claude Sonnet (Expensive)
- Limit to 30-minute sessions
- Stop after 3 failed attempts
- Max 50K tokens per session
- Use only for high-value tasks

### GLM 4.6 (Mid-tier)
- Limit to 1-hour sessions
- Stop after 5 failed attempts
- Max 100K tokens per session
- Primary workhorse for implementation

### Grok (Budget)
- Can use more freely
- Quick tasks only (<15 min)
- Max 30K tokens per session
- For simple, well-defined tasks

### Gemini (Free/Cheap)
- Use liberally for documentation
- Generate comprehensive docs
- Batch multiple doc tasks together

---

## Quality vs Cost Trade-offs

### When Quality Matters More (Use Claude Sonnet)
- Security-critical code
- Complex business logic
- Multi-file refactoring
- Architecture decisions

### When Speed Matters More (Use Grok)
- Hot fixes in production
- Quick bug fixes
- Simple updates

### When Budget Matters Most (Use Gemini)
- Documentation (can regenerate if wrong)
- Test generation (can verify manually)
- Comments and explanations

---

## Emergency Budget Mode

If approaching $60/month limit (>90% spent):
1. **Stop using Claude Sonnet** (except critical OpenSpec)
2. **Switch to Grok for all coding**
3. **Use Gemini for everything else**
4. **Manual coding** for complex tasks
5. **Wait for next month** before resuming normal usage

---

## Correct Model Strings Reference

**Copy-paste ready:**
```
anthropic/claude-sonnet-4.5             ← Claude Sonnet 4.5
z-ai/glm-4.6                            ← GLM 4.6
x-ai/grok-code-fast-1                   ← Grok Code Fast 1
google/gemini-2.0-flash-001:free        ← Gemini Flash (free tier)
```
