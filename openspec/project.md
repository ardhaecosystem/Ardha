# Ardha Project Documentation

**Version:** 1.0
**Last Updated:** November 1, 2025
**Project Type:** AI-Native Project Management & Development Platform
**License:** MIT (Open Source)

---

## 🎯 Project Vision

Ardha is the world's first truly unified AI-native project management and development platform that eliminates the artificial boundary between planning and execution. We solve the critical problem where development teams waste 58% of their time coordinating between fragmented tools.

### Core Mission
Democratize AI-powered software development by providing the world's most intelligent, transparent, and accessible project management platform that learns and evolves with every team.

### Revolutionary Approach
Current tools force teams to choose between:
- **Project Management** (Linear, Jira, Notion) - Planning without execution capability
- **AI Development** (Cursor, Cline, Replit) - Coding without project context

**Ardha eliminates this false dichotomy** by providing unified workflows where AI understands both project goals AND implementation details.

---

## 🏗️ System Architecture

### High-Level Architecture
Ardha follows a modern web application architecture with three primary layers:

**Frontend Layer:**
- React-based single-page application built with Next.js 15
- Real-time updates via WebSocket connections
- Embedded code editor for in-browser development
- Responsive design supporting desktop, tablet, and mobile

**Backend Layer:**
- RESTful API built with FastAPI (Python)
- Asynchronous request handling for high performance
- JWT-based authentication with OAuth2 support
- WebSocket server for real-time collaboration

**Data Layer:**
- PostgreSQL for relational data (users, projects, tasks)
- Qdrant vector database for semantic memory search
- Redis for caching and session management
- File system for project files and git repositories

### System Constraints
**Memory Budget: 8GB Total System RAM**
- PostgreSQL: 2GB container limit
- Qdrant: 2.5GB container limit (with quantization)
- Redis: 512MB container limit
- Backend: 2GB container limit
- Frontend: 1GB container limit

**Performance Targets:**
- Page load time: <2 seconds (90th percentile)
- API response time: <500ms (95th percentile)
- Initial bundle size: <200KB gzipped
- Time to Interactive: <3 seconds

---

## 🎨 User Experience Principles

### Design Philosophy

**Core Principles:**
1. **Premium Minimalism**: Clean aesthetic inspired by Linear with Notion's flexibility
2. **Performance First**: Fast page loads, smooth interactions, no lag
3. **AI Transparency**: Always show what AI is doing and why
4. **Progressive Disclosure**: Simple by default, powerful when needed
5. **Unified Theme System**: Seamless light/dark mode throughout
6. **Consistent Rhythm**: Predictable spacing and layout patterns
7. **Purposeful Animation**: Every motion serves a purpose
8. **Accessible by Default**: WCAG 2.1 AA compliance minimum

### Design System Standards

**Premium Theme System (Dark/Light Mode):**

**Core Theme Architecture:**
- LCH color space for mathematically perfect neutral grays (no color cast in either mode)
- CSS custom properties for dynamic switching without page reload
- System preference detection with manual override
- Theme persisted in user preferences (localStorage + database)
- Smooth transition animations (200ms) between mode switches
- All components support both modes without exceptions

**Theme Coverage - Every Single Element:**

**Authentication Pages (Login, Register, Password Reset):**
- Background: Gradient from neutral-50 to neutral-100 (light) / neutral-0 to neutral-50 (dark)
- Form cards: White with shadow (light) / neutral-100 elevated (dark)
- Input fields: Light borders with focus rings in both modes
- Buttons: Purple primary maintains brand consistency
- Logos: SVG with theme-aware colors
- Error messages: Red semantic color adjusted for contrast
- Loading states: Skeleton screens respect theme
- OAuth buttons: Brand colors (GitHub black, Google white) with theme-aware borders

**Main Application Layout:**
- App background: neutral-50 (light) / neutral-0 (dark)
- Sidebar background: neutral-100 (light) / neutral-50 (dark)
- Sidebar borders: neutral-200 (light) / neutral-300 (dark)
- Header background: neutral-0 (light) / neutral-100 (dark)
- Header shadow: Subtle in light, none in dark
- Scrollbars: Themed to match UI colors

**Project Pages:**
- Content area: White (light) / neutral-100 (dark)
- Section dividers: neutral-200 (light) / neutral-300 (dark)
- Card backgrounds: White elevated (light) / neutral-100 (dark)
- Card hover: neutral-100 (light) / neutral-200 (dark)
- Text hierarchy: neutral-800/600/500 (light) / neutral-900/700/600 (dark)

**Task Board (Kanban):**
- Column backgrounds: neutral-100 (light) / neutral-50 (dark)
- Task cards: White (light) / neutral-100 (dark)
- Task card shadows: Soft shadows (light) / elevated borders (dark)
- Drag indicators: Purple with transparency
- Status badges: Semantic colors with theme-adjusted contrast
- Priority indicators: Color-coded with accessibility

**Code Editor (Project Chat):**
- Editor background: neutral-0 (light) / neutral-50 (dark)
- Syntax highlighting: One Light theme (light) / One Dark Pro theme (dark)
- Line numbers: neutral-400 (light) / neutral-600 (dark)
- Active line: neutral-100 (light) / neutral-100 (dark)
- Selection: Purple-100 with alpha (light) / Purple-900 with alpha (dark)
- Cursor: Purple-500 in both modes
- Inline suggestions: Dimmed text in theme color

**Chat Interface:**
- Chat background: neutral-50 (light) / neutral-0 (dark)
- User messages: Purple-50 (light) / Purple-900 (dark)
- AI messages: neutral-100 (light) / neutral-100 (dark)
- Message borders: Subtle in both modes
- Code blocks: Editor theme colors
- AI thinking indicator: Animated dots in purple
- Timestamp text: neutral-500 (light) / neutral-600 (dark)

**Modals and Dialogs:**
- Overlay: Black 50% alpha (light) / Black 70% alpha (dark)
- Modal background: White (light) / neutral-100 (dark)
- Modal shadows: Strong elevation in light, border in dark
- Modal headers: neutral-100 (light) / neutral-50 (dark)

**Dropdowns and Menus:**
- Background: White (light) / neutral-100 (dark)
- Hover states: neutral-100 (light) / neutral-200 (dark)
- Active items: Purple-50 (light) / Purple-900 (dark)
- Separators: neutral-200 (light) / neutral-300 (dark)

**Forms and Inputs:**
- Input background: White (light) / neutral-100 (dark)
- Input border: neutral-200 (light) / neutral-400 (dark)
- Input focus: Purple-500 ring in both modes
- Placeholder: neutral-400 (light) / neutral-500 (dark)
- Disabled: neutral-100 (light) / neutral-200 (dark) with reduced opacity

**Tables and Lists:**
- Row background: Alternating white/neutral-50 (light) / neutral-100/neutral-50 (dark)
- Row hover: neutral-100 (light) / neutral-200 (dark)
- Header background: neutral-100 (light) / neutral-50 (dark)
- Header text: Bold, neutral-800 (light) / neutral-900 (dark)
- Cell borders: neutral-200 (light) / neutral-300 (dark)

**Calendars and Timelines:**
- Grid lines: neutral-200 (light) / neutral-300 (dark)
- Today marker: Purple-500 highlight
- Weekend shading: neutral-100 (light) / neutral-50 (dark)
- Event cards: Colored by category with theme-aware opacity
- Overdue indicators: Red semantic color

**Toast Notifications:**
- Success: Green-50 bg, green-700 text (light) / Green-900 bg, green-100 text (dark)
- Error: Red-50 bg, red-700 text (light) / Red-900 bg, red-100 text (dark)
- Warning: Yellow-50 bg, yellow-800 text (light) / Yellow-900 bg, yellow-100 text (dark)
- Info: Blue-50 bg, blue-700 text (light) / Blue-900 bg, blue-100 text (dark)

**Loading States:**
- Skeletons: neutral-200 animated (light) / neutral-300 animated (dark)
- Progress bars: Purple gradient with transparency
- Spinners: Purple-500 in both modes

**Icons and Emojis:**
- Icons: Lucide React with currentColor (adapts to theme)
- Icon size: Consistent 16px, 20px, 24px based on context
- Emoji: Native emoji rendering (consistent across themes)
- Icon buttons: Proper hover/active states in both themes

**Animations:**
- Fade transitions: 150ms ease-out
- Scale transforms: 250ms spring easing
- Slide animations: 200ms ease-in-out
- All animations respect prefers-reduced-motion
- Smooth theme switching: 200ms color transitions

**Typography:**
- Font: Inter Variable for UI, weight 400/500/600
- Font: JetBrains Mono for code, weight 400
- Text rendering: -webkit-font-smoothing antialiased
- Letter spacing: Slight tracking for uppercase labels
- Line height: 1.6 for body, 1.2-1.4 for headings
- Font size scale: Consistent across all pages

**Spacing and Layout:**
- Base unit: 4px (0.25rem)
- All spacing in multiples of 4px
- Consistent padding: 16px/24px/32px based on element
- Consistent margins: 8px/16px/24px based on context
- Consistent border radius: 4px (buttons), 6px (cards), 8px (modals)

**Accessibility in Themes:**
- WCAG 2.1 AA contrast ratios minimum
- Focus indicators: 2px purple ring, 2px offset
- Keyboard navigation: Clear focus states in both themes
- Screen reader: Theme announcement on switch
- High contrast mode support: Fallback to system colors

**Theme Toggle Component:**
- Location: User menu in header
- Icon: Sun (light mode) / Moon (dark mode)
- Keyboard shortcut: Cmd/Ctrl + Shift + T
- Tooltip: "Switch to dark mode" / "Switch to light mode"
- Animation: Icon rotation on toggle
- Persistence: Saved to user preferences immediately

**Color System:**
- LCH color space for mathematically perfect neutral grays (no color cast in either mode)
- Primary accent: Purple (brand color)
- Semantic colors: Green (success), Red (error), Yellow (warning), Blue (info)
- AI-specific gradient: Purple to pink with subtle glow effects

**Typography:**
- Font family: Inter Variable for UI, JetBrains Mono for code
- Type scale: Major Third ratio (1.250)
- Base size: 15px (0.9375rem) for optimal readability
- Line height: 1.6 for body text, 1.2-1.4 for headings

**Spacing System:**
- Base unit: 4px (0.25rem)
- All spacing must be multiples of 4px
- Consistent padding, margins, and gaps throughout

**Component States:**
- Every interactive element has: default, hover, active, focus, disabled states
- Smooth transitions using defined duration and easing functions
- Keyboard navigation support for accessibility

---

---

## 📄 Complete Page Descriptions

### Authentication Pages

**1. Login Page**
- **Layout**: Centered card on gradient background
- **Elements**:
  - Ardha logo at top (theme-aware SVG)
  - "Welcome back" heading with subtitle
  - Email input field (with icon)
  - Password input field (with show/hide toggle icon)
  - "Remember me" checkbox
  - "Forgot password?" link (right-aligned)
  - "Sign in" primary button (full width)
  - Divider with "or continue with"
  - OAuth buttons: GitHub and Google (side by side)
  - "Don't have an account? Sign up" link at bottom
- **States**:
  - Loading state: Button shows spinner, form disabled
  - Error state: Red toast notification with message
  - Success state: Smooth redirect to dashboard
- **Theme**: Premium card with shadow (light) / elevated (dark)
- **Validation**: Real-time email format check, required fields

**2. Register Page**
- **Layout**: Similar to login, slightly taller card
- **Elements**:
  - Ardha logo at top
  - "Create your account" heading
  - Full name input field
  - Username input field (with availability check)
  - Email input field
  - Password input field (with strength indicator)
  - Confirm password input field
  - Terms of service checkbox (required)
  - "Create account" primary button
  - OAuth options (GitHub, Google)
  - "Already have an account? Sign in" link
- **States**:
  - Password strength: Visual indicator (weak/medium/strong)
  - Username availability: Real-time check with icon
  - Validation errors: Below each field
- **Theme**: Matches login page aesthetic

**3. Forgot Password Page**
- **Layout**: Centered card
- **Elements**:
  - Back arrow to login
  - "Reset your password" heading
  - Explanatory text
  - Email input field
  - "Send reset link" button
  - Success message: "Check your email"
  - "Return to login" link
- **Flow**: Email → Check inbox → Reset link email → Password reset page

**4. Password Reset Page**
- **Layout**: Centered card
- **Elements**:
  - "Create new password" heading
  - New password input (with strength indicator)
  - Confirm password input
  - "Reset password" button
  - Password requirements list
- **Validation**: 8+ characters, uppercase, lowercase, number, special char

---

### Main Application Pages

**5. Dashboard / Home Page**
- **Layout**: Sidebar + main content area + header
- **Header**:
  - Ardha logo (left)
  - Search bar (Cmd+K trigger) - center
  - Notifications bell icon
  - Theme toggle
  - User avatar dropdown (right)
- **Sidebar**:
  - User profile section (avatar, name, status)
  - Navigation sections:
    - Home (dashboard icon)
    - Projects (folder icon with count badge)
    - Chats (message icon)
    - Settings (gear icon)
  - "+ New" button (creates project or chat)
  - Projects list (expandable)
  - Chats list (expandable)
- **Main Content**:
  - Welcome banner with user name
  - Quick actions grid:
    - "New Project" card
    - "Start Normal Chat" card
    - "Browse Templates" card
    - "View Documentation" card
  - Recent projects section (grid of project cards)
  - Recent chats section (list of chat items)
  - Activity feed (recent updates across all projects)
- **Theme**: Dashboard background, card-based layout, hover effects
- **Empty State**: Onboarding cards if no projects/chats exist

**6. Projects List Page**
- **Layout**: Sidebar + main content
- **Header Bar**:
  - "Projects" heading with count
  - View toggle: Grid / List
  - Filter dropdown: All / My Projects / Shared / Archived
  - Sort dropdown: Recent / Name / Created Date
  - "+ New Project" button (primary, right-aligned)
- **Grid View**:
  - Project cards in responsive grid (3-4 columns)
  - Each card:
    - Project icon (emoji or uploaded)
    - Project name
    - Description (truncated)
    - Tech stack badges
    - Last updated timestamp
    - Team avatars (max 3, +N more)
    - Progress bar (tasks completed percentage)
    - Hover: Reveals quick actions (Open, Settings, Archive)
- **List View**:
  - Table with columns: Icon, Name, Description, Owner, Tasks, Last Updated, Actions
  - Sortable columns
  - Row hover: Highlight with actions
- **Empty State**: Large illustration, "Create your first project" CTA
- **Loading State**: Skeleton cards/rows

**7. Project Detail Page**
- **Layout**: Sidebar + main tabbed content + header
- **Project Header**:
  - Project icon + name (editable inline)
  - Tech stack badges
  - Star/favorite toggle
  - Members avatars
  - "+ Invite" button
  - "Settings" icon button
  - Project status badge (Active / Archived)
