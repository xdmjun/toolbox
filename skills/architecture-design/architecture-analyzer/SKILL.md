---
name: "architecture-analyzer"
description: "Analyzes project architecture across 5 dimensions (technical, data, business, application, code). Invoke when user wants to understand an unfamiliar project's architecture or needs architecture documentation."
---

# Architecture Analyzer

Analyzes unfamiliar projects to produce comprehensive architecture documentation across five dimensions: Technical Architecture, Data Architecture, Business Architecture, Application Architecture, and Code Architecture.

## When to Invoke

- User wants to understand an unfamiliar project's architecture
- User asks "analyze this project's architecture"
- User needs architecture documentation
- User wants to see how different parts of a system connect

## Scope & Boundaries

### What This Skill Focuses On

| Focus Area | Description |
|------------|-------------|
| **Architecture Dimensions** | Technical, Data, Business, Application, Code |
| **Architecture Patterns** | MVC, Layered, Hexagonal, Microservices, etc. |
| **Architecture Diagrams** | C4 Model, Data Flow, Sequence Diagrams |
| **Architecture Decisions** | ADR (Architecture Decision Records) |
| **System Structure** | How components interact and depend on each other |

### What This Skill Does NOT Cover

| Area | Recommended Skill/Tool |
|------|------------------------|
| Detailed project statistics | Use `project-analyzer` skill |
| Code quality & linting | Use code review tools |
| Build/test commands | Check package.json scripts, Makefile |
| Dependency health | Use `npm outdated`, `pip-audit` |
| Security analysis | Use security scanning tools |

## Analysis Framework

Based on 4+1 View Model and C4 Model, this skill provides multi-perspective architecture analysis:

### Five Architecture Dimensions

| Dimension | Focus | Key Questions |
|-----------|-------|---------------|
| **Technical Architecture** | Tech stack, infrastructure | What technologies? How deployed? |
| **Data Architecture** | Data models, data flow | What data? How stored and flows? |
| **Business Architecture** | Business domains, processes | What business problems? How solved? |
| **Application Architecture** | Services, components, APIs | How structured? How communicate? |
| **Code Architecture** | Code organization, patterns | How code organized? What patterns? |

## Execution Steps

### Step 1: Project Discovery & Type Detection

```
1. Determine analysis scope:
   - If user specifies paths → Use those paths
   - If no path specified → Use current working directory

2. Identify project type:
```

| Project Type | Architectural Implications |
|--------------|---------------------------|
| **Monolithic** | Single deployable unit, layered architecture |
| **Microservices** | Multiple services, distributed data, inter-service communication |
| **Full-stack** | Frontend + Backend integration patterns |
| **Frontend-only** | Component architecture, state management, API integration |
| **Backend-only** | API design, service layer, data access patterns |
| **Library/Package** | Public API design, export structure |

```
3. Check completeness:
   - If only frontend OR only backend detected:
     → Prompt user: "Detected [frontend/backend] only. For complete architecture analysis, please provide both frontend and backend code paths."

4. Report progress:
   → "Starting architecture analysis for [project type]..."
```

### Step 2: Technical Architecture Analysis

Analyze technology choices from an architectural perspective. Report progress: "Analyzing technical architecture..."

**What to identify:**

| Category | Examples | Architectural Relevance |
|----------|----------|------------------------|
| Frontend Framework | React, Vue, Angular | Component model, rendering strategy |
| Backend Framework | FastAPI, Express, Django | Request handling, middleware pattern |
| Database | PostgreSQL, MongoDB, Redis | Data storage strategy, consistency model |
| Message Queue | RabbitMQ, Kafka | Async processing, event-driven architecture |
| Cache | Redis, Memcached | Caching strategy, performance optimization |
| API Style | REST, GraphQL, gRPC | Interface design, communication pattern |

**Output sections:**
- Technology Stack table (Layer, Technology, Architectural Role)
- Infrastructure Architecture (Container, Orchestration, Deployment)
- Tech Stack Diagram (Mermaid graph showing layers)

### Step 3: Data Architecture Analysis

Analyze data models and flows. Report progress: "Analyzing data architecture..."

**What to look for:**

| File Pattern | Architectural Information |
|--------------|---------------------------|
| models/, entities/ | Domain model structure |
| migrations/ | Schema evolution strategy |
| prisma/schema.prisma | Data modeling approach |
| repositories/ | Data access pattern |

**Output sections:**
- Core Data Entities (Entity, Key Attributes, Relationships)
- Data Flow Diagram (Mermaid flowchart)
- Storage Strategy (Primary DB, Cache, File Storage)
- Data Consistency Model (if applicable)

### Step 4: Business Architecture Analysis

Analyze business logic and processes. Report progress: "Analyzing business architecture..."

**What to look for:**

| File Pattern | Architectural Information |
|--------------|---------------------------|
| README.md | Business context and goals |
| services/, domain/ | Business logic organization |
| api/, routes/ | Business capabilities exposed |

**Output sections:**
- Core Business Domains (Domain, Description, Key Capabilities)
- Business Process Flow (Mermaid sequence diagram)
- Business Rules Location (where business logic resides)

### Step 5: Application Architecture Analysis

Analyze application structure and interactions. Report progress: "Analyzing application architecture..."

**Architecture pattern detection:**

| Pattern | Indicators | Characteristics |
|---------|------------|-----------------|
| MVC | models/, views/, controllers/ | Separation of concerns |
| Layered | presentation/, business/, data/ | Hierarchical dependencies |
| Hexagonal/Clean | domain/, application/, infrastructure/ | Dependency inversion |
| Modular | Feature-based directories | High cohesion, low coupling |
| Microservices | Multiple services/, docker-compose | Distributed, independent deploy |

**Output sections:**
- Architecture Pattern (detected pattern and rationale)
- Service/Module Structure (components and responsibilities)
- Application Architecture Diagram (Mermaid graph)
- API Structure (endpoints, protocols, contracts)

### Step 6: Code Architecture Analysis

Analyze code organization at macro level. Report progress: "Analyzing code architecture..."

**What to look for:**

| Aspect | Architectural Relevance |
|--------|------------------------|
| Directory structure | Module boundaries, layering |
| Dependency direction | Coupling, dependency rules |
| Shared modules | Reusability, common utilities |
| Entry points | Application bootstrap, initialization |

**Output sections:**
- Directory Structure (tree showing architectural layers)
- Layered Architecture Diagram (Mermaid graph)
- Design Patterns Detected (pattern, location, purpose)
- Code Organization Conventions

### Step 7: Integrated Architecture View

Create comprehensive C4 Model view. Report progress: "Creating integrated architecture view..."

**C4 Model Levels:**

| Level | View | Description |
|-------|------|-------------|
| **Context** | System in environment | Users, external systems |
| **Container** | Deployable units | Apps, services, databases |
| **Component** | Container internals | Modules, classes, functions |

**Output sections:**
- System Context Diagram (C4 Level 1)
- Container Diagram (C4 Level 2)
- Component Diagram (C4 Level 3)
- Architecture Decision Records (ADR)

### Step 8: Content Verification (CRITICAL)

Before generating any documentation, MUST verify all content against actual code:

```
Verification Checklist:
□ All mentioned components/services actually exist
□ All technology names are from actual config files
□ All data entities are from actual model files
□ All architecture patterns are supported by code structure
□ No assumptions or guesses without code evidence
```

**Mark uncertain content:**
- If something cannot be verified, mark as `[Unverified: reason]`
- Never invent architecture components or patterns

### Step 9: User Confirmation for Documentation

After completing verification, ALWAYS ask the user:

```
Architecture analysis complete! Would you like me to generate a documentation file?

Options:
1. Yes - Generate ARCHITECTURE.md in the project root
2. Yes - Generate to a custom path (you specify)
3. No - I've seen enough, no need for a file
```

## Common Architecture Patterns

### By Project Type

| Project Type | Common Patterns | Key Characteristics |
|--------------|-----------------|---------------------|
| **Monolithic** | Layered, MVC | Single deployable, shared database |
| **Microservices** | Event-Driven, CQRS | Independent deploy, distributed data |
| **Full-stack** | Component-based, API Gateway | Frontend-Backend separation |
| **Frontend** | Flux/Redux, MVVM | State management, component hierarchy |
| **Backend** | Repository, Service Layer | Data access abstraction |

### Architecture Decision Records (ADR) Template

When documenting architecture decisions:

```
## ADR-001: [Decision Title]

### Context
[What is the issue that we're seeing that motivates this decision?]

### Decision
[What is the change that we're proposing and/or doing?]

### Consequences
[What becomes easier or more difficult to do because of this change?]

### Alternatives Considered
[What other options were evaluated?]
```

## Special Handling

### For Microservices Architecture
- Document service boundaries and responsibilities
- Map inter-service communication (sync vs async)
- Analyze data distribution strategy
- Note shared infrastructure (API Gateway, Service Mesh)

### For Monolithic Architecture
- Identify modular boundaries within the monolith
- Document layering and dependency direction
- Suggest potential decomposition points

### For Full-Stack Applications
- Document frontend-backend integration pattern
- Analyze API contract and data flow
- Note shared types/models between layers

## Related Skills

For more detailed analysis in specific areas, consider:

| Need | Recommended Skill |
|------|-------------------|
| Project statistics, file counts, LOC | `project-analyzer` |
| Code quality, linting issues | Code review tools |
| Dependency analysis | `npm outdated`, `pip-audit` |
| Security vulnerability scan | Security scanning tools |
| Performance profiling | Profiling tools |

## Output Format

Generate architecture documentation with this structure:

```
# Architecture Documentation

## Executive Summary
[1-2 sentences describing the architecture style and key characteristics]

## Architecture Overview
- Architecture Style: [Monolithic/Microservices/etc.]
- Primary Pattern: [Layered/Hexagonal/etc.]

## 1. Technical Architecture
### Technology Stack
| Layer | Technology | Architectural Role |
|-------|------------|-------------------|
| [Layer] | [Tech] | [Role] |

### Infrastructure Architecture
[Container, orchestration, deployment approach]

### Tech Stack Diagram
[Mermaid graph]

## 2. Data Architecture
### Core Entities
[Entity diagram/table]

### Data Flow
[Mermaid flowchart]

### Storage Strategy
[Database choices, caching strategy]

## 3. Business Architecture
### Business Domains
[Domain breakdown]

### Business Process Flow
[Mermaid sequence diagram]

## 4. Application Architecture
### Architecture Pattern
[Pattern name and rationale]

### Component Structure
[Mermaid component diagram]

### API Architecture
[API style, endpoints overview]

## 5. Code Architecture
### Directory Structure
[Tree showing layers]

### Design Patterns
[Patterns detected]

## 6. C4 Model Views
### System Context
[C4 Level 1 diagram]

### Container View
[C4 Level 2 diagram]

### Component View
[C4 Level 3 diagram]

## Architecture Decision Records
[Key decisions made]

## Recommendations
[Architecture improvement suggestions]

## Appendix: Verification Notes
[Any unverified items]
```

## Important Notes

1. **Architecture Focus**: Stay focused on architectural aspects, not implementation details
2. **Holistic View**: Analyze frontend and backend together for complete picture
3. **Diagram Generation**: Use Mermaid syntax for all architecture diagrams
4. **No Hallucination**: Only report what is verifiable in the actual codebase
5. **Pattern Recognition**: Identify patterns based on code structure, not assumptions
6. **User Guidance**: Prompt user for complete codebase if only partial code provided
7. **Always Ask for Documentation**: After analysis, prompt about generating documentation
