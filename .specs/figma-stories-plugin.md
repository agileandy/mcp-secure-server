# Figma-to-Agile-Stories MCP Plugin

A Model Context Protocol (MCP) plugin that converts Figma designs into structured agile user stories with AI-enhanced descriptions. Generates well-formatted user stories from Figma component data, supporting both template-based and AI-powered story generation.

## Features

- **Figma Integration**: Extract component data from Figma files via REST API
- **Epic Creation**: Group stories by Figma pages (epics) or custom grouping
- **Dual Generation Modes**:
  - Template-based: Rule-based story generation from component metadata
  - AI-enhanced: LLM-powered story generation with context awareness
- **Multi-Format Output**: Generate stories in Markdown, JSON, or plain text
- **Interactive Mode**: Preview and customize stories before saving
- **Corporate Ready**: Security-first design with local processing

## Architecture

```
src/plugins/figma_stories/
├── __init__.py           # Main plugin class (FigmaStoriesPlugin)
├── models.py             # Data models (UserStory, Epic, Component, StoryConfig)
├── config.py             # Configuration loading
├── figma_client.py       # Figma REST API client
├── story_generator.py    # Story generation engine
├── ai_client.py          # AI integration (OpenRouter/OpenAI-compatible)
├── markdown_writer.py    # Markdown output generation
├── templates.py          # Prompt/story templates
└── exceptions.py         # Custom exceptions
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `FIGMA_API_TOKEN` | Figma personal access token | Yes |
| `AI_API_KEY` | AI API key (OpenRouter/OpenAI) | No (for template mode) |

### YAML Configuration

```yaml
figma_stories:
  output_dir: "${HOME}/projects/user-stories"
  ai:
    provider: "openrouter"
    model: "nvidia/nemotron-3-nano-30b-a3b:free"
    temperature: 0.7
    max_tokens: 1024
  defaults:
    story_format: "given_when_then"
    epic_source: "page_name"
    template_mode: false
```

## MCP Tools

### configure

Configure plugin settings for the current session.

**Input:**
```json
{
  "output_dir": "/path/to/output",
  "ai_enabled": true,
  "ai_model": "nvidia/nemotron-3-nano-30b-a3b:free",
  "story_format": "given_when_then"
}
```

### generate

Generate agile user stories from a Figma file.

**Input:**
```json
{
  "figma_file_key": "abc123xyz",
  "page_names": ["Login", "Dashboard"],
  "output_format": "markdown",
  "preview_only": false
}
```

**Output:**
```json
{
  "stories_generated": 5,
  "epics_created": 2,
  "output_path": "/home/user/stories/login-stories.md"
}
```

### preview

Preview generated stories without saving.

**Input:**
```json
{
  "figma_file_key": "abc123xyz",
  "page_names": ["Login"]
}
```

### list_pages

List available pages in a Figma file.

**Input:**
```json
{
  "figma_file_key": "abc123xyz"
}
```

### get_status

Check plugin status and configuration.

**Input:**
```json
{}
```

## Story Format

### Given-When-Then (Default)

```markdown
## Login Button (LOGIN-001)

**As a** user,
**I want to** click the login button to authenticate,
**So that** I can access my account.

### Acceptance Criteria

GIVEN the user is on the login page
WHEN the user clicks the login button
THEN the login form should be submitted

GIVEN the user has entered valid credentials
WHEN the user clicks the login button
THEN the user should be redirected to the dashboard
```

### User Story Format

```markdown
## Login Button (LOGIN-001)

**As a** user
**I want to** click the login button to authenticate
**So that** I can access my account

### Description
Interactive button component with primary styling. Triggers authentication flow on click.

### Technical Notes
- Component: Button
- Props: onClick, disabled, variant
```

## Component Mapping

| Figma Component Type | User Story Template |
|---------------------|---------------------|
| Button | "As a user, I want to [action] so that [benefit]" |
| Input | "As a user, I want to enter [data] so that [purpose]" |
| Card | "As a user, I want to view [content] so that [benefit]" |
| Navigation | "As a user, I want to navigate to [destination] so that [goal]" |
| Modal | "As a user, I want to see [information] in a modal so that [reason]" |
| Form | "As a user, I want to submit [data] so that [outcome]" |
| List | "As a user, I want to browse [items] so that [goal]" |
| Table | "As a user, I want to view [data] in a table so that [purpose]" |

## AI Integration

### Supported Providers

- **OpenRouter**: Recommended for corporate environments
- **OpenAI**: Standard API compatibility
- **Ollama**: Local model inference

### Prompt Template

```
You are an agile product owner. Convert the following Figma component into a well-written user story.

Component: {component_name}
Type: {component_type}
Description: {component_description}
Properties: {component_properties}

Requirements:
1. Write from user perspective (As a...)
2. Define clear acceptance criteria (Given-When-Then)
3. Keep it concise but complete
4. Focus on user value, not implementation

Output format:
## {story_title}

**As a** {user_role}
**I want to** {action}
**So that** {benefit}

### Acceptance Criteria

GIVEN [context]
WHEN [event]
THEN [outcome]

...
```

## Usage Examples

### Basic Story Generation

```python
# Configure plugin
await plugin.configure(output_dir="./stories", story_format="given_when_then")

# Generate stories from Figma file
result = await plugin.generate(
    figma_file_key="abc123",
    page_names=["Authentication"],
    output_format="markdown"
)

print(f"Generated {result['stories_generated']} stories")
```

### Interactive Preview

```python
# Preview without saving
preview = await plugin.preview(
    figma_file_key="abc123",
    page_names=["Dashboard"]
)

for story in preview["stories"]:
    print(story["title"])
    print(story["content"])
```

## Security Considerations

1. **API Tokens**: Store in environment variables, never in config files
2. **Network Access**: Figma API endpoints must be allowlisted in security policy
3. **File Output**: Output directories must be in allowed paths
4. **Data Privacy**: Figma file content processed locally, not stored externally

## Dependencies

- `httpx`: Async HTTP client for Figma API
- `pyyaml`: YAML configuration parsing
- `openai`: AI API client (optional, for AI mode)

## Testing

```bash
# Run all tests
uv run pytest tests/test_figma_stories/

# Run with coverage
uv run pytest --cov=src/plugins/figma_stories tests/test_figma_stories/
```