- **Project Sidebar** (nested within app sidebar):
  - Overview (dashboard icon)
  - Tasks (checkbox icon) with count badge
  - Board (kanban icon)
  - Timeline (calendar icon)
  - Databases (table icon) - expandable list
    - Each database listed with icon
  - Chat (message icon)
  - Files (folder icon)
  - Git (branch icon)
  - OpenSpec (document icon)
  - Settings (gear icon)
- **Main Content** (changes based on sidebar selection):
  - Default: Overview dashboard
  - Shows: Project stats, recent activity, task summary, upcoming milestones

**8. Project Overview (Dashboard)**
- **Layout**: Grid of stat cards + sections
- **Stat Cards** (top row):
  - Total tasks (with completion percentage)
  - Active tasks
  - In review tasks
  - Completed this week
- **Charts Section**:
  - Task completion velocity (line chart)
  - Tasks by status (donut chart)
  - AI usage by mode (bar chart)
  - Time estimates vs actual (comparison chart)
- **Recent Activity Feed**:
  - Timeline of recent updates
  - Each entry: Icon, action description, user avatar, timestamp
  - Types: Task created, Task completed, Commit pushed, PR merged, Chat activity
- **Upcoming Section**:
  - Next milestone card (with progress)
  - Overdue tasks warning (if any)
  - Next team meeting (if scheduled)
- **Quick Actions**:
  - "Generate Tasks from Idea" button (AI)
  - "Create Manual Task" button
  - "Start Project Chat" button

**9. Tasks Page (List View)**
- **Layout**: Full-width table
- **Header Bar**:
  - "Tasks" heading with count
  - View toggle: Board / List / Calendar / Timeline
  - Filters: Status, Assignee, Priority, Tags, Milestone
  - Sort: Priority / Due Date / Created Date / Assignee
  - Group by: Status / Assignee / Milestone / None
  - Search: Filter tasks by text
  - "+ New Task" button
- **Table Columns**:
  - Checkbox (multi-select)
  - ID (e.g., ARD-42)
  - Title (clickable, opens task detail)
  - Status badge
  - Assignee avatar
  - Priority indicator
  - Due date (with overdue warning)
  - Estimate hours
  - Tags (max 3, +N more)
  - Actions (three dots menu)
- **Row Interactions**:
  - Click: Open task detail modal
  - Hover: Highlight row, show actions
  - Right-click: Context menu (Assign, Change Status, Delete)
- **Bulk Actions** (when multiple selected):
  - Assign to...
  - Change status to...
  - Add tag...
  - Delete tasks
- **Empty State**: "No tasks found" with filter reset option

**10. Task Board (Kanban View)**
- **Layout**: Horizontal columns with scrolling
- **Columns** (default):
  - Backlog (gray)
  - To Do (blue)
  - In Progress (yellow)
  - In Review (purple)
  - Done (green)
- **Column Header**:
  - Status name
  - Task count badge
  - "+ Add Task" button (on hover)
  - Column menu (collapse, hide, settings)
- **Task Cards**:
  - Drag handle (six dots icon)
  - Task ID (small, top-left)
  - Task title (2 lines max, truncated)
  - Assignee avatar (bottom-left)
  - Priority indicator (colored dot)
  - Tags (max 2, bottom)
  - Due date badge (if set)
  - Comment count (if any)
  - Attachment count (if any)
  - AI badge (if AI-generated)
  - Estimate hours (bottom-right)
- **Drag & Drop**:
  - Smooth animation when dragging
  - Column highlights on drag over
  - Auto-status update on drop
  - Undo notification appears briefly
- **Filters**: Same as list view, applied to all columns
- **Empty Column**: "No tasks" with "+ Add Task" button

**11. Task Detail Modal**
- **Layout**: Large modal (80% viewport width/height)
- **Header**:
  - Task ID badge
  - Task title (editable inline)
  - Close button (×)
- **Left Panel (main content, 70%)**:
  - **Status Section**:
    - Status dropdown (changes color on select)
    - Priority dropdown
    - Assignee selector (with avatar)
  - **Description Section**:
    - Rich text editor
    - Markdown support
    - Image paste support
  - **Acceptance Criteria**:
    - Checklist items
    - Add new criteria button
  - **Related Section**:
    - Dependencies (blocks/depends on)
    - Related commits (with links)
    - Related PRs (with status)
    - Related files (clickable)
  - **Comments Section**:
    - Comment thread
    - Mention support (@username)
    - Rich text / code blocks
    - Edit/delete own comments
- **Right Panel (sidebar, 30%)**:
  - **Metadata**:
    - Created by (user + timestamp)
    - Created at date
    - Last updated timestamp
  - **Estimation**:
    - Estimate hours input
    - Actual hours (tracked)
    - Complexity dropdown
  - **Organization**:
    - Phase selector
    - Milestone selector
    - Epic selector (if applicable)
  - **Tags**:
    - Tag selector (multi-select)
    - Create new tag inline
  - **OpenSpec**:
    - Link to OpenSpec proposal (if applicable)
    - View in OpenSpec button
  - **AI Actions**:
    - "AI: Implement Task" button
    - "AI: Generate Tests" button
    - "AI: Estimate Time" button
- **Footer**:
  - Activity log (collapsed by default)
  - Delete task button (destructive, right)

**12. Calendar View**
- **Layout**: Full calendar grid
- **Header**:
  - Month/Year navigation (< Today >)
  - View toggle: Month / Week / Day
  - "Sync with Google Calendar" button
  - Filter by: Tasks / Meetings / Milestones / All
- **Calendar Grid**:
  - Day cells with date number
  - Events as colored bars/dots
  - Each event shows: Icon, title, time, assignee avatar
  - Today highlighted
  - Weekends shaded differently
  - Overdue tasks in red
- **Event Click**: Opens task detail modal
- **Drag & Drop**: Reschedule by dragging
- **Empty Day**: Click to create new task with that due date
- **Milestone Markers**: Special badge on milestone target dates

**13. Timeline View (Gantt Chart)**
- **Layout**: Left task list + right timeline bars
- **Left Panel**:
  - Task ID
  - Task title
  - Assignee avatar
  - Expand/collapse for subtasks
- **Right Panel**:
  - Timeline grid (days/weeks/months)
  - Task bars (color-coded by status)
  - Dependencies shown as arrows
  - Milestones as diamonds
  - Today marker (vertical line)
- **Interactions**:
  - Drag bar edges to adjust duration
  - Drag entire bar to reschedule
  - Hover: Show task details tooltip
  - Click: Open task detail
- **Zoom Controls**: Day / Week / Month / Quarter view

**14. Database View Page**
- **Layout**: Sidebar + main database view + header
- **Database Header**:
  - Database icon + name (editable)
  - Description (expandable)
  - View selector dropdown (Board / List / Calendar / Timeline / Gallery)
  - "+ New View" button
  - "Edit Properties" button
  - "Database Settings" button (three dots)
- **Toolbar**:
  - Filter button (opens filter builder)
  - Sort button (opens sort configurator)
  - Group by dropdown
  - Search bar
  - "+ New Entry" button (primary, right)
- **Main Content** (changes based on selected view):
  - Board: Like task board but for any database
  - List: Table with all properties as columns
  - Calendar: Events plotted on calendar
  - Timeline: Gantt-style timeline
  - Gallery: Card grid with image/icon preview
- **Property Editor Modal**:
  - List of all properties
  - Reorder by drag-and-drop
  - Add property button
  - Each property: Name, type, settings, delete button
  - Type-specific configuration forms

**15. Normal Chat Page (ChatGPT-Style)**
- **Layout**: Two-column (sidebar + chat area)
- **Sidebar** (left, 280px):
  - "+ New Chat" button (top)
  - Chat history grouped:
    - Today
    - Yesterday
    - Last 7 days
    - Last 30 days
    - Older
  - Each chat item:
    - Chat title (truncated)
    - Last message preview (dimmed)
    - Timestamp
    - Hover: Show delete/rename icons
- **Chat Area** (right):
  - **Header**:
    - Chat title (editable, click to rename)
    - Mode selector (if using custom mode)
    - Settings icon (model selection, temperature)
    - Share button
    - Clear conversation button
  - **Messages Area** (scrollable):
    - User messages: Right-aligned, purple background
    - AI messages: Left-aligned, neutral background
    - Timestamps between messages (relative: "2 minutes ago")
    - Each AI message:
      - AI avatar/icon
      - Message content (markdown rendered)
      - Code blocks with syntax highlighting
      - Copy button for code blocks
      - Regenerate button
      - Thumbs up/down feedback buttons
    - Streaming messages: Typing indicator, incremental text
  - **Input Area** (bottom):
    - Textarea (auto-expands up to 10 lines)
    - Attach file button
    - Emoji picker button
    - Send button (or Enter to send)
    - Model selector (small text below: "Using GPT-4o")
    - Token count (small text: "~1,234 tokens")
- **Empty State**: "Start a conversation" with suggested prompts
- **Loading State**: AI thinking animation (three dots pulsing)

**16. Project Chat Page (Cursor-Inspired with Ardha Theme)**
- **Layout**: Three-column + header + terminal (complex IDE layout)
- **Header** (full width, purple accent):
  - Ardha logo + Project name with icon (left)
  - Current git branch dropdown with branch icon (left-center)
  - AI mode selector pills: Research / Architect / Implementation / Debug / Documentation (center)
    - Active mode: Purple fill
    - Inactive modes: Transparent with border
    - Mode icons for visual distinction
  - Command palette hint: "Press ⌘K to search" (center-right)
  - OpenSpec status indicator with badge (active proposals count)
  - Theme toggle (moon/sun icon)
  - User avatar dropdown (right)
- **Left Panel - File Explorer** (280px, resizable with drag handle):
  - **Top Bar**:
    - "EXPLORER" label (uppercase, small)
    - Collapse all / Expand all icons
    - Refresh icon
    - New file / New folder icons
  - **File Tree** (Ardha theme):
    - Folder icons: Chevron right (collapsed) / down (expanded)
    - File icons: Language-specific (colorful)
    - Indentation: 16px per level
    - Git status badges: Green (M), Blue (A), Red (D), Yellow (U)
    - Selected file: Purple highlight background
    - Hover: Light purple background
    - Click: Open in center editor
    - Right-click: Context menu (Rename, Delete, Copy Path, Reveal in Finder)
  - **Bottom Sections** (accordion, collapsible):
    - **Git Changes** (default expanded):
      - Section header with count badge
      - Branch name with icon
      - Staged changes (green checkmark icon)
      - Unstaged changes (orange dot icon)
      - Each file: Checkbox, file name, git action badge
      - Commit message input (multiline textarea)
      - Commit button (purple, full width)
      - Push/Pull buttons (side by side)
    - **Active Tasks** (collapsed by default):
      - Current sprint/milestone name
      - Task list (compact):
        - Task checkbox
        - Task ID badge
        - Task title (truncated)
        - Assignee avatar (small)
      - Click task: Open task detail modal
      - "View all tasks" link at bottom
    - **OpenSpec** (collapsed by default):
      - Active proposals count badge
      - Proposal list:
        - Proposal name
        - Status badge (Pending/Approved)
        - Click: Open OpenSpec panel in center
      - "View all specs" link
- **Center Panel - Code Editor** (flexible width, ~50%, resizable):
  - **Tab Bar** (Ardha theme):
    - Open file tabs (max 12 visible, overflow menu)
    - Each tab:
      - File icon
      - File name
      - Modified dot (orange if unsaved)
      - Close × button (on hover)
    - Active tab: Purple bottom border (2px)
    - Inactive tabs: Transparent background
    - Tab hover: Light purple background
  - **Editor Area** (CodeMirror 6, Ardha-themed):
    - Theme integration:
      - Light mode: One Light theme with purple accents
      - Dark mode: One Dark Pro with purple accents
    - Line numbers: Left gutter, same theme as sidebar
    - Git change indicators: Left gutter bars
      - Green: Added lines
      - Red: Deleted lines
      - Yellow: Modified lines
    - Current line: Subtle highlight (matches theme)
    - Bracket matching: Purple outline
    - Code folding: Chevron icons in gutter
    - Selection: Purple-100 (light) / Purple-900 (dark) with alpha
    - Cursor: Purple-500 (2px width, blinks)
    - Minimap: Optional, right side, same theme
  - **AI Inline Suggestions** (Ardha style):
    - Ghost text in dimmed gray (50% opacity)
    - Purple dot indicator at line start
    - Hover: Show "Tab to accept, Esc to dismiss" tooltip
    - Accept animation: Fade in from gray to normal text
    - Manual trigger: Cmd+Space shows purple loading indicator
  - **Editor Footer Bar**:
    - File path breadcrumb (clickable segments)
    - Language mode selector (dropdown)
    - Line:Column position (e.g., "Ln 42, Col 8")
    - Encoding (UTF-8)
    - EOL type (LF/CRLF)
    - Indentation (Spaces: 2 or Tabs: 1, clickable)
    - All in small text, neutral-600 color
- **Right Panel - AI Project Chat** (380px, resizable):
  - **Chat Header** (purple accent):
    - "AI Assistant" label with sparkles icon
    - Current mode badge (pill shape, colored by mode)
    - Model indicator (small text: "Claude Sonnet 4.5")
    - Clear chat icon button
    - Chat settings icon button
  - **Context Panel** (collapsible, below header):
    - "Context Loaded" header with info icon
    - Context items (compact list):
      - "📁 12 files" with expand button
      - "🌿 Branch: main" with clickable link
      - "📋 Active: add-auth" (OpenSpec) with link
      - "💾 3 uncommitted changes" with link
      - "📝 Last 5 commits" with expand
    - Expand shows detailed list of each context item
    - Token usage bar: "~45k / 200k tokens"
  - **Messages Area** (scrollable, compact):
    - User messages:
      - Right-aligned
      - Purple-500 background (light) / Purple-900 (dark)
      - White text
      - Avatar (user photo, small)
      - Max width: 85%
      - Timestamp below (small, dimmed)
    - AI messages:
      - Left-aligned
      - Neutral-100 background (light) / Neutral-100 (dark)
      - Normal text color
      - AI icon (purple sparkles)
      - Max width: 90%
      - Markdown rendered (bold, italic, lists, tables)
      - Code blocks:
        - Language badge (top-right)
        - Copy button (hover, top-right)
        - "Apply to file" button (if code change suggested)
        - Syntax highlighting matches editor theme
      - File diffs:
        - File name header
        - Diff viewer (+ green, - red)
        - "Accept" / "Reject" buttons (bottom)
      - Task updates:
        - Task ID badge
        - Status change indicator
        - Link to open task detail
      - Timestamp below (small)
      - Action buttons row (on hover):
        - Regenerate (circular arrow icon)
        - Copy (clipboard icon)
        - Thumbs up/down (feedback)
    - Streaming AI messages:
      - Typing indicator: Three purple dots pulsing
      - Text appears word-by-word
      - Cursor blinks at end during streaming
  - **Quick Actions Bar** (above input, sticky):
    - Slash command hints (small chips):
      - "/implement" - Implement task
      - "/review" - Code review
      - "/test" - Generate tests
      - "/fix" - Fix error
      - "/explain" - Explain code
    - Click chip: Insert into input
    - Horizontal scroll if too many
  - **Input Area** (bottom, sticky):
    - **File Context Indicator** (if code selected):
      - Small banner above input
      - "Context: main.py lines 42-58"
      - × button to clear selection
    - **Textarea**:
      - Auto-expands up to 6 lines
      - Placeholder: "Ask about your project or describe a task..."
      - Rounded corners, border matches theme
      - Focus: Purple ring (2px)
    - **Input Toolbar** (inline, right side of textarea):
      - Attach file icon (from project tree)
      - Select code range icon (pick lines from editor)
      - Emoji picker icon
    - **Bottom Bar** (below textarea):
      - Left: Token count "~234 tokens"
      - Right: Send button (purple, icon: paper plane)
      - Enter to send, Shift+Enter for new line
- **Bottom Panel - Integrated Terminal** (height ~180px, collapsible, resizable):
  - **Terminal Tab Bar**:
    - Multiple terminal tabs (max 5, scrollable)
    - Each tab:
      - Terminal icon
      - Shell name (bash/zsh/sh)
      - × close button (on hover)
    - "+ New Terminal" button (right)
    - Active tab: Purple bottom border
  - **Terminal Instance** (xterm.js, Ardha-themed):
    - Theme: Matches editor (One Light / One Dark Pro)
    - Font: JetBrains Mono (same as code editor)
    - Font size: 13px
    - Cursor: Purple block, blinking
    - Selection: Purple-100 background
    - Scrollback: 1000 lines
    - Click file paths: Open in editor
    - Cmd+C / Cmd+V: Copy/paste support
    - Drag & drop files: Paste file path
  - **Terminal Toolbar** (right side, vertical):
    - Split terminal icon (horizontal/vertical)
    - Clear terminal icon (trash)
    - Kill terminal icon (×)
    - Maximize/restore icon (expand/compress)
    - All icons: Neutral color, hover: purple
  - **Terminal Status Bar** (bottom of panel):
    - Current directory (left)
    - Terminal type (center): bash, zsh, etc.
    - Exit code (right): 0 (green) or error code (red)
- **Panel Interactions** (Ardha-specific):
  - **Resize Handles**:
    - Between panels: 4px drag handle
    - Hover: Purple highlight
    - Dragging: Purple line indicator
    - Snap to sizes: 25%, 33%, 50%, 66%, 75%
  - **Panel Collapse**:
    - Minimize buttons on panel headers
    - Collapsed: Shows thin bar with icon to expand
    - Expand animation: 200ms ease-out
  - **Split Views**:
    - Editor can split: Vertical or horizontal
    - Split button in editor toolbar
    - Each split: Independent tab bar and editor
    - Split divider: Resizable, purple on hover
  - **Keyboard Shortcuts** (all with purple highlights):
    - Cmd+K: Command palette
    - Cmd+B: Toggle file explorer
    - Cmd+J: Toggle terminal
    - Cmd+\: Toggle AI chat
    - Cmd+P: Quick file open
    - Cmd+Shift+P: Command palette (actions)
    - Cmd+`: Switch terminal
    - Cmd+Shift+F: Find in files
    - Cmd+Shift+L: Toggle layout (focused/default)
- **Command Palette** (Cmd+K, Ardha design):
  - Large centered modal (600px wide)
  - Purple accent top border
  - Search input: Auto-focused, large text, purple focus ring
  - Results sections (with icons):
    - Recent (clock icon)
    - Projects (folder icon)
    - Tasks (checkbox icon)
    - Files (file icon)
    - Commands (terminal icon)
    - AI Modes (sparkles icon)
  - Each result:
    - Icon + Title + Description
    - Keyboard shortcut (right side, dimmed)
    - Hover: Purple background
    - Selected: Purple background, white text
  - Navigation: Arrow keys, Enter to select, Esc to close
  - Fuzzy search: Highlights matching characters in purple
- **Ardha Theme Consistency Throughout Project Chat**:
  - Purple as primary accent (buttons, highlights, borders)
  - LCH color space neutrals (perfect grays)
  - Smooth transitions (200ms) on all interactions
  - 4px spacing grid maintained
  - Icons: Lucide React, consistent sizes
  - Fonts: Inter UI, JetBrains Mono code
  - Shadows: Subtle in light, borders in dark
  - Focus states: 2px purple ring, 2px offset
  - Hover states: Light purple background
  - Active states: Darker purple background
  - All text: Proper contrast ratios (WCAG AA)

**17. Files Page**
- **Layout**: Breadcrumb + file grid/list
- **Header**:
  - Breadcrumb navigation (Project / Folder / Subfolder)
  - View toggle: Grid / List
  - Sort: Name / Date / Size / Type
  - Search files
  - Upload button
  - New folder button
- **Grid View**:
  - File/folder cards with preview thumbnails
  - File icons for types
  - File name
  - File size
  - Last modified date
- **List View**:
  - Table: Icon, Name, Size, Type, Modified, Actions
  - Sortable columns
- **Interactions**:
  - Click folder: Navigate into
  - Click file: Open preview or download
  - Right-click: Context menu (Rename, Delete, Download, Copy link)

**18. Git Page**
- **Layout**: Tab-based
- **Tabs**: Changes / History / Branches / Settings
- **Changes Tab**:
  - Unstaged changes section (file list)
  - Staged changes section (file list)
  - Commit message input (with emoji picker)
  - Commit button
  - Diff viewer (for selected file)
- **History Tab**:
  - Commit timeline (reverse chronological)
  - Each commit: Hash, message, author, date
  - Click: Show commit details and diff
- **Branches Tab**:
  - Current branch indicator
  - Branch list (local and remote)
  - New branch button
  - Merge/delete options
- **Settings Tab**:
  - Remote URL
  - Git user config
  - .gitignore editor

**19. OpenSpec Page**
- **Layout**: Two-column (proposals list + content)
- **Left Panel**:
  - Active proposals list
  - Archived proposals list
  - Each proposal item: Name, status badge, date
- **Right Panel** (when proposal selected):
  - Proposal details (markdown rendered)
  - Tasks list (with completion checkboxes)
  - Spec delta (diff view)
  - Action buttons: Approve / Request Changes / Archive
- **Empty State**: "No active proposals" with guide link

**20. Project Settings Page**
- **Layout**: Sidebar menu + settings content
- **Settings Menu** (left):
  - General
  - Members & Permissions
  - Git Integration
  - AI Configuration
  - OpenSpec Settings
  - Databases
  - Danger Zone
- **General**:
  - Project name input
  - Project icon upload/emoji picker
  - Description textarea
  - Visibility (private/team/public)
  - Tech stack multi-select
  - Save changes button
- **Members & Permissions**:
  - Members list table
  - Role dropdowns per member
  - Invite member button
  - Pending invitations list
- **Git Integration**:
  - Repository URL input
  - Default branch input
  - Auto-commit settings toggle
  - GitHub token input (masked)
- **AI Configuration**:
  - Default AI mode selector
  - Model preference (auto or specific)
  - Budget limits (daily/monthly)
  - Custom modes list with edit/delete
- **OpenSpec Settings**:
  - Enable/disable OpenSpec
  - OpenSpec directory path
  - Auto-approve settings
- **Databases**:
  - List of all databases
  - Create database button
  - Edit/delete per database
- **Danger Zone**:
  - Archive project button
  - Delete project button (requires confirmation)

**21. User Settings Page**
- **Layout**: Sidebar menu + settings content
- **Settings Menu**:
  - Profile
  - Account
  - Appearance
  - AI Preferences
  - Notifications
  - Integrations
  - Billing (for hosted version)
  - Security
- **Profile**:
  - Avatar upload
  - Full name input
  - Username input (with availability check)
  - Bio textarea
  - Save changes button
- **Account**:
  - Email (read-only, with change email button)
  - Password change section
  - Connected OAuth accounts
  - Delete account button
- **Appearance**:
  - Theme selector: Light / Dark / System
  - Accent color picker (currently purple, locked for brand)
  - Font size slider (13px - 17px)
  - Compact mode toggle
  - Code editor theme: One Light / One Dark Pro / Custom
- **AI Preferences**:
  - Default mode selector
  - Model preference (Auto / Specific model)
  - Budget alerts settings
  - Daily limit (dollars)
  - Monthly limit (dollars)
  - Alert at percentage (80%)
  - Auto-execute tools toggle
- **Notifications**:
  - Email notifications toggles
  - In-app notifications toggles
  - Desktop notifications permission
  - Notification sounds toggle
- **Integrations**:
  - GitHub connection status
  - Google connection status
  - Calendar sync (Google Calendar)
  - Add integration button
- **Billing** (hosted version only):
  - Current plan (Free / Pro / Enterprise)
  - Usage this month (tokens/cost)
  - Payment method
  - Billing history table
  - Download invoices
- **Security**:
  - Two-factor authentication setup
  - Active sessions list (with device info)
  - API tokens management
  - Security log

**22. Command Palette (Cmd+K)**
- **Modal**: Center screen, 600px wide, purple top accent
- **Search Input**: Auto-focused, large text, purple focus ring
- **Results Sections**:
  - Recent (clock icon)
  - Projects (folder icon)
  - Tasks (checkbox icon)
  - Files (file icon)
  - Commands (terminal icon)
  - AI Modes (sparkles icon)
- **Result Items**:
  - Icon, title, description, keyboard shortcut
  - Highlighted matching text (purple)
  - Hover: Purple background
- **Navigation**: Arrow keys up/down, Enter to select, Esc to close
- **Empty State**: "No results found" with search tips

**23. Error Pages**

**404 Not Found:**
- Theme-aware illustration
- "Page not found" heading
- Helpful message
- "Go to Dashboard" button (purple)
- "Go Back" button (secondary)

**500 Server Error:**
- Error illustration
- "Something went wrong" heading
- Error ID (for support reference)
- "Try Again" button
- "Contact Support" button
- Details collapse (for technical users)

**Offline Page:**
- Offline illustration
- "You're offline" heading
- Explanation text
- "Check Connection" button
- Auto-retry counter

---

## 🔄 Core Workflows

### Workflow 1: End-to-End AI Orchestration (Idea → Production)

**Stage 1: Idea Exploration (Research Mode)**
- User describes idea in natural language
- AI conducts market research, competitive analysis, technical feasibility assessment
- Outputs: Research summary, market opportunity brief, technical recommendations

**Stage 2: Requirements Definition (Architect Mode)**
- AI generates Product Requirements Document (PRD)
- AI generates Architecture Requirements Document (ARD)
- Includes: vision, target users, features, success metrics, tech stack, data models, API design

**Stage 3: Task Generation (OpenSpec Integration)**
- AI creates OpenSpec proposal in `openspec/changes/` directory
- Generates: proposal.md (summary), tasks.md (breakdown), spec-delta.md (spec updates)
- Proposal includes task phases, dependencies, estimates

**Stage 4: Human Review & Approval**
- User reviews PRD, ARD, and generated tasks in Ardha UI
- Can modify requirements (AI regenerates tasks)
- Must explicitly approve before implementation begins

**Stage 5: Implementation (Implementation Mode)**
- AI implements tasks sequentially following OpenSpec specifications
- For each task: generates code, runs tests, creates git commit, updates task status
- Real-time progress visible in Ardha UI

**Stage 6: Testing & Quality Assurance (Debug Mode)**
- AI runs automated test suites (unit, integration, E2E)
- Analyzes failures and generates fixes
- Re-runs tests until all pass

**Stage 7: Code Review & GitHub Integration**
- AI creates pull request with comprehensive description
- Links to OpenSpec proposal and related tasks
- Includes test results and performance metrics

**Stage 8: Deployment & Monitoring**
- After merge, AI updates OpenSpec (marks tasks done, archives change)
- Updates project roadmap
- Suggests next steps for subsequent phases

### Workflow 2: Dual Chat System

**Normal Chat Mode (General Purpose):**
- Similar to ChatGPT/Claude interface
- Two-column layout: sidebar with chat history, main area for conversation
- No project context loaded
- Use cases: general questions, brainstorming, learning, quick code snippets
- Can convert chat to project with special command

**Project Chat Mode (IDE-Integrated):**
- Three-column layout: file explorer, code editor, AI chat
- Full project context: all files, git history, tasks, OpenSpec specs
- Code editor with syntax highlighting, AI completions, inline suggestions
- Integrated terminal for running commands
- Git panel for version control operations
- Task panel showing project tasks
- OpenSpec panel displaying specifications
- Persistent conversations linked to project

### Workflow 3: Multi-Mode AI System

**Pre-built Modes:**
1. **Research Mode**: Market research, idea validation, competitive analysis
2. **Architect Mode**: PRD/ARD generation, system design, architecture decisions
3. **Implementation Mode**: Code generation, debugging, refactoring
4. **Debug Mode**: Error analysis, testing, performance optimization
5. **Documentation Mode**: README, API docs, inline comments

**Custom Modes:**
- Users can create unlimited custom modes
- Each mode has: name, icon, system prompt, temperature, available tools, context strategy
- Custom modes can be exported/imported/shared with team
- Examples: Security Audit Mode, Performance Optimization Mode, Database Migration Mode

**Mode Configuration:**
- System prompt with project variables
- Temperature control (0.0-1.0)
- Tool access permissions
- Auto-execute settings for tools
- Context strategy (minimal, selective, full)
- Memory persistence level (session, project, global)

---

## 🤖 AI Integration Strategy

### OpenRouter Multi-Model Support

**Model Selection Approach:**
- Access to 400+ AI models from multiple providers (OpenAI, Anthropic, Google, Meta, etc.)
- Auto-model selection based on task complexity
- User can manually override model choice
- Model comparison UI showing cost, performance, context window

**Complexity-Based Routing:**
- Simple tasks: GPT-4o-mini, Gemini Flash ($0.15-0.30 per 1M tokens)
- Medium tasks: Claude 3.5 Haiku, GPT-4o ($0.50-3.00 per 1M tokens)
- Complex tasks: Claude 3.5 Sonnet, GPT-4 Turbo ($3.00-15.00 per 1M tokens)
- Maximum tasks: Claude Opus, O1 ($15.00-60.00 per 1M tokens)

**Cost Tracking:**
- Real-time token usage and cost display
- Daily and monthly budget limits
- Usage breakdown by mode and model
- Cost projections and alerts
- Transparent pricing with 0% markup on AI tokens

**Prompt Caching:**
- Large static context (project files, docs) marked as cacheable
- 90% cost reduction on cached content
- 5-minute cache duration
- Automatic cache warming for frequently accessed projects

### LangGraph Workflow Orchestration

**Core Concepts:**
- Workflows modeled as directed graphs with nodes and edges
- Each node is a pure function that processes state
- Deterministic control flow (no "prompt spaghetti")
- State persisted at each node for resumption
- Human-in-the-loop approval gates

**Workflow State Management:**
- Shared state object passed through all nodes
- Includes: user input, research findings, PRD/ARD, tasks, implementation results, errors
- State stored in PostgreSQL for persistence
- Can resume workflow from any checkpoint

**Key Features:**
- Parallel execution where possible (research tasks)
- Conditional routing based on state (approval gates)
- Automatic retries with error context
- Streaming progress updates to UI via WebSocket
- LangSmith integration for observability and debugging

### Project-Based Memory System

**Memory Hierarchy:**

**Short-Term Memory (Current Session):**
- Stored in Redis (in-memory)
- Lifetime: 1-2 hours
- Contains: recent messages, active files, current task, uncommitted changes

**Long-Term Memory (Project History):**
- Stored in Qdrant (vector database)
- Lifetime: Permanent for project
- Contains: all conversations (embedded), code changes with explanations, architecture decisions, bugs fixed, patterns learned

**Organizational Memory (Cross-Project):**
- Stored in Qdrant (separate collection)
- Lifetime: Permanent organization-wide
- Contains: common patterns, team coding standards, recurring issues, estimation accuracy

**Memory Retrieval (Adaptive RAG):**
1. Semantic search using query embedding
2. Self-reflection: AI evaluates if context is sufficient
3. Multi-hop retrieval: Follow chains of related information if needed
4. Combine retrieved memories with current context

**Memory Ingestion Pipeline:**
- After every conversation: summarize, extract decisions, create embeddings, store in Qdrant
- After code commits: generate explanation, embed, link to tasks, store in Qdrant
- Continuous learning: AI improves from past successes and failures

### ACE Framework (Continuous Learning)

**Agentic Context Engineering Principles:**
- Maintain evolving "playbook" of strategies and patterns
- Learn from project outcomes and retrospectives
- Compound organizational knowledge over time
- Self-improve prompts based on success metrics

**Learning Loop:**
1. Execute task/workflow with current strategy
2. Measure outcome (tests passed, code quality, time taken)
3. Compare to estimates and past similar tasks
4. Update strategy playbook with learnings
5. Apply improved strategy to next similar task

---

## 📋 Project Management Features

### Task Management

**Task Data Model:**
- Identity: ID, project, identifier (e.g., "ARD-42"), title, description
- Status: todo, in_progress, in_review, done, cancelled
- Assignment: assignee, created by (user or AI)
- Organization: phase, milestone, epic hierarchy
- Dependencies: depends_on, blocks relationships
- Estimation: estimate hours, actual hours, complexity
- Priority: urgent, high, medium, low
- OpenSpec reference: link to change proposal
- Metadata: AI confidence, reasoning, related commits/PRs/files

**Task Views:**
1. **Board View (Kanban)**: Visual status columns with drag-and-drop
2. **List View (Table)**: Detailed data grid with sorting and filtering
3. **Calendar View**: Time-based scheduling with due dates
4. **Timeline View (Gantt)**: Project scheduling with dependencies
5. **Gallery View**: Visual card layout for design-heavy tasks

**AI-Powered Task Features:**
- Smart task generation from PRD/ARD
- Intelligent estimation based on past similar tasks
- Automatic status updates from git commits
- Dependency detection and management
- Task templates for recurring patterns

### Milestones & Roadmap

**Milestone Structure:**
- Name, description, target date
- Status: planning, active, at_risk, complete, cancelled
- Progress automatically calculated from tasks
- Owner and priority
- Visual color coding

**Roadmap View:**
- Timeline visualization showing all milestones
- Tasks grouped by milestone
- Critical path highlighting
- Progress indicators
- Risk detection and alerts

**AI-Powered Milestone Features:**
- Automatic timeline estimation based on team velocity
- Risk detection (behind schedule, blocked tasks, capacity issues)
- Recommendations for scope adjustments
- Predictive completion dates

### Databases (Notion-Style Flexible Data)

**Database Types:**
1. **Tasks Database**: Built-in task management (cannot be deleted, core feature)
2. **Resources Database**: Documents, links, files, videos
3. **Meeting Notes Database**: Agendas, notes, action items
4. **Design Assets Database**: Logos, icons, mockups, wireframes
5. **Custom Databases**: User-defined for any structured data (unlimited)

**Database CRUD Operations:**

**Create Database:**
- User clicks "+ New Database" button in project sidebar
- Modal appears with database configuration:
  - Database name (required)
  - Database icon (emoji picker)
  - Description (optional)
  - Initial properties to add (can customize later)
  - Default view type (board, list, calendar, timeline, gallery)
- On creation:
  - Database entry created in PostgreSQL
  - Default view automatically generated
  - WebSocket broadcast to all project members
  - Appears in project sidebar immediately
  - User redirected to new database

**Read/View Database:**
- Click database in sidebar to open
- Shows current view (board, list, calendar, timeline, gallery)
- View selector dropdown to switch between views
- Filter bar for querying data
- Sort controls for ordering
- All changes stream in real-time via WebSocket

**Update Database:**
- Rename database: Click title, edit inline, save automatically
- Change icon: Click icon, select from emoji picker
- Edit description: Click description area, edit, auto-save
- Add/Remove Properties:
  - Click "+" button to add new property
  - Configure: name, type, options (for select fields)
  - Click property settings → "Delete property" to remove
  - Confirmation required if property has data
- Reorder Properties: Drag-and-drop property headers
- All updates broadcast via WebSocket to collaborators

**Delete Database:**
- Click database settings (three dots menu)
- Select "Delete Database"
- Confirmation modal appears:
  - Warning: "This will permanently delete X entries"
  - Checkbox: "I understand this cannot be undone"
  - Input field: Type database name to confirm
- On confirmation:
  - Soft delete: Marked as deleted, hidden from UI
  - Hard delete after 30 days (background job)
  - All views associated with database also deleted
  - WebSocket broadcast removes from all clients
  - Restore available within 30 days from trash

**Database Properties:**
- Text: single line, rich text
- Number: numeric values with formatting options
- Selection: select, multi-select with custom colors
- Temporal: date, date+time with timezone support
- Relations: person (link to users), relation to other database
- Media: files (upload), URL (link), email, phone
- Computed: formula (custom calculations), rollup (aggregate from relations)
- Special: checkbox, created time, created by, last edited time, last edited by

**Property CRUD Operations:**

**Add Property:**
- Click "+ Add Property" button in database view
- Property configuration modal:
  - Property name (e.g., "Status", "Priority", "Due Date")
  - Property type (dropdown with all types)
  - Type-specific settings:
    - Select: Define options (name, color)
    - Formula: Enter formula expression
    - Relation: Choose target database
    - Rollup: Choose relation property, target property, function
- On creation:
  - Column added to all views
  - Default value applied to existing entries (null/empty)
  - WebSocket broadcast to all viewers

**Edit Property:**
- Click property header → "Edit Property"
- Can change: name, type-specific settings
- Cannot change: property type after creation (must delete and recreate)
- For select properties: Add/edit/delete options
- For formula properties: Update formula expression
- Changes apply to all entries immediately

**Delete Property:**
- Click property header → "Delete Property"
- Confirmation dialog:
  - Warning if property contains data
  - Option to export data before deletion
- On confirmation:
  - Property removed from all entries
  - Property removed from all views
  - Cannot be undone (unless restore from backup)

**Dynamic Update Mechanisms:**

**1. Real-Time Sync (WebSocket):**
- Every database operation broadcasts to all connected clients
- Optimistic updates: UI updates immediately, then confirms with server
- Conflict resolution: Last-write-wins with user notification
- Presence indicators: Show who is viewing/editing

**2. Automatic Status Updates:**
- Git commit detection: Parse commit messages for task references
- Update task status based on commit type (feat/fix/test)
- Link commits to related database entries
- Broadcast status changes to all viewers

**3. AI-Powered Auto-Fill:**
- Task estimates: AI predicts hours based on description and past tasks
- URL metadata: Extract title, description, thumbnail from pasted URLs
- Action items: Extract from meeting notes and create linked tasks
- Tags: Suggest relevant tags based on content analysis

**4. Formula & Rollup Auto-Calculation:**
- Formula recalculation: Triggered on any referenced property change
- Rollup recalculation: Triggered when related entries change
- Batch processing: Multiple changes processed efficiently
- Real-time display: Updated values appear immediately in UI

**5. Database View Synchronization:**
- All views of same database share data (single source of truth)
- View-specific settings: Filters, sorts, groups, visible fields
- User-specific views: Private views for personal organization
- Shared views: Team views visible to all project members

**Database Migration on Delete:**
- When database deleted, related data handling:
  - Relations from other databases: Set to null or show as "Deleted Database"
  - Rollups referencing deleted database: Show error state
  - Formulas referencing deleted database: Show #REF error
  - Option to migrate entries to another database before deletion

**Performance Optimization:**
- Pagination: Load 50 entries at a time, infinite scroll
- Virtual scrolling: Render only visible entries in large tables
- Lazy loading: Load property values on demand for heavy fields (files, rich text)
- Caching: Redis cache for frequently accessed databases
- Indexing: PostgreSQL indexes on commonly filtered/sorted fields

---

## 🔧 Technical Stack

### Frontend Technologies
- **Framework**: Next.js 15 (App Router, React 19)
- **Language**: TypeScript 5.3+
- **State Management**: Zustand
- **UI Library**: shadcn/ui (built on Radix UI primitives)
- **Styling**: Tailwind CSS with custom design tokens
- **Animation**: Framer Motion
- **Icons**: Lucide React
- **Code Editor**: CodeMirror 6
- **Terminal**: xterm.js
- **Real-Time Collaboration**: Yjs (CRDT)
- **Data Fetching**: TanStack Query (React Query), SWR

### Backend Technologies
- **Framework**: FastAPI 0.110+ (Python 3.11)
- **Dependency Management**: Poetry
- **Validation**: Pydantic v2
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Database Driver**: asyncpg (PostgreSQL)
- **Cache Client**: redis-py (async)
- **AI Orchestration**: LangGraph
- **AI Client**: OpenAI SDK (OpenRouter compatible)
- **Vector Search**: Qdrant-client
- **Embeddings**: Sentence-Transformers
- **Authentication**: python-jose (JWT), passlib (password hashing)
- **Background Tasks**: Celery with Celery Beat
- **Testing**: pytest, pytest-asyncio, httpx

### Database Technologies
- **Relational**: PostgreSQL 15 with specific tuning for 8GB RAM
- **Vector**: Qdrant v1.7.4 with scalar quantization for memory efficiency
- **Cache**: Redis 7 with LRU eviction policy

### Infrastructure Technologies
- **Containerization**: Docker with docker-compose
- **Reverse Proxy**: Caddy (automatic HTTPS)
- **Version Control**: Git with GitHub integration
- **Monitoring**: Prometheus + Grafana (optional)
- **Logging**: Loki (optional)

### Locked Dependencies & Versions

**Critical Note**: All dependencies must be locked to specific versions to ensure reproducible builds and prevent breaking changes. Use exact versions in package.json and pyproject.toml.

**Frontend Dependencies (package.json):**

**Core Framework:**
```json
{
  "next": "15.0.2",
  "react": "19.0.0",
  "react-dom": "19.0.0",
  "typescript": "5.3.3"
}
```

**State & Data:**
```json
{
  "zustand": "4.4.7",
  "@tanstack/react-query": "5.17.9",
  "swr": "2.2.4"
}
```

**UI Components:**
```json
{
  "@radix-ui/react-alert-dialog": "1.0.5",
  "@radix-ui/react-dialog": "1.0.5",
  "@radix-ui/react-dropdown-menu": "2.0.6",
  "@radix-ui/react-popover": "1.0.7",
  "@radix-ui/react-select": "2.0.0",
  "@radix-ui/react-tabs": "1.0.4",
  "@radix-ui/react-tooltip": "1.0.7",
  "tailwindcss": "3.4.1",
  "class-variance-authority": "0.7.0",
  "clsx": "2.1.0",
  "tailwind-merge": "2.2.0",
  "framer-motion": "10.18.0",
  "lucide-react": "0.303.0"
}
```

**Code Editor & Terminal:**
```json
{
  "codemirror": "6.0.1",
  "@uiw/react-codemirror": "4.21.21",
  "@codemirror/lang-javascript": "6.2.1",
  "@codemirror/lang-python": "6.1.4",
  "@codemirror/lang-html": "6.4.7",
  "@codemirror/lang-css": "6.2.1",
  "@codemirror/lang-json": "6.0.1",
  "@codemirror/lang-markdown": "6.2.4",
  "@codemirror/theme-one-dark": "6.1.2",
  "xterm": "5.3.0",
  "xterm-addon-fit": "0.8.0",
  "xterm-addon-web-links": "0.9.0"
}
```

**Real-Time:**
```json
{
  "yjs": "13.6.10",
  "y-websocket": "1.5.0",
  "y-codemirror.next": "0.3.5"
}
```

**Forms & Validation:**
```json
{
  "react-hook-form": "7.49.3",
  "zod": "3.22.4",
  "@hookform/resolvers": "3.3.4"
}
```

**Utilities:**
```json
{
  "date-fns": "3.0.6",
  "lodash": "4.17.21",
  "nanoid": "5.0.4",
  "slugify": "1.6.6"
}
```

**Backend Dependencies (pyproject.toml):**

**Core:**
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "0.110.0"
uvicorn = {extras = ["standard"], version = "0.27.0"}
pydantic = "2.6.0"
pydantic-settings = "2.1.0"
```

**Database - PostgreSQL:**
```toml
sqlalchemy = {extras = ["asyncio"], version = "2.0.25"}
asyncpg = "0.29.0"
alembic = "1.13.1"
psycopg2-binary = "2.9.9"
```

**Database - Redis:**
```toml
redis = {extras = ["hiredis"], version = "5.0.1"}
hiredis = "2.3.2"
```

**Database - Qdrant:**
```toml
qdrant-client = "1.7.3"
```

**AI & LLM:**
```toml
openai = "1.10.0"
langchain = "0.1.4"
langchain-openai = "0.0.5"
langgraph = "0.0.20"
sentence-transformers = "2.3.1"
```

**Authentication:**
```toml
python-jose = {extras = ["cryptography"], version = "3.3.0"}
passlib = {extras = ["bcrypt"], version = "1.7.4"}
bcrypt = "4.1.2"
```

**Background Tasks:**
```toml
celery = {extras = ["redis"], version = "5.3.4"}
flower = "2.0.1"
```

**Utilities:**
```toml
python-dotenv = "1.0.0"
httpx = "0.26.0"
tenacity = "8.2.3"
python-slugify = "8.0.1"
python-dateutil = "2.8.2"
pytz = "2023.3"
gitpython = "3.1.41"
```

**Infrastructure Versions:**

**Docker Images:**
```yaml
postgres: postgres:15.5-alpine
qdrant: qdrant/qdrant:v1.7.4
redis: redis:7.2-alpine
python: python:3.11.7-slim
node: node:20.10.0-alpine
caddy: caddy:2.7-alpine
```

**Development Tools:**
- Docker: >=24.0.0
- Docker Compose: >=2.20.0
- Node.js: 20.10.0 LTS
- Python: 3.11.7
- Poetry: 1.7.0
- Git: >=2.40.0

---

## 📁 Project Structure

### Repository Organization
- Monorepo structure with separate frontend and backend directories
- Shared types and utilities where appropriate
- OpenSpec directory at project root

### Frontend Directory Structure
- App Router pages in `app/` directory
- Reusable components in `components/`
- Custom hooks in `hooks/`
- Zustand stores in `stores/`
- API client and utilities in `lib/`
- TypeScript types in `types/`

### Backend Directory Structure
- API routes in `app/api/v1/`
- SQLAlchemy models in `app/models/`
- Pydantic schemas in `app/schemas/`
- Business logic in `app/services/`
- LangGraph workflows in `app/workflows/`
- Core utilities in `app/core/`
- Database setup in `app/db/`
- Alembic migrations in `app/migrations/`

### OpenSpec Directory Structure
- Current specifications in `openspec/specs/`
- Proposed changes in `openspec/changes/`
- Archived changes in `openspec/archive/`
- AI agent instructions in `openspec/AGENTS.md`

---

## 🔐 Security & Authentication

### Authentication Strategy
- Multi-provider OAuth2: Email/Password, GitHub, Google
- JWT access tokens (15 minute expiry)
- Refresh tokens (7 day expiry, httpOnly cookie)
- Token rotation on each refresh

### Role-Based Access Control (RBAC)
- **Owner**: Full control, can delete project
- **Admin**: Manage team and settings (cannot delete)
- **Member**: Read/write tasks, code, chat
- **Viewer**: Read-only access

### Security Best Practices
- Input validation using Pydantic
- SQL injection prevention via ORM
- Rate limiting on API endpoints
- CORS configuration for allowed origins
- Environment variables for secrets (never hardcoded)
- Password hashing with bcrypt (cost factor 12)
- XSS prevention through content sanitization

---

## 🎯 OpenSpec Integration

### OpenSpec Workflow in Ardha

**Ardha's Custom OpenSpec Implementation:**
- OpenSpec provides the framework for spec-driven development
- Ardha adds visual UI layer on top of OpenSpec markdown files
- Auto-syncs OpenSpec tasks to PostgreSQL database for tracking
- Git commits automatically update OpenSpec task status
- Automated archival when all tasks in a change are complete

**File Structure:**
- `openspec/specs/`: Source of truth specifications (current state)
- `openspec/changes/<change-name>/`: Proposed changes awaiting approval
  - `proposal.md`: Summary of what and why
  - `tasks.md`: Detailed task breakdown with dependencies
  - `spec-delta.md`: Specification updates to merge after completion
- `openspec/archive/`: Completed and archived changes

**Workflow Stages:**
1. **Proposal Creation**: AI generates OpenSpec files in changes directory
2. **Human Review**: User reviews proposal in Ardha UI (not just markdown)
3. **Approval & Sync**: User approves, Ardha syncs tasks to database
4. **Implementation**: AI implements tasks, updates both database and markdown
5. **Archival**: Completed change moves to archive, spec updates merge to specs

**Key Differences from Standard OpenSpec:**
- Visual approval UI instead of command-line only
- Real-time task status in web interface
- Database persistence for task tracking
- WebSocket updates for collaborative editing
- Integrated with project chat and memory systems

---

## 🎨 User Interface Components

### Core UI Components

**Buttons**: Primary, secondary, ghost, danger variants with consistent states
**Inputs**: Text, number, select, multi-select with validation
**Cards**: Elevation, borders, hover effects for content grouping
**Modals/Dialogs**: Overlay with backdrop blur for focused interactions
**Dropdowns/Menus**: Context menus and action dropdowns
**Badges/Tags**: Status indicators and labels
**Toast Notifications**: Success, error, warning, info messages
**Avatars**: User profile images with fallback initials
**Loading States**: Spinners, skeletons, progress bars
**AI-Specific Components**: AI chat bubbles, thinking indicators, AI badges

### Layout Components

**Command Palette (Cmd+K)**: Universal search and action execution
**Sidebar**: Navigation for projects, chats, settings
**Header**: Project/chat title, mode selector, user menu
**File Tree**: Hierarchical file explorer for projects
**Code Editor**: Syntax-highlighted editing with AI completions
**Terminal**: Integrated shell for commands
**Git Panel**: View changes, stage, commit, push
**Task Board**: Kanban columns with drag-and-drop
**Calendar**: Time-based view with event scheduling
**Timeline**: Gantt-style project scheduling

---

## 📊 Data Models

### Core Entities

**User**
- Authentication: email, username, password hash
- OAuth: GitHub ID, Google ID
- Profile: full name, avatar URL
- Settings: preferences stored as JSON
- Timestamps: created, updated, last login

**Project**
- Identity: name, description, slug
- Ownership: owner user, team members
- Settings: visibility (private/team/public), tech stack
- Repository: git repo URL, branch
- OpenSpec: enabled flag, path to openspec directory
- Timestamps: created, updated, archived

**Task**
- Identity: ID, project, identifier (ARD-42), title, description
- Status: todo, in_progress, in_review, done, cancelled
- Assignment: assignee, created by (user or AI)
- Organization: phase, milestone, epic
- Estimation: estimate hours, actual hours, complexity
- Priority: urgent, high, medium, low
- Relationships: dependencies (depends_on, blocks)
- OpenSpec: reference to change directory
- AI metadata: generated by AI flag, confidence score, reasoning
- Related: commits, PRs, files
- Timestamps: created, updated, started, completed, due date

**Chat**
- Identity: ID, project (optional), title
- Type: normal (standalone) or project (integrated)
- Owner: user who created chat
- Mode: current AI mode (research, architect, implementation, etc.)
- Timestamps: created, updated

**Message**
- Identity: ID, chat
- Role: user, assistant, system
- Content: message text
- Metadata: model used, tokens, cost, additional data as JSON
- Timestamp: created

**Milestone**
- Identity: ID, project, name, description
- Dates: target date, started, completed
- Status: planning, active, at_risk, complete, cancelled
- Metadata: priority, color, owner
- Progress: auto-calculated from tasks
- Timestamps: created, updated

**File**
- Identity: ID, project, path, name, extension
- Type: code, doc, config, test
- Content: for small files, stored directly
- Metadata: size, language
- Git: last commit SHA, last modified by
- Timestamps: created, updated

**Project Member**
- Identity: ID, project, user
- Role: owner, admin, member, viewer
- Timestamp: joined date

**OpenSpec Proposal**
- Identity: ID, project, change name, directory path
- Content: proposal text, tasks text, spec delta text
- Status: pending, approved, rejected, archived
- Approval: approved by user, approved timestamp
- Timestamps: created, updated

### Data Relationships

- User → Projects (many-to-many via project_members)
- Project → Tasks (one-to-many)
- Project → Chats (one-to-many)
- Project → Files (one-to-many)
- Project → Milestones (one-to-many)
- Task → Task Dependencies (many-to-many self-referential)
- Task → Tags (many-to-many)
- Chat → Messages (one-to-many)
- Milestone → Tasks (one-to-many)

---

## 🚀 Development Conventions

### Code Quality Standards
- TypeScript strict mode enabled on frontend
- Python type hints required on backend
- Minimum 80% test coverage for new features
- All API endpoints must have OpenAPI documentation
- All components must have accessibility attributes

### Git Workflow
- Feature branches from main
- Conventional commit messages
- Pull requests required for main branch
- Minimum one approval before merge
- CI/CD checks must pass (linting, tests, build)

### Testing Strategy
- Unit tests for business logic
- Integration tests for API endpoints
- End-to-end tests for critical user flows
- Visual regression testing for UI components
- Load testing for performance-critical endpoints

### Documentation Requirements
- README for each major module
- API documentation auto-generated from OpenAPI spec
- Component documentation with examples
- Architecture decision records (ADRs) for major decisions
- User guides for key features

### Performance Guidelines
- Frontend bundle size monitoring
- Database query optimization (N+1 prevention)
- API response time monitoring
- Memory usage profiling
- Rate limiting for expensive operations

---

## 📈 Success Metrics

### Technical Performance Metrics
- Page load time: <2 seconds (90th percentile)
- API response time: <500ms (95th percentile)
- Initial bundle size: <200KB gzipped
- Time to Interactive: <3 seconds
- 99% uptime
- <0.1% error rate
- Zero data loss incidents

### AI Quality Metrics
- Task generation accuracy: >80%
- Code implementation success rate: >70%
- Average AI cost per project: <$5
- AI response relevance: >90% (user satisfaction)

### User Adoption Metrics
- GitHub stars: 1,000 at MVP (4 months)
- Monthly active users: 100 at MVP
- Projects created: 100 at MVP
- PRs generated by AI: 50 at MVP
- AI messages sent: 10,000 at MVP

### 6-Month Goals
- 5,000 GitHub stars
- 1,000 monthly active users
- 500 active projects
- $100K total AI usage volume

### 12-Month Goals
- 15,000 GitHub stars
- 10,000 monthly active users
- 5,000 active projects
- $1M total AI usage volume
- 500+ community contributors

---

## 🎓 Domain Concepts

### Key Terminology

**AI Mode**: A specialized AI assistant configuration with specific system prompt, tools, and context strategy (e.g., Research Mode, Implementation Mode)

**OpenSpec Proposal**: A structured change request containing proposal summary, task breakdown, and specification updates

**Spec Delta**: A markdown file showing additions, modifications, and removals to specifications

**Task Dependency**: Relationship where one task must complete before another can start (blocks/depends_on)

**Project Context**: The complete state of a project including files, git history, tasks, and specifications that AI can reference

**Memory System**: Three-tier system (short-term Redis, long-term Qdrant project memories, organizational patterns) for AI context

**LangGraph Workflow**: Deterministic AI workflow represented as a directed graph with state management

**Prompt Caching**: Technique to mark large static context as cacheable, reducing AI costs by 90% on repeated requests

**Complexity-Based Routing**: Automatic selection of AI model based on task difficulty to optimize cost vs quality

**ACE Framework**: Agentic Context Engineering - continuous learning system where AI improves from past outcomes

**CRDT**: Conflict-free Replicated Data Type - enables multiple users to edit simultaneously without conflicts

**Vector Embedding**: High-dimensional numerical representation of text for semantic similarity search

**Semantic Search**: Finding relevant information based on meaning rather than keyword matching

**RAG (Retrieval-Augmented Generation)**: AI technique that retrieves relevant context before generating responses

**Multi-Hop Retrieval**: Following chains of related information across multiple searches to gather complete context

---

## 🚀 Quick Start (5 Minutes)

**For Users Who Want to Try Ardha:**

```bash
# Prerequisites: Docker and Docker Compose installed

# 1. Clone the repository
git clone https://github.com/yourusername/ardha.git
cd ardha

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env - Add your OpenRouter API key (required)
# OPENROUTER_API_KEY=your_key_here
nano .env

# 4. Start all services
docker-compose up -d

# 5. Wait 30 seconds for services to initialize

# 6. Open your browser
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs

# 7. Create your first account and start building!
```

**That's it!** You're ready to use Ardha.

**Common Issues:**
- "Port already in use" → Change ports in docker-compose.yml
- "API key error" → Verify OPENROUTER_API_KEY in .env
- "Database error" → Run `docker-compose down -v` then `docker-compose up -d`

