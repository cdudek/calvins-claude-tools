---
name: docs-c4-create
description: "Creates C4 architecture diagrams for a system: context, container and component levels, from the code and configuration. Use when the user says 'C4 model', 'C4 diagram', 'system context diagram', 'container diagram', 'component diagram'. Skip for: ER and data model diagrams or structural-risk planning (use cct:arch-plan-write), checking documentation against code (use cct:docs-audit)."
allowed-tools: "Bash(git *) Read Grep Glob Write"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# C4 Model Generator

Expert at generating C4 model architecture diagrams.

## C4 Model Overview

The C4 model provides four levels of abstraction:

1. **Context** - System context showing actors and external systems
2. **Container** - High-level technical building blocks (apps, databases, etc.)
3. **Component** - Components within containers
4. **Code** - Class/module level (optional, often auto-generated)

## Level 1: System Context Diagram

Shows how the system fits into the world.

```mermaid
C4Context
    title System Context Diagram for guilde-lite

    Person(dev, "Developer", "Uses Claude Code for development")
    System(guilde, "guilde-lite", "Development environment automation")

    System_Ext(homebrew, "Homebrew", "Package manager")
    System_Ext(mise, "mise", "Runtime version manager")
    System_Ext(orbstack, "OrbStack", "Container runtime")
    System_Ext(claude, "Claude Code", "AI assistant")

    Rel(dev, guilde, "Uses")
    Rel(guilde, homebrew, "Installs system packages")
    Rel(guilde, mise, "Manages runtimes")
    Rel(guilde, orbstack, "Runs containers")
    Rel(dev, claude, "Interacts with")
    Rel(claude, guilde, "Automates")
```

### Context Diagram Elements
- **Person**: Human users of the system
- **System**: The system being documented (highlighted)
- **System_Ext**: External systems that interact with your system
- **Rel**: Relationships between elements

## Level 2: Container Diagram

Shows the technical building blocks.

```mermaid
C4Container
    title Container Diagram for guilde-lite

    Person(dev, "Developer")

    System_Boundary(guilde, "guilde-lite") {
        Container(taskfile, "Taskfile", "YAML", "Task automation")
        Container(scripts, "Scripts", "Bash", "Automation scripts")
        Container(conductor, "Conductor", "Markdown", "Workflow orchestration")
        Container(claude_config, "Claude Config", "JSON/MD", "AI assistant configuration")
    }

    System_Boundary(databases, "Database Stack") {
        ContainerDb(postgres, "PostgreSQL", "Database", "Primary data store")
        ContainerDb(redis, "Redis", "Cache", "Caching and queues")
        ContainerDb(qdrant, "Qdrant", "Vector DB", "Embeddings storage")
    }

    Rel(dev, taskfile, "Runs tasks")
    Rel(taskfile, scripts, "Executes")
    Rel(scripts, databases, "Manages")
    Rel(dev, conductor, "Follows workflow")
    Rel(dev, claude_config, "Configures AI")
```

### Container Diagram Elements
- **Container**: Application, service, or data store
- **ContainerDb**: Database or storage system
- **System_Boundary**: Groups containers within a system

## Level 3: Component Diagram

Shows components within a container.

```mermaid
C4Component
    title Component Diagram for Conductor

    Container_Boundary(conductor, "Conductor") {
        Component(tracks, "Tracks", "Markdown", "Work item definitions")
        Component(workflow, "Workflow", "Markdown", "Development process")
        Component(tech_stack, "Tech Stack", "Markdown", "Technology decisions")
        Component(product, "Product", "Markdown", "Product context")
    }

    Container_Boundary(hooks, "Claude Hooks") {
        Component(session_start, "SessionStart", "JSON", "Context loading")
        Component(pre_compact, "PreCompact", "JSON", "Context preservation")
        Component(pre_tool, "PreToolUse", "JSON", "TDD enforcement")
        Component(post_tool, "PostToolUse", "JSON", "Review reminders")
    }

    Rel(workflow, tracks, "References")
    Rel(session_start, tracks, "Loads")
    Rel(pre_compact, tracks, "Preserves state")
```

### Component Diagram Elements
- **Component**: A logical grouping of code
- **Container_Boundary**: The parent container

## C4 with Mermaid

Since native C4 support varies, you can also use standard Mermaid flowcharts:

### Alternative Context Diagram
```mermaid
flowchart TB
    subgraph Users
        dev[("Developer")]
    end

    subgraph guilde-lite["guilde-lite System"]
        automation["Automation<br/>Taskfile + Scripts"]
        conductor["Conductor<br/>Workflow Management"]
        claude_cfg["Claude Config<br/>AI Settings"]
    end

    subgraph External["External Systems"]
        mise["mise<br/>Runtime Manager"]
        orbstack["OrbStack<br/>Containers"]
        claude["Claude Code<br/>AI Assistant"]
    end

    dev --> automation
    dev --> conductor
    automation --> mise
    automation --> orbstack
    dev --> claude
    claude --> claude_cfg
```

## C4 Documentation Structure

Recommended documentation structure:
```
docs/
├── architecture/
│   ├── c4-context.md       # Level 1: Context
│   ├── c4-containers.md    # Level 2: Containers
│   ├── c4-components/      # Level 3: Components
│   │   ├── conductor.md
│   │   ├── automation.md
│   │   └── hooks.md
│   └── decisions/          # Architecture Decision Records
│       ├── ADR-001-mise-first.md
│       └── ADR-002-orbstack.md
```

## Generation Workflow

1. **Identify Scope**: Determine which C4 level is needed
2. **Map Actors**: List all people and external systems
3. **Define Boundaries**: Draw system and container boundaries
4. **Add Elements**: Place containers, components within boundaries
5. **Connect with Relationships**: Add relationship arrows with descriptions
6. **Review Abstraction Level**: Ensure appropriate detail for the level

## Best Practices

### Naming
- Use clear, consistent names
- Include technology in container descriptions
- Use action verbs for relationships

### Layout
- Keep diagrams focused on one level
- Group related elements
- Limit relationships to meaningful ones (not every possible connection)

### Documentation
- Always include a title
- Add descriptions for complex relationships
- Link to more detailed diagrams at lower levels

## Integration

Optional external agents (not in cct; use them only when the c4-architecture plugin is installed):
- `c4-context` - System context level
- `c4-container` - Container level
- `c4-component` - Component level
- `c4-code` - Code level

## Commands

```bash
# Check architecture docs
bash scripts/doc-sync-check.sh check docs/architecture/c4-context.md

# Validate all documentation
task docs:validate
```
