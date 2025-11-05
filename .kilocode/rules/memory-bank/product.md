# Ardha Product Vision

## Why This Project Exists

### The Core Problem
Modern software development is broken into silos:
- **Planning Tools** (Linear, Jira, Notion): Great for project management, but can't execute code
- **AI Coding Tools** (Cursor, Cline, Replit): Great at writing code, but lack project context
- **Result**: Teams waste 58% of their time switching between tools, copying context, and manually syncing state

### The Opportunity
AI coding assistants are revolutionary, but they operate in isolation. They don't understand:
- Why a feature exists (PRD context)
- How it fits into the project (architecture context)
- What else needs to change (dependency context)
- What was tried before (historical context)

## What Ardha Solves

### Unified AI Workflow
Ardha eliminates the artificial boundary between planning and execution:

**Traditional Workflow (Fragmented):**
```
Linear/Jira → Manual PRD → Cursor/Cline → Manual Task Updates → GitHub → Back to Linear
     ↓              ↓             ↓                 ↓                ↓            ↓
  Context       Context       Context          Context         Context      Context
   Lost          Lost          Lost             Lost            Lost         Lost
```

**Ardha Workflow (Unified):**
```
Idea → AI Research → PRD → AI Tasks → AI Implementation → Auto PR → Archive
  └─────────────────── Full Context Preserved ──────────────────────┘
```

### Why It's Revolutionary

1. **Project-Based Memory**: AI remembers every conversation, decision, and code change for the project
2. **OpenSpec Integration**: Specifications drive development, not vibes
3. **Continuous Learning**: AI gets better with each project (ACE framework)
4. **Cost Efficiency**: Prompt caching and smart routing reduce costs by 78-90%
5. **Transparent AI**: Always shows what AI is doing and why

## How It Should Work

### User Journey: From Idea to Production

**Step 1: Idea Exploration (Research Mode)**
```
User: "I want to build a real-time collaborative markdown editor"

AI (Research Mode):
- Conducts market research
- Analyzes competitors (Notion, Google Docs, HackMD)
- Assesses technical feasibility
- Suggests tech stack
- Outputs: Research summary, opportunity brief
```

**Step 2: Requirements Definition (Architect Mode)**
```
AI (Architect Mode):
- Generates Product Requirements Document (PRD)
- Generates Architecture Requirements Document (ARD)
- Defines data models, API design, tech stack
- User reviews and approves
```

**Step 3: Task Generation (OpenSpec)**
```
AI creates OpenSpec proposal:
- proposal.md: High-level summary
- tasks.md: Detailed task breakdown with dependencies
- spec-delta.md: Specification updates

Human review and approval required before implementation
```

**Step 4: Implementation (Implementation Mode)**
```
AI (Implementation Mode):
- Implements tasks sequentially
- For each task:
  * Generates code
  * Runs tests
  * Creates git commit
  * Updates task status
- Real-time progress visible in UI
```

**Step 5: Quality Assurance (Debug Mode)**
```
AI (Debug Mode):
- Runs automated test suites
- Analyzes failures
- Generates fixes
- Re-runs tests until all pass
```

**Step 6: Code Review & Deployment**
```
AI:
- Creates GitHub pull request
- Links to OpenSpec proposal
- Includes test results
- After merge: Updates specs, archives proposal
```

### Dual Chat Experience

**Normal Chat (General Purpose)**
- ChatGPT-style interface
- Two columns: chat history sidebar + main conversation area
- No project context loaded
- Use cases: general questions, brainstorming, learning
- Can convert to project with special command

**Project Chat (IDE-Integrated)**
- Cursor-inspired three-column layout:
  * Left: File explorer, git changes, active tasks, OpenSpec
  * Center: Code editor (CodeMirror 6) with AI inline suggestions
  * Right: AI chat with full project context
- Integrated terminal at bottom
- Full context: all files, git history, tasks, specs
- Real-time collaboration via WebSocket

### Multi-Mode AI System

**Pre-built Modes:**
1. **Research Mode**: Market research, idea validation, competitive analysis
2. **Architect Mode**: PRD/ARD generation, system design, architecture decisions
3. **Implementation Mode**: Code generation, debugging, refactoring
4. **Debug Mode**: Error analysis, testing, performance optimization
5. **Documentation Mode**: README, API docs, inline comments

**Custom Modes:**
- Unlimited user-defined modes
- Each mode has: name, icon, system prompt, temperature, tools, context strategy
- Examples: Security Audit, Performance Optimization, Database Migration