**Get Help:** [Discord](https://discord.gg/ardha) | [Discussions](https://github.com/yourusername/ardha/discussions)

---

## 🔀 Git Workflow & Development Process

### Branch Strategy (For Solo Developer with AI Assistance)

**Three-Branch Model:**

```
main (production-ready)
  ↑
  merge after thorough testing
  ↑
develop (integration branch)
  ↑
  merge when feature complete
  ↑
feature/* (work branches)
```

**Branch Descriptions:**

**1. main Branch**
- **Purpose**: Production-ready code only
- **Protection**:
  - Requires passing CI/CD
  - Requires all tests passing
  - Manual final review before merge
- **Deployments**: Auto-deploy to production (future hosted version)
- **Tags**: Semantic versioning (v1.0.0, v1.1.0, etc.)
- **Never commit directly** - always via PR from develop

**2. develop Branch**
- **Purpose**: Integration branch for completed features
- **Testing**: All integration and E2E tests must pass
- **Stability**: Should always be in a working state
- **Merge frequency**: After each feature completion
- **Protection**: Requires passing CI/CD
- **Use for**: Testing multiple features together before production

**3. feature/* Branches**
- **Purpose**: Individual feature development
- **Naming convention**:
  - `feature/auth-system` - New features
  - `feature/task-board` - UI components
  - `feature/openspec-integration` - Major integrations
  - `bugfix/fix-login-error` - Bug fixes
  - `refactor/optimize-queries` - Code improvements
  - `docs/api-documentation` - Documentation updates
- **Lifetime**: Created from develop, deleted after merge
- **Commits**: Can be messy, will be squashed on merge
- **Testing**: Unit tests must pass before merge

**Workflow Example:**

```bash
# Starting a new feature
git checkout develop
git pull origin develop
git checkout -b feature/chat-interface

# Work on feature (multiple commits)
git add .
git commit -m "feat: add chat message component"
git add .
git commit -m "feat: add chat input with emoji picker"
git add .
git commit -m "test: add chat component tests"

# Push to GitHub
git push origin feature/chat-interface

# Create PR: feature/chat-interface → develop
# - GitHub Actions runs tests
# - Review code yourself (or with AI assistance)
# - Merge with "Squash and merge"

# After merge, sync develop
git checkout develop
git pull origin develop

# Delete feature branch
git branch -d feature/chat-interface
git push origin --delete feature/chat-interface

# When develop is stable and tested
# Create PR: develop → main
# - Full E2E test suite runs
# - Manual final verification
# - Merge with "Create a merge commit" (preserve history)

# Tag release on main
git checkout main
git pull origin main
git tag -a v1.0.0 -m "Release version 1.0.0 - MVP"
git push origin v1.0.0
```

### Commit Message Convention

**Use Conventional Commits format:**

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, semicolons, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvement

**Examples:**
```
feat(auth): implement GitHub OAuth login

- Add GitHub OAuth strategy
- Create callback handler
- Update user model with github_id
- Add tests for OAuth flow

Closes #23

---

fix(tasks): prevent duplicate task IDs

Task identifiers were not unique across projects.
Added compound unique constraint on (project_id, identifier).

Fixes #45

---

docs(readme): add Docker installation instructions

Added step-by-step guide for Docker-based installation.
Includes troubleshooting section for common issues.

---

test(api): increase coverage for task endpoints

Added integration tests for:
- Task creation with dependencies
- Task status updates
- Task deletion with cascade

Coverage increased from 78% to 92%.
```

### Solo Developer + AI Workflow

**Your Development Environment:**
- **Primary IDE**: Kilo Code (for AI-assisted development)
- **AI Assistants**:
  - Kilo Code: For feature implementation, code generation
  - Claude (me): For architecture decisions, complex problem-solving, documentation
- **Testing**: Local pytest, Vitest, Playwright
- **Git**: Command line or Kilo Code's Git integration

**Daily Workflow:**

**Morning (2-3 hours):**
1. Review yesterday's progress
2. Check CI/CD status
3. Plan today's tasks (1-2 features max)
4. Create feature branch
5. Start implementation with AI assistance

**Afternoon (3-4 hours):**
6. Continue feature development
7. Write tests as you go
8. Run local test suite
9. Fix any failing tests
10. Push to GitHub

**Evening (1-2 hours):**
11. Review code with AI
12. Update documentation
13. Create PR to develop
14. Plan tomorrow's work

**Weekly Cycle:**
- **Monday-Thursday**: Feature development
- **Friday**: Testing, bug fixes, PR reviews, merge to develop
- **Saturday**: Optional - Refactoring, optimization
- **Sunday**: Rest (no coding!)

### AI-Assisted Development Tips

**When to Use Kilo Code:**
- Implementing API endpoints
- Creating database models
- Writing tests
- Refactoring code
- Debugging errors
- Generating boilerplate

**When to Use Claude (Me):**
- Architecture decisions
- Complex algorithm design
- Documentation writing
- Problem troubleshooting
- Code review feedback
- Planning multi-file changes

**Workflow with AI:**
```bash
# 1. Start with plan
> Ask Claude: "I'm implementing user authentication. What's the best approach?"

# 2. Use Kilo Code for implementation
> Ask Kilo Code: "Implement JWT authentication with the plan discussed"

# 3. Generate tests with AI
> Ask Kilo Code: "Generate pytest tests for auth endpoints"

# 4. Review with Claude
> Ask Claude: "Review this auth implementation for security issues"

# 5. Document with AI
> Ask Kilo Code: "Add docstrings to all auth functions"
```

### GitHub Repository Setup

**Repository Structure:**
```
ardha/
├── .github/
│   ├── workflows/
│   │   ├── backend-tests.yml      # Backend CI
│   │   ├── frontend-tests.yml     # Frontend CI
│   │   └── deploy.yml             # Deployment (future)
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── question.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── FUNDING.yml                # GitHub Sponsors
├── backend/
├── frontend/
├── openspec/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── LICENSE (MIT)
├── README.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
└── CHANGELOG.md
```

**Branch Protection Rules:**

**For `main` branch:**
```yaml
Required:
  - Require pull request before merging
  - Require status checks to pass
    ✓ Backend tests
    ✓ Frontend tests
    ✓ E2E tests
    ✓ Linting
  - Require conversation resolution before merging
  - Do not allow bypassing the above settings

Optional:
  - Require signed commits (recommended)
  - Include administrators (apply to you too)
```

**For `develop` branch:**
```yaml
Required:
  - Require pull request before merging
  - Require status checks to pass
    ✓ Backend tests
    ✓ Frontend tests

Allowed:
  - Can force push if needed (you're solo)
  - Can bypass for hotfixes
```

### GitHub Actions CI/CD

**Backend Tests (.github/workflows/backend-tests.yml):**
```yaml
name: Backend Tests

on:
  push:
    branches: [main, develop, 'feature/**']
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Poetry
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          echo "$HOME/.local/bin" >> $GITHUB_PATH

      - name: Install dependencies
        run: |
          cd backend
          poetry install

      - name: Run linters
        run: |
          cd backend
          poetry run black --check .
          poetry run isort --check .
          poetry run mypy .

      - name: Run tests
        run: |
          cd backend
          poetry run pytest --cov=app --cov-report=xml
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
```

**Frontend Tests (.github/workflows/frontend-tests.yml):**
```yaml
name: Frontend Tests

on:
  push:
    branches: [main, develop, 'feature/**']
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: |
          cd frontend
          npm ci

      - name: Run linters
        run: |
          cd frontend
          npm run lint

      - name: Run type check
        run: |
          cd frontend
          npm run type-check

      - name: Run tests
        run: |
          cd frontend
          npm run test:coverage

      - name: Build
        run: |
          cd frontend
          npm run build

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./frontend/coverage/coverage-final.json
```

### Issue and PR Templates

**Bug Report Template (.github/ISSUE_TEMPLATE/bug_report.md):**
```markdown
---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '...'
3. Scroll down to '...'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment (please complete the following information):**
 - OS: [e.g. macOS, Ubuntu 22.04]
 - Browser [e.g. chrome, firefox]
 - Version [e.g. 1.0.0]
 - Installation method: [Docker / Native]

**Additional context**
Add any other context about the problem here.

**Logs**
Please attach relevant logs (backend/frontend).
```

**Pull Request Template (.github/PULL_REQUEST_TEMPLATE.md):**
```markdown
## Description
Brief description of the changes in this PR.

## Type of change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## How Has This Been Tested?
Describe the tests you ran to verify your changes.

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] E2E tests pass (if applicable)
- [ ] Manual testing completed

## Checklist:
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Screenshots (if applicable):
Add screenshots to help reviewers understand your changes.

## Related Issues:
Closes #(issue number)
```

---

## 📚 Documentation Structure

### MVP Philosophy (4-Month Timeline)
- Focus on core end-to-end workflow: Idea → PRD → Tasks → Implementation
- Beautiful but minimal UI (Linear-inspired aesthetics)
- Essential features only: dual chat, task board, OpenSpec integration, Git basics
- No mobile apps, advanced analytics, or complex integrations in MVP
- Ship fast, gather feedback, iterate

### Backend-First Development Strategy

**Why Backend First:**
1. **Database Schema Foundation**: Establish stable data models before UI
2. **API Contract Definition**: Frontend can develop against mock data/Swagger
3. **AI Integration Core**: LangGraph workflows need solid API foundation
4. **Testing Efficiency**: Backend tests run faster, catch more critical bugs
5. **Parallel Development**: Once APIs defined, frontend team can work in parallel

**Development Phases (Sequential):**

---

**Phase 1: Backend Foundation (Weeks 1-3)**

**Objectives:**
- Setup project infrastructure
- Implement core database schema
- Create authentication system
- Build basic API endpoints
- Setup testing framework

**Deliverables:**

**Week 1: Infrastructure Setup**
- Initialize Poetry project with locked dependencies
- Setup Docker Compose (PostgreSQL, Redis, Qdrant)
- Configure FastAPI application structure
- Setup Alembic for database migrations
- Create .env configuration with environment variables
- Setup pytest with fixtures
- Configure pre-commit hooks (black, isort, mypy, pylint)
- Setup CI/CD pipeline (GitHub Actions)

**Tasks:**
- Create backend directory structure
- Install all locked dependencies
- Configure SQLAlchemy async engine
- Create base database models
- Write initial Alembic migration
- Setup Redis connection pool
- Setup Qdrant client
- Configure logging (structured JSON logs)

**Week 2: Authentication & User Management**
- Implement JWT token generation and validation
- Create OAuth2 password flow
- Implement GitHub OAuth integration
- Implement Google OAuth integration
- Create user registration endpoint
- Create user login endpoint
- Create token refresh endpoint
- Implement password hashing with bcrypt
- Create user profile CRUD endpoints

**Database Models:**
- User model with fields
- OAuth connection model
- Session model (if needed)

**API Endpoints:**
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
- GET /api/v1/auth/me
- PATCH /api/v1/users/me
- POST /api/v1/auth/oauth/github
- POST /api/v1/auth/oauth/google

**Week 3: Core Project & Task Models**
- Implement Project model with relationships
- Implement Task model with dependencies
- Implement Milestone model
- Implement project member permissions
- Create project CRUD endpoints
- Create task CRUD endpoints
- Create milestone CRUD endpoints
- Implement task dependency logic

**Database Models:**
- Project model
- Task model
- Task dependencies model
- Task tags model
- Task activity model
- Milestone model
- Project member model

**API Endpoints:**
- GET /api/v1/projects
- POST /api/v1/projects
- GET /api/v1/projects/{id}
- PATCH /api/v1/projects/{id}
- DELETE /api/v1/projects/{id}
- GET /api/v1/projects/{project_id}/tasks
- POST /api/v1/projects/{project_id}/tasks
- GET /api/v1/tasks/{id}
- PATCH /api/v1/tasks/{id}
- DELETE /api/v1/tasks/{id}
- POST /api/v1/tasks/{id}/dependencies

**Testing Requirements (Phase 1):**
- Unit tests for authentication logic (100% coverage)
- Unit tests for JWT token handling
- Unit tests for password hashing
- Integration tests for all auth endpoints
- Integration tests for project CRUD
- Integration tests for task CRUD
- Integration tests for task dependencies
- Test database fixtures
- Mock external OAuth providers
- Minimum 85% overall code coverage

**Exit Criteria Phase 1:**
- [ ] All database migrations run successfully
- [ ] All tests pass (85%+ coverage)
- [ ] Authentication flow works end-to-end
- [ ] Projects and tasks can be created via API
- [ ] OpenAPI documentation generated
- [ ] Docker Compose stack runs without errors
- [ ] CI/CD pipeline passes all checks

---

**Phase 2: AI Integration & LangGraph (Weeks 4-6)**

**Objectives:**
- Integrate OpenRouter client
- Implement basic chat functionality
- Create LangGraph workflow foundation
- Implement embedding and vector search
- Setup memory system

**Deliverables:**

**Week 4: OpenRouter & Chat Foundation**
- Setup OpenRouter client with retry logic
- Implement model selection logic
- Create chat model with messages
- Implement chat CRUD endpoints
- Create message streaming endpoint
- Implement token tracking
- Implement cost calculation
- Create cost limit enforcement

**Database Models:**
- Chat model
- Message model
- AI usage tracking model

**API Endpoints:**
- GET /api/v1/chats
- POST /api/v1/chats
- GET /api/v1/chats/{id}
- POST /api/v1/chats/{id}/messages
- GET /api/v1/chats/{id}/messages
- DELETE /api/v1/chats/{id}
- WS /api/v1/chats/{id}/ws (WebSocket)
- GET /api/v1/ai/models
- GET /api/v1/ai/usage

**Week 5: LangGraph Workflows**
- Create LangGraph state definition
- Implement basic workflow nodes
- Create research workflow (Idea → Research)
- Create PRD generation workflow
- Create task generation workflow
- Implement workflow state persistence
- Create workflow checkpoint system
- Add workflow streaming to WebSocket

**Services:**
- AIService: OpenRouter client wrapper
- LangGraphService: Workflow orchestration
- WorkflowStateManager: Checkpoint management

**Week 6: Memory & Vector Search**
- Implement embedding generation service
- Setup Qdrant collections
- Create memory ingestion pipeline
- Implement semantic search
- Create memory retrieval service
- Implement short-term memory (Redis)
- Implement long-term memory (Qdrant)
- Create memory summarization

**Services:**
- EmbeddingService: Text → vectors
- MemoryService: CRUD for memories
- SemanticSearchService: Query Qdrant
- MemoryIngestionService: Background job

**Testing Requirements (Phase 2):**
- Unit tests for OpenRouter client
- Unit tests for LangGraph nodes
- Unit tests for workflow state management
- Unit tests for embedding generation
- Integration tests for chat endpoints
- Integration tests for workflows (mocked AI responses)
- Integration tests for memory CRUD
- Mock OpenRouter API responses
- Test workflow checkpoints and resumption
- Minimum 80% coverage for new code

**Exit Criteria Phase 2:**
- [ ] Chat messages can be sent and received
- [ ] AI responds via OpenRouter successfully
- [ ] Basic LangGraph workflow completes
- [ ] Embeddings generated and stored in Qdrant
- [ ] Semantic search returns relevant results
- [ ] Memory ingestion pipeline processes chats
- [ ] All tests pass (80%+ coverage)
- [ ] WebSocket streaming works for chat

---

**Phase 3: OpenSpec Integration & Git (Weeks 7-9)**

**Objectives:**
- Implement OpenSpec proposal management
- Create Git integration service
- Build file management system
- Implement task-commit linking
- Create GitHub PR automation

**Deliverables:**

**Week 7: OpenSpec Integration**
- Create OpenSpec proposal model
- Implement proposal file parsing
- Create proposal CRUD endpoints
- Implement proposal approval workflow
- Create task sync from OpenSpec
- Implement proposal archival
- Create spec delta application

**Database Models:**
- OpenSpec proposal model

**API Endpoints:**
- GET /api/v1/projects/{project_id}/openspec
- POST /api/v1/projects/{project_id}/openspec/proposals
- GET /api/v1/openspec/proposals/{id}
- PATCH /api/v1/openspec/proposals/{id}/approve
- POST /api/v1/openspec/proposals/{id}/archive
- GET /api/v1/openspec/proposals/{id}/tasks

**Services:**
- OpenSpecService: Parse markdown files
- ProposalService: CRUD operations
- TaskSyncService: OpenSpec → Database

**Week 8: Git Integration**
- Implement Git repository initialization
- Create file read/write operations
- Implement git status endpoint
- Create git commit endpoint
- Implement git push/pull
- Create branch management
- Implement commit history
- Add git diff viewer

**Database Models:**
- File model
- Git commit reference model

**API Endpoints:**
- GET /api/v1/projects/{project_id}/files
- GET /api/v1/files/{id}/content
- PATCH /api/v1/files/{id}/content
- GET /api/v1/projects/{project_id}/git/status
- POST /api/v1/projects/{project_id}/git/commit
- POST /api/v1/projects/{project_id}/git/push
- GET /api/v1/projects/{project_id}/git/branches
- GET /api/v1/projects/{project_id}/git/history

**Services:**
- GitService: GitPython wrapper
- FileService: File CRUD operations
- CommitParser: Extract task IDs from commits

**Week 9: GitHub Integration & Automation**
- Setup GitHub API client
- Implement PR creation
- Implement PR status webhook
- Create automatic task status updates from commits
- Implement commit-task linking
- Create PR template generation
- Add CI/CD status reporting

**API Endpoints:**
- POST /api/v1/projects/{project_id}/github/pr
- GET /api/v1/projects/{project_id}/github/prs
- POST /api/v1/webhooks/github (webhook receiver)

**Services:**
- GitHubService: GitHub API client
- PRService: Pull request management
- WebhookService: Process GitHub webhooks

**Testing Requirements (Phase 3):**
- Unit tests for OpenSpec parsing
- Unit tests for Git operations
- Unit tests for GitHub API client
- Integration tests for OpenSpec endpoints
- Integration tests for Git endpoints
- Integration tests for webhook processing
- Mock GitHub API responses
- Test file read/write operations
- Test commit-task linking logic
- Minimum 80% coverage for new code

**Exit Criteria Phase 3:**
- [ ] OpenSpec proposals can be created and parsed
- [ ] Tasks sync from OpenSpec to database
- [ ] Git operations work (commit, push, pull)
- [ ] Files can be read and written via API
- [ ] GitHub PRs can be created from backend
- [ ] Commits automatically update task status
- [ ] All tests pass (80%+ coverage)
- [ ] Git integration works with real repositories

---

**Phase 4: Database Management & Background Jobs (Weeks 10-12)**

**Objectives:**
- Implement Notion-style database system
- Create database view management
- Setup Celery background tasks
- Implement notification system
- Create scheduled jobs

**Deliverables:**

**Week 10: Database System**
- Implement dynamic database model
- Create database property system
- Implement database view system
- Create database entry CRUD
- Implement formula evaluation
- Implement rollup calculation
- Create relation handling

**Database Models:**
- Database model
- Database property model
- Database view model
- Database entry model
- Database entry value model

**API Endpoints:**
- POST /api/v1/projects/{project_id}/databases
- GET /api/v1/databases/{id}
- PATCH /api/v1/databases/{id}
- DELETE /api/v1/databases/{id}
- POST /api/v1/databases/{id}/properties
- GET /api/v1/databases/{id}/entries
- POST /api/v1/databases/{id}/entries
- PATCH /api/v1/entries/{id}

**Week 11: Celery Background Jobs**
- Setup Celery with Redis broker
- Create task queues (high, normal, low priority)
- Implement scheduled jobs with Celery Beat
- Create memory ingestion background job
- Create daily cost report job
- Create backup job
- Create cleanup job for old data
- Implement job monitoring with Flower

**Background Jobs:**
- ingest_conversation_to_memory (after each chat)
- ingest_commit_to_memory (after each commit)
- calculate_team_velocity (daily)
- send_overdue_task_reminders (daily)
- generate_daily_cost_report (daily)
- cleanup_old_sessions (weekly)
- backup_database (daily)

**Week 12: Notifications & WebSocket**
- Implement WebSocket manager
- Create notification model
- Implement notification CRUD
- Create real-time notification system
- Implement email notifications
- Create notification preferences
- Add desktop notification support
- Implement broadcast system for updates

**Database Models:**
- Notification model
- Notification preference model

**API Endpoints:**
- GET /api/v1/notifications
- PATCH /api/v1/notifications/{id}/read
- DELETE /api/v1/notifications/{id}
- PATCH /api/v1/users/me/notification-preferences
- WS /api/v1/ws (main WebSocket connection)

**Services:**
- WebSocketManager: Manage connections
- NotificationService: Send notifications
- EmailService: SMTP client for emails
- BroadcastService: Send to all project members

**Testing Requirements (Phase 4):**
- Unit tests for database property evaluation
- Unit tests for formula calculations
- Unit tests for Celery tasks
- Integration tests for database CRUD
- Integration tests for background jobs
- Integration tests for notifications
- Integration tests for WebSocket
- Test scheduled job execution
- Test notification delivery
- Minimum 80% coverage for new code

**Exit Criteria Phase 4:**
- [ ] Custom databases can be created
- [ ] Database properties work (all types)
- [ ] Formulas and rollups calculate correctly
- [ ] Celery jobs execute successfully
- [ ] Background memory ingestion works
- [ ] Notifications send correctly
- [ ] WebSocket broadcasts work
- [ ] All tests pass (80%+ coverage)
- [ ] Flower dashboard accessible

---

**Phase 5: Frontend Development (Weeks 13-16)**

**Objectives:**
- Build Next.js application
- Implement authentication UI
- Create main application layout
- Build project and task interfaces
- Implement chat interfaces
- Create code editor integration

**Note**: By this point, backend APIs are stable and documented. Frontend team can work in parallel with backend refinements.

**Week 13: Authentication & Layout**
- Initialize Next.js 15 project
- Setup Tailwind CSS with design tokens
- Implement authentication pages (login, register, forgot password)
- Create main application layout
- Implement routing structure
- Setup Zustand stores
- Configure React Query
- Implement protected routes

**Week 14: Project & Task Management**
- Create project list page
- Create project detail page
- Implement task board (Kanban view)
- Implement task list (table view)
- Create task detail modal
- Implement task creation flow
- Add task filtering and sorting
- Create milestone views

**Week 15: Chat Interfaces**
- Create normal chat page (ChatGPT-style)
- Implement message rendering
- Add markdown and code highlighting
- Create project chat page (Cursor-inspired)
- Integrate CodeMirror 6 editor
- Add file tree component
- Implement terminal (xterm.js)
- Setup WebSocket connection

**Week 16: Polish & Integration**
- Implement database views
- Create settings pages
- Add command palette (Cmd+K)
- Implement theme switching
- Add loading states and skeletons
- Create error boundaries
- Implement toast notifications
- Add keyboard shortcuts
- Final UI polish and animations

**Testing Requirements (Phase 5):**
- Component unit tests with Vitest
- Component integration tests with Testing Library
- E2E tests with Playwright for critical flows:
  - User registration and login
  - Project creation and task management
  - Chat conversation
  - Code editor usage
- Accessibility tests (axe-core)
- Visual regression tests (Percy or Chromatic)
- Minimum 70% coverage for components

**Exit Criteria Phase 5:**
- [ ] All pages render correctly
- [ ] Authentication flow works end-to-end
- [ ] Projects and tasks manageable via UI
- [ ] Chat interfaces functional
- [ ] Code editor works with syntax highlighting
- [ ] Terminal executes commands
- [ ] WebSocket updates work real-time
- [ ] All E2E tests pass
- [ ] Accessibility audit passes (WCAG AA)
- [ ] Performance: Lighthouse score >90

---

**Phase 6: Integration, Testing & Launch Prep (Weeks 17-20)**

**Objectives:**
- Integration testing full stack
- Performance optimization
- Security audit
- Documentation
- Deployment preparation
- Launch readiness

**Week 17: Integration & Refinement**
- End-to-end workflow testing (Idea → PRD → Implementation)
- Fix integration bugs
- Optimize database queries (N+1 prevention)
- Implement caching strategies
- Add database indexes
- Optimize frontend bundle size
- Add error monitoring (Sentry)
- Implement analytics (optional)

**Week 18: Performance & Optimization**
- Backend performance testing (load tests with Locust)
- Frontend performance optimization (code splitting)
- Database query optimization
- Redis caching optimization
- Implement rate limiting
- Add request compression
- Optimize image loading
- Implement lazy loading
- Target: <2s page load, <500ms API responses

**Week 19: Security & Documentation**
- Security audit (OWASP Top 10 checklist)
- Penetration testing (basic)
- Dependency vulnerability scan
- Input sanitization audit
- SQL injection prevention verification
- XSS prevention verification
- Write comprehensive README
- Create API documentation (OpenAPI/Swagger)
- Write deployment guide
- Create user guide with screenshots
- Write contribution guidelines

**Week 20: Launch Preparation**
- Setup production environment
- Configure monitoring (Prometheus + Grafana)
- Setup logging (Loki)
- Configure backups
- Create disaster recovery plan
- Write incident response procedures
- Prepare demo video
- Write launch blog post
- Create Product Hunt submission
- Final QA testing
- Create "Show HN" post draft

**Testing Requirements (Phase 6):**
- Load testing: 100 concurrent users
- Stress testing: Find breaking point
- Security testing: OWASP Top 10
- Penetration testing: Basic attacks
- Backup and restore testing
- Disaster recovery testing
- Migration testing (from older versions)

**Exit Criteria Phase 6:**
- [ ] Full workflow tested end-to-end by multiple users
- [ ] Performance targets met (<2s, <500ms)
- [ ] Security audit passed
- [ ] All documentation complete
- [ ] Production environment configured
- [ ] Monitoring and logging active
- [ ] Backups configured and tested
- [ ] Launch materials ready
- [ ] Final QA approved by team

---

### Testing Strategy Per Phase

**Testing Pyramid:**
```
           /\
          /  \
         / E2E \          10% - Playwright (critical flows)
        /──────\
       /        \
      / Integra- \        30% - API integration tests
     /    tion    \
    /──────────────\
   /                \
  /   Unit Tests     \    60% - Fast, isolated tests
 /____________________\
```

**Backend Testing Strategy:**

**Unit Tests (60% of total tests):**
- Test individual functions and methods
- Mock all external dependencies
- Focus on business logic
- Run in <5 seconds
- Tools: pytest, pytest-mock
- Coverage target: 90%+ for critical code

**Integration Tests (30%):**
- Test API endpoints end-to-end
- Use test database (PostgreSQL in Docker)
- Test Redis and Qdrant interactions
- Mock only external APIs (OpenRouter, GitHub)
- Run in <30 seconds
- Tools: pytest, pytest-asyncio, httpx
- Coverage target: 80%+ for API routes

**Contract Tests:**
- Verify OpenAPI spec matches implementation
- Test request/response schemas
- Validate status codes
- Tools: pytest with OpenAPI validation

**Performance Tests:**
- Load testing with Locust
- Stress testing to find limits
- Monitor memory usage during tests
- Target: 100 req/s per endpoint

**Frontend Testing Strategy:**

**Component Unit Tests (50%):**
- Test individual components in isolation
- Mock all API calls
- Focus on logic and state management
- Tools: Vitest, Testing Library
- Coverage target: 70%+ for components

**Integration Tests (30%):**
- Test user workflows
- Test API integration with MSW (Mock Service Worker)
- Test state management across components
- Tools: Vitest, Testing Library, MSW

**E2E Tests (20%):**
- Test critical user journeys
- Use real backend (test environment)
- Test in multiple browsers
- Tools: Playwright
- Focus areas:
  - User registration and login
  - Project creation
  - Task creation and management
  - Chat conversation
  - Code editor usage

**Visual Regression Tests:**
- Test UI consistency across changes
- Screenshot comparison
- Tools: Percy or Chromatic
- Run on every PR

**Accessibility Tests:**
- WCAG 2.1 AA compliance
- Keyboard navigation
- Screen reader compatibility
- Tools: axe-core, pa11y

**Continuous Integration:**

**On Every Commit:**
1. Linting (ESLint, Black)
2. Type checking (TypeScript, mypy)
3. Unit tests
4. Code coverage report

**On Every PR:**
1. All commit checks
2. Integration tests
3. E2E tests (critical paths)
4. Security scan (dependencies)
5. Build verification
6. Visual regression (frontend)

**On Main Branch:**
1. All PR checks
2. Full E2E test suite
3. Performance benchmarks
4. Security audit
5. Deploy to staging
6. Smoke tests on staging

**Testing Tools Summary:**

**Backend:**
- pytest: Unit and integration testing
- pytest-asyncio: Async test support
- pytest-cov: Coverage reporting
- pytest-mock: Mocking utilities
- httpx: API testing client
- Locust: Load testing
- bandit: Security linting
- safety: Dependency vulnerability scanning

**Frontend:**
- Vitest: Unit testing (Vite-native, fast)
- Testing Library: Component testing
- Playwright: E2E testing
- MSW: API mocking
- axe-core: Accessibility testing
- Percy/Chromatic: Visual regression

**Test Data Management:**
- Factories for test data generation (factory_boy for Python)
- Fixtures for common test scenarios
- Database seeding scripts
- Reset database between tests

**Test Coverage Goals:**
- Backend overall: 85%+
- Backend critical paths: 95%+
- Frontend components: 70%+
- Frontend critical paths: 90%+

---

### Incremental Development Strategy
1. **Phase 1**: Backend foundation (API, database, auth)
2. **Phase 2**: Frontend foundation (UI, routing, basic components)
3. **Phase 3**: AI integration (OpenRouter, basic chat)
4. **Phase 4**: LangGraph workflows (core orchestration)
5. **Phase 5**: OpenSpec integration (proposal → implementation → archive)
6. **Phase 6**: Polish, testing, documentation, launch

### Risk Mitigation
- 8GB RAM constraint: Extensive load testing, quantization, tuning, graceful degradation
- AI cost unpredictability: Hard budget limits, real-time tracking, cost preview, prompt caching
- AI output quality: Human approval gates, confidence scoring, user feedback collection
- Feature scope creep: Ruthless prioritization, fixed timeline, feature freeze before launch
- User adoption: Build in public, excellent docs, video tutorials, community engagement

### Quality Gates
- No merge without passing tests
- No merge without code review
- No deployment without performance benchmarks
- No feature complete without documentation
- No release without user testing

---

## 🌐 Deployment & Operations

### Self-Hosted Deployment
- Docker Compose for local development and small teams
- Single-server deployment sufficient for <100 users
- Automated backups of PostgreSQL
- Environment variable configuration
- Caddy for automatic HTTPS

### Production Deployment
- Load balancer (Nginx or Caddy) for multiple app servers
- Separate database server with replication
- Redis Sentinel for high availability
- Qdrant cluster for scaling vector search
- CDN for static assets (Cloudflare)
- Monitoring with Prometheus + Grafana
- Log aggregation with Loki

### Hosted Version (Future)
- Multi-tenant architecture with data isolation
- Usage-based billing (0% markup on AI + 5% platform fee)
- Automatic scaling based on load
- Global CDN distribution
- 99.9% uptime SLA
- Regular security audits

### Backup Strategy
- PostgreSQL: Daily full backups, continuous WAL archiving
- Qdrant: Weekly snapshots
- User files: Real-time sync to object storage
- Retention: 30 days for operational backups, 1 year for compliance

### Monitoring & Alerting
- Application performance monitoring (response times, error rates)
- Infrastructure monitoring (CPU, memory, disk, network)
- AI usage monitoring (tokens, costs, model distribution)
- Alert on: high error rates, slow responses, memory pressure, budget overruns
- Weekly health reports emailed to team

---

## 🤝 Contribution Guidelines

### Open Source Principles
- MIT License for maximum freedom
- Public roadmap and issue tracker
- Transparent decision-making process
- Recognition for all contributors
- Code of conduct for respectful community

### How to Contribute
- Bug reports with reproducible examples
- Feature requests with clear use cases
- Code contributions via pull requests
- Documentation improvements
- Community support in Discord/GitHub Discussions

### Development Setup
- Fork repository
- Clone locally
- Follow setup instructions in README
- Create feature branch
- Make changes with tests
- Submit pull request
- Wait for review and merge

### Code Style
- Frontend: Prettier + ESLint
- Backend: Black + isort + mypy
- Conventional commits
- Clear, self-documenting code
- Comments for complex logic only

---

---

## ✅ Final PRD Audit Checklist

### Critical Features Verification

**AI-Powered Workflow Orchestration:**
- [ ] End-to-end AI workflow (Idea → Production) documented
- [ ] Multi-mode AI chat system specified (5 pre-built modes + custom)
- [ ] OpenRouter integration with 400+ models
- [ ] LangGraph workflow orchestration with state management
- [ ] OpenSpec integration for spec-driven development
- [ ] ACE framework for continuous learning
- [ ] Prompt caching for 90% cost reduction
- [ ] Complexity-based model routing
- [ ] Cost tracking and budget limits
- [ ] Self-reflection and multi-hop retrieval for memory

**Project Management Features:**
- [ ] Dual chat system (Normal + Project-integrated)
- [ ] Project-based memory (short-term Redis + long-term Qdrant)
- [ ] Task management with Linear-inspired UI
- [ ] Multiple task views (Board, List, Calendar, Timeline, Gallery)
- [ ] Task dependencies (blocks/depends on)
- [ ] Milestones with progress tracking
- [ ] Roadmap view with Gantt chart
- [ ] Notion-style databases with dynamic CRUD
- [ ] Multiple database views per database
- [ ] Custom database properties (all types)
- [ ] Formula and rollup calculations
- [ ] Real-time updates via WebSocket

**Code Integration Features:**
- [ ] Project chat page (Cursor-inspired layout)
- [ ] CodeMirror 6 editor with syntax highlighting
- [ ] Integrated terminal (xterm.js)
- [ ] File tree explorer
- [ ] Git integration (status, commit, push, pull, branches)
- [ ] GitHub PR automation
- [ ] Commit-task linking
- [ ] Inline AI suggestions in editor
- [ ] Code editor theme matching Ardha design

**OpenSpec Integration:**
- [ ] Proposal creation (proposal.md, tasks.md, spec-delta.md)
- [ ] Visual UI for proposal review (not just markdown)
- [ ] Auto-sync tasks from OpenSpec to PostgreSQL
- [ ] Git commit auto-updates to OpenSpec task status
- [ ] Proposal approval workflow
- [ ] Automated archival when tasks complete
- [ ] Spec delta application to source truth

**UI/UX Features:**
- [ ] Premium theme system (LCH color space)
- [ ] Seamless dark/light mode on ALL pages
- [ ] Theme coverage from login through all app pages
- [ ] Consistent purple accent throughout
- [ ] 4px spacing grid maintained
- [ ] Inter Variable font for UI
- [ ] JetBrains Mono font for code
- [ ] Lucide React icons consistently
- [ ] Framer Motion animations
- [ ] All component states defined (hover, active, focus, disabled)
- [ ] WCAG 2.1 AA accessibility compliance
- [ ] Command palette (Cmd+K)
- [ ] Keyboard shortcuts
- [ ] Toast notifications
- [ ] Loading states and skeletons
- [ ] Error boundaries

**Database Features:**
- [ ] Notion-style database creation
- [ ] Database deletion with confirmation
- [ ] Dynamic property addition
- [ ] Dynamic property deletion
- [ ] Property reordering
- [ ] Database view creation (Board, List, Calendar, Timeline, Gallery)
- [ ] View-specific filters and sorts
- [ ] Real-time sync across all viewers
- [ ] Formula evaluation
- [ ] Rollup calculations
- [ ] Relation handling between databases

**Authentication & Security:**
- [ ] Email/password authentication
- [ ] GitHub OAuth integration
- [ ] Google OAuth integration
- [ ] JWT access tokens (15 min)
- [ ] Refresh tokens (7 days, httpOnly cookie)
- [ ] Role-based access control (Owner, Admin, Member, Viewer)
- [ ] Password strength validation
- [ ] Input sanitization
- [ ] SQL injection prevention (ORM)
- [ ] XSS prevention
- [ ] CORS configuration
- [ ] Rate limiting
- [ ] Environment variables for secrets

**Performance Requirements:**
- [ ] 8GB RAM system constraint respected
- [ ] PostgreSQL: 2GB container limit
- [ ] Qdrant: 2.5GB limit with quantization
- [ ] Redis: 512MB limit with LRU eviction
- [ ] Backend: 2GB limit
- [ ] Frontend: 1GB limit
- [ ] Page load <2 seconds (90th percentile)
- [ ] API response <500ms (95th percentile)
- [ ] Bundle size <200KB gzipped
- [ ] Time to Interactive <3 seconds

**Data Models:**
- [ ] User model complete
- [ ] Project model complete
- [ ] Task model with all fields
- [ ] Task dependencies model
- [ ] Task tags model
- [ ] Task activity (audit log)
- [ ] Chat model
- [ ] Message model
- [ ] Milestone model
- [ ] OpenSpec proposal model
- [ ] File model
- [ ] Project member model with roles
- [ ] Database model (Notion-style)
- [ ] Database property model
- [ ] Database view model
- [ ] Database entry model
- [ ] Notification model
- [ ] AI usage tracking model

**API Endpoints:**
- [ ] Authentication endpoints (register, login, refresh, logout, me)
- [ ] Project CRUD endpoints
- [ ] Task CRUD endpoints with dependencies
- [ ] Task status update
- [ ] Task comments
- [ ] Chat CRUD endpoints
- [ ] Message creation and streaming
- [ ] AI model selection
- [ ] AI usage tracking
- [ ] File CRUD endpoints
- [ ] Git status, commit, push, pull
- [ ] Git branch management
- [ ] GitHub PR creation
- [ ] OpenSpec proposal CRUD
- [ ] OpenSpec approval workflow
- [ ] Database CRUD endpoints
- [ ] Database property management
- [ ] Database entry CRUD
- [ ] Milestone CRUD endpoints
- [ ] Notification endpoints
- [ ] WebSocket endpoints for real-time updates

**Backend Services:**
- [ ] AIService (OpenRouter client)
- [ ] LangGraphService (workflow orchestration)
- [ ] MemoryService (Qdrant operations)
- [ ] EmbeddingService (text → vectors)
- [ ] OpenSpecService (markdown parsing)
- [ ] GitService (GitPython wrapper)
- [ ] GitHubService (GitHub API client)
- [ ] FileService (file operations)
- [ ] NotificationService (notifications)
- [ ] EmailService (SMTP client)
- [ ] WebSocketManager (real-time connections)
- [ ] BroadcastService (send to all project members)
- [ ] BackgroundJobService (Celery tasks)

**Background Jobs:**
- [ ] Memory ingestion (conversations)
- [ ] Memory ingestion (commits)
- [ ] Team velocity calculation
- [ ] Overdue task reminders
- [ ] Daily cost reports
- [ ] Session cleanup
- [ ] Database backups

**Testing Coverage:**
- [ ] Backend unit tests (85%+ coverage)
- [ ] Backend integration tests
- [ ] Backend API contract tests
- [ ] Backend load tests
- [ ] Frontend component tests (70%+ coverage)
- [ ] Frontend integration tests
- [ ] Frontend E2E tests (Playwright)
- [ ] Frontend accessibility tests
- [ ] Frontend visual regression tests
- [ ] CI/CD pipeline configured
- [ ] All tests run on every commit
- [ ] E2E tests on every PR

**Documentation:**
- [ ] Comprehensive README
- [ ] Installation guide (Docker Compose)
- [ ] Installation guide (Native)
- [ ] API documentation (OpenAPI/Swagger)
- [ ] User guide with screenshots
- [ ] Deployment guide
- [ ] Contribution guidelines
- [ ] Code of conduct
- [ ] Security policy
- [ ] Changelog

**Deployment Requirements:**
- [ ] Docker Compose for self-hosted
- [ ] Environment variable configuration
- [ ] PostgreSQL migrations automated
- [ ] Redis persistence configured
- [ ] Qdrant persistence configured
- [ ] Caddy automatic HTTPS
- [ ] Monitoring setup (Prometheus + Grafana)
- [ ] Logging setup (Loki)
- [ ] Backup automation
- [ ] Disaster recovery procedures

**Page Descriptions (All 23 Pages):**
- [ ] Login page described
- [ ] Register page described
- [ ] Forgot password page described
- [ ] Password reset page described
- [ ] Dashboard/home page described
- [ ] Projects list page described
- [ ] Project detail page described
- [ ] Project overview dashboard described
- [ ] Tasks list page described
- [ ] Task board (Kanban) described
- [ ] Task detail modal described
- [ ] Calendar view described
- [ ] Timeline (Gantt) view described
- [ ] Database view page described
- [ ] Normal chat page described
- [ ] Project chat page (Cursor-inspired) described in detail
- [ ] Files page described
- [ ] Git page described
- [ ] OpenSpec page described
- [ ] Project settings page described
- [ ] User settings page described
- [ ] Command palette described
- [ ] Error pages (404, 500, Offline) described

**Locked Dependencies:**
- [ ] Frontend: All packages with exact versions
- [ ] Backend: All packages with locked versions in pyproject.toml
- [ ] Docker images: All with specific version tags
- [ ] Development tools: Version requirements specified

**Development Approach:**
- [ ] Backend-first strategy documented
- [ ] 6 sequential phases defined (20 weeks total)
- [ ] Phase 1: Backend Foundation (Weeks 1-3)
- [ ] Phase 2: AI Integration (Weeks 4-6)
- [ ] Phase 3: OpenSpec & Git (Weeks 7-9)
- [ ] Phase 4: Databases & Background Jobs (Weeks 10-12)
- [ ] Phase 5: Frontend Development (Weeks 13-16)
- [ ] Phase 6: Integration & Launch Prep (Weeks 17-20)
- [ ] Testing requirements per phase defined
- [ ] Exit criteria per phase defined
- [ ] Testing pyramid defined (60% unit, 30% integration, 10% E2E)

**Success Metrics:**
- [ ] MVP technical metrics defined (performance, reliability)
- [ ] MVP AI quality metrics defined (accuracy, cost)
- [ ] MVP adoption metrics defined (users, projects)
- [ ] 6-month goals specified
- [ ] 12-month goals specified

**Risk Mitigation:**
- [ ] 8GB RAM constraint mitigation strategies
- [ ] AI cost unpredictability mitigation
- [ ] AI output quality mitigation
- [ ] Feature scope creep mitigation
- [ ] User adoption challenge mitigation
- [ ] Competitive response mitigation

### Missing Critical Features Check

**Cross-Reference with Original PRD:**
- [ ] All features from Executive Summary covered
- [ ] All features from Market Opportunity covered
- [ ] All features from Core Features covered
- [ ] All features from User Experience covered
- [ ] All features from Technical Architecture covered
- [ ] All features from Development Approach covered
- [ ] All success metrics included
- [ ] All risk mitigations included

**Additions Beyond PRD (Improvements):**
- [ ] Comprehensive page-by-page descriptions (23 pages)
- [ ] Detailed Cursor-inspired project chat layout
- [ ] Complete theme system with LCH colors
- [ ] Exhaustive Notion-style database CRUD operations
- [ ] Detailed backend-first development phases
- [ ] Comprehensive testing strategy per phase
- [ ] Locked dependency versions for reproducibility
- [ ] Complete exit criteria per development phase

### Final Sign-Off

**This PRD is complete and ready for development if:**
- [x] All critical features from original PRD included
- [x] All pages described in detail (no visualizations, as requested)
- [x] Premium dark/light theme coverage on ALL pages
- [x] Project chat page (Cursor-inspired) detailed with Ardha theme
- [x] Notion database features with dynamic CRUD fully specified
- [x] Frontend and backend dependencies locked to exact versions
- [x] Backend-first development approach with 6 phases defined
- [x] Testing strategy per phase comprehensive
- [x] Exit criteria per phase clear and measurable
- [x] Final audit completed against original PRD

**Status: ✅ READY FOR DEVELOPMENT**

---

## 📝 Change Log

### Version 1.1 (Current - November 1, 2025)
**Major Enhancements:**
- ✅ Added comprehensive Notion-style database CRUD operations
  - Database creation, editing, deletion workflows
  - Dynamic property management (add/edit/delete)
  - View management with filters and sorts
  - Real-time synchronization specifications

- ✅ Complete premium theme system documentation
  - LCH color space implementation across ALL pages
  - Dark/light mode coverage from login through all application pages
  - Detailed theme specifications for every UI element
  - Consistent purple accent throughout application

- ✅ All 23 pages described in detail (without visualizations)
  - Authentication pages (4): Login, Register, Forgot Password, Reset Password
  - Main application pages (19): Dashboard, Projects, Tasks, Chat, Settings, etc.
  - Project chat page: Cursor-inspired layout with Ardha theme integration
  - Comprehensive descriptions of every element, interaction, and state

- ✅ Locked dependencies for reproducible builds
  - Frontend: All npm packages with exact versions
  - Backend: All Poetry packages with locked versions
  - Docker: All images with specific version tags
  - Development tools: Version requirements specified

- ✅ Backend-first development strategy
  - 6 sequential phases over 20 weeks
  - Phase 1: Backend Foundation (Weeks 1-3)
  - Phase 2: AI Integration (Weeks 4-6)
  - Phase 3: OpenSpec & Git (Weeks 7-9)
  - Phase 4: Databases & Background Jobs (Weeks 10-12)
  - Phase 5: Frontend Development (Weeks 13-16)
  - Phase 6: Integration & Launch Prep (Weeks 17-20)

- ✅ Comprehensive testing strategy
  - Testing pyramid defined (60% unit, 30% integration, 10% E2E)
  - Testing requirements per phase
  - Coverage targets specified
  - CI/CD pipeline requirements
  - Exit criteria per phase

- ✅ Final PRD audit checklist
  - 200+ checkpoint verification against original PRD
  - Missing features identification
  - Cross-reference with all sections
  - Ready-for-development sign-off

### Version 1.0 (October 31, 2025)
- Initial PRD creation
- Complete technical architecture defined
- OpenSpec integration strategy documented
- 8GB RAM optimization approach finalized
- MVP scope locked for 4-month timeline

### Future Versions
- v1.2: Mobile responsive improvements (TBD)
- v1.3: VS Code extension integration (TBD)
- v2.0: Desktop apps (Electron) (TBD)
- v2.1: Mobile apps (iOS + Android) (TBD)
- v3.0: Enterprise features (SSO, SAML, audit logs) (TBD)

---

## 🎯 Project Status

**Current Phase**: Pre-Development (PRD Complete)
**Next Milestone**: MVP Development Kickoff
**Target MVP Launch**: February 2026 (4 months)
**Team Size**: 2-4 full-stack developers needed
**Funding Status**: Self-funded / Open source

**Immediate Next Steps**:
1. Create GitHub organization and repositories
2. Setup development environment
3. Initialize monorepo structure
4. Configure CI/CD pipeline
5. Begin Phase 1: Backend foundation

---

## 📚 Additional Resources

### External Documentation
- OpenSpec: https://github.com/Fission-AI/OpenSpec
- OpenRouter: https://openrouter.ai/
- LangGraph: https://langchain-ai.github.io/langgraph/
- FastAPI: https://fastapi.tiangolo.com/
- Next.js: https://nextjs.org/
- shadcn/ui: https://ui.shadcn.com/

### Research Papers
- Agentic Context Engineering (ACE): https://arxiv.org/abs/2510.04618

### Community
- GitHub: https://github.com/yourusername/ardha (TBD)
- Discord: https://discord.gg/ardha (TBD)
- Twitter: https://twitter.com/ardhapm (TBD)

---

**This document serves as the complete project context for AI coding assistants working on Ardha. It covers the vision, architecture, workflows, conventions, and standards without implementation details. Refer to this document when working on any feature to maintain consistency with the overall project design.**