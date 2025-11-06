# Code Mode: Use GLM 4.6 or Grok Code Fast 1

Default model for Code mode:
**Model**: `z-ai/glm-4.6`

Use Grok for simple tasks:
**Model**: `x-ai/grok-code-fast-1`

Task routing:
- Complex features → GLM 4.6 (`z-ai/glm-4.6`)
- Simple bugs → Grok (`x-ai/grok-code-fast-1`)
- Documentation → Gemini (`google/gemini-2.0-flash-001:free`)

Switch models based on task complexity.

## Correct Model Strings
- GLM 4.6: `z-ai/glm-4.6`
- Grok Code Fast 1: `x-ai/grok-code-fast-1`
- Claude Sonnet 4.5: `anthropic/claude-sonnet-4.5-20241022`
- Gemini Flash: `google/gemini-2.0-flash-001:free`