### Project Management Features

**Task Management**
- Multiple views: Board (Kanban), List, Calendar, Timeline (Gantt), Gallery
- Task dependencies (blocks/depends on)
- AI-powered estimation
- Automatic status updates from git commits
- Rich task detail modal with comments, files, related PRs

**Notion-Style Databases**
- Create custom databases for any structured data
- Dynamic properties: text, number, select, date, person, relation, formula, rollup
- Multiple views per database
- Real-time sync across all collaborators
- AI-powered auto-fill (estimates, metadata extraction)

**OpenSpec Integration**
- Visual UI for reviewing proposals (not just markdown)
- Auto-sync tasks from OpenSpec to database
- Git commits auto-update OpenSpec task status
- Automated archival when all tasks complete

## User Experience Goals

### Premium Minimalism
- Clean aesthetic inspired by Linear
- Notion's flexibility for databases
- Fast, smooth, no lag
- Beautiful dark/light theme throughout

### AI Transparency
- Always show what AI is doing and why
- Show token usage and cost estimates
- Confidence scores on AI suggestions
- Human approval gates for critical decisions

### Progressive Disclosure
- Simple by default
- Powerful features hidden until needed
- Keyboard shortcuts for power users
- Command palette (Cmd+K) for everything

### Consistent Rhythm
- 4px spacing grid throughout
- LCH color space for perfect neutrals (no color cast)
- Purple accent as brand color
- Inter Variable for UI, JetBrains Mono for code

### Accessibility First
- WCAG 2.1 AA compliance minimum
- Keyboard navigation everywhere
- Screen reader support
- Clear focus indicators

## Value Propositions

### For Solo Developers
- **AI pair programmer** that understands your entire project
- **Project manager** that tracks everything automatically
- **Documentation generator** that keeps docs in sync with code
- **Cost**: <$5/month in AI usage (vs $500+/month for alternatives)

### For Small Teams (2-10 people)
- **Unified workspace** - no more tool switching
- **Project memory** - new members get instant context
- **Automated workflow** - from idea to production
- **Cost**: Self-hosted (free) or hosted ($10/user/month)

### For Open Source Projects
- **Free self-hosted** deployment
- **Transparent AI** - contributors see AI decisions
- **Community modes** - share custom AI modes
- **Learning tool** - AI explains decisions for education

## Success Criteria (MVP)

### User Can Successfully:
1. Create account and login (email/password, GitHub, Google)
2. Create first project with tech stack
3. Have AI generate PRD from idea description
4. Review and approve AI-generated tasks
5. Watch AI implement first task
6. See code changes in integrated editor
7. Commit changes via git panel
8. See task automatically marked complete
9. Create custom database for tracking
10. Switch between light and dark theme seamlessly

### AI Quality Benchmarks:
- **Task Generation**: 80%+ accuracy (tasks make sense, properly scoped)
- **Code Implementation**: 70%+ success rate (compiles, tests pass)
- **Cost Efficiency**: <$5 per project on average
- **Response Relevance**: 90%+ helpful responses

### Technical Performance:
- **Speed**: <2s page load, <500ms API response
- **Reliability**: 99% uptime, <0.1% error rate
- **Scale**: Handles 50K LOC projects smoothly

### Community Adoption (4 months):
- 1,000 GitHub stars
- 100 monthly active users
- 100 projects created
- 50 AI-generated PRs merged

## Long-Term Vision (12+ months)

### Platform Evolution
- Mobile apps (iOS + Android)
- VS Code extension (Ardha inside IDE)
- Desktop apps (Electron)
- Team collaboration features (live cursors, comments)

### AI Advancement
- Multi-agent workflows (specialized AI agents)
- Self-improving prompts (ACE framework)
- Cross-project learning (organizational memory)
- Predictive task generation

### Enterprise Features
- SSO and SAML integration
- Audit logs and compliance
- Advanced security (SOC 2)
- Dedicated support

### Ecosystem
- Plugin marketplace
- Community modes library
- Template marketplace
- Integration directory

## Core Principles (Never Compromise)

1. **Open Source First**: Core platform always free and open
2. **Privacy Respected**: User data never trained on without permission
3. **AI Transparency**: Always show what AI is doing and why
4. **Developer Control**: AI suggests, human approves
5. **Cost Transparency**: 0% markup on AI costs for hosted version
6. **Performance First**: Fast is a feature, not optional
7. **Accessible Always**: WCAG compliance is mandatory
8. **Beautiful Default**: Design quality matters from day one