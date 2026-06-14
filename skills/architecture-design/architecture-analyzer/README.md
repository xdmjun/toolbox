# Architecture Analyzer

A skill for analyzing project architecture across 5 dimensions: Technical, Data, Business, Application, and Code Architecture.

## Features

- **Five Architecture Dimensions**: Technical, Data, Business, Application, Code
- **Architecture Patterns Detection**: MVC, Layered, Hexagonal, Microservices, etc.
- **C4 Model Diagrams**: System Context, Container, Component views
- **Architecture Decision Records (ADR)**: Document key architecture decisions
- **Mermaid Diagrams**: Auto-generated architecture diagrams

## Installation

```bash
npx skills add xdmjun/architecture-analyzer
```

## Usage

Invoke this skill when you need to:
- Understand an unfamiliar project's architecture
- Generate architecture documentation
- See how different parts of a system connect

## What This Skill Analyzes

| Dimension | Focus |
|-----------|-------|
| **Technical Architecture** | Tech stack, frameworks, infrastructure |
| **Data Architecture** | Data models, data flow, storage solutions |
| **Business Architecture** | Business domains, processes, rules |
| **Application Architecture** | Services, components, APIs |
| **Code Architecture** | Code organization, design patterns |

## What This Skill Does NOT Cover

| Area | Recommended Tool |
|------|------------------|
| Detailed project statistics | `project-analyzer` skill |
| Code quality & linting | Code review tools |
| Build/test commands | package.json scripts, Makefile |
| Dependency health | `npm outdated`, `pip-audit` |

## Output

Generates comprehensive architecture documentation including:
- Technology Stack Analysis
- Data Flow Diagrams
- Business Process Flows
- Application Architecture Diagrams
- C4 Model Views
- Architecture Decision Records

## License

MIT
