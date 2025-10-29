# Google Tasks MCP Server

A comprehensive Model Context Protocol (MCP) server for Google Tasks that enables LLMs to manage tasks and task lists through well-designed, workflow-oriented tools.

## Features

This MCP server provides intelligent, workflow-oriented tools for Google Tasks management:

### Task List Management

- **Create, update, delete, and list** task lists
- Organize tasks into projects and categories

### Task Operations

- **Create tasks** with titles, notes, due dates, and hierarchical structure (subtasks)
- **List tasks** with powerful filtering (date ranges, status, pagination)
- **Update tasks** - modify title, notes, status, due dates
- **Delete tasks** permanently
- **Move tasks** between positions and parents
- **Clear completed tasks** in bulk

### Workflow Tools

- **Quick Add** - Natural language task creation
- **Bulk Create** - Create multiple tasks at once
- **Search Tasks** - Find tasks across all lists
- **Task Summary** - Get organized views by time range (today, tomorrow, week, overdue)

## Prerequisites

1. **Python 3.8+** installed on your system
2. **Google Cloud Project** with Tasks API enabled
3. **OAuth 2.0 Credentials** for desktop application

## Setup Instructions

### Step 1: Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Tasks API:

   - Go to "APIs & Services" > "Library"
   - Search for "Tasks API"
   - Click "Enable"

4. Create OAuth 2.0 Credentials:

   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" as the application type
   - Give it a name (e.g., "Google Tasks MCP")
   - Download the credentials JSON file

5. Create the configuration directory:

   ```bash
   mkdir -p ~/.google_tasks_mcp
   ```

6. Save the downloaded credentials file as:
   ```
   ~/.google_tasks_mcp/credentials.json
   ```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: First Run & Authentication

Run the server for the first time to authenticate:

```bash
python google_tasks_mcp.py
```

This will:

1. Open a browser window for Google authentication
2. Ask you to authorize the application
3. Save the authentication token for future use

## Configuration

### For Claude Desktop App

Add this to your Claude desktop configuration file:

**MacOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "google-tasks": {
      "command": "python",
      "args": ["/path/to/google_tasks_mcp.py"],
      "env": {}
    }
  }
}
```

Replace `/path/to/google_tasks_mcp.py` with the actual path to the server file.

### For Other MCP Clients

The server runs on stdio transport by default:

```bash
python google_tasks_mcp.py
```

### Running as a Remote (HTTP/SSE) MCP Server

This server can also run remotely over HTTP/SSE. Control it with environment variables:

- `MCP_MODE`: set to `remote` (enables HTTP/SSE). Default: `stdio`.
- `MCP_HOST`: bind host (e.g., `0.0.0.0`). Default: `0.0.0.0`.
- `MCP_PORT`: port number. Default: `8000`.
- `MCP_PATH`: SSE endpoint path. Default: `/sse`.

Example:

```bash
source /Users/omshejul/python-env/venv/bin/python

export MCP_MODE=remote
export MCP_HOST=0.0.0.0
export MCP_PORT=8000
export MCP_PATH=/sse
python google_tasks_mcp.py
```

#### Claude Remote Config (SSE)

Claude Desktop typically expects stdio servers. Use the `mcp-remote` adapter to connect via SSE. Add an entry like this to the `mcpServers` section of your Claude config:

```json
{
  "mcpServers": {
    "google-tasks": {
      "command": "npx",
      "args": ["-y", "mcp-remote@latest", "http://YOUR_HOST:8000/sse"]
    }
  }
}
```

Replace `YOUR_HOST` and port as needed. Ensure the server is reachable from the client.

#### Optional: Require a Bearer Token

Set an auth token for the remote server so clients must present `Authorization: Bearer <token>`:

```bash
export MCP_AUTH_TOKEN=REPLACE_ME_SECRET
export MCP_MODE=remote
export MCP_HOST=0.0.0.0
export MCP_PORT=8000
export MCP_PATH=/sse
/Users/omshejul/python-env/venv/bin/python google_tasks_mcp.py
```

For Claude with `mcp-remote`, pass the header and keep the secret in an env var:

```json
{
  "mcpServers": {
    "google-tasks": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest",
        "http://YOUR_HOST:8000/sse",
        "--header",
        "Authorization:Bearer ${GOOGLE_TASKS_MCP_TOKEN}"
      ],
      "env": {
        "GOOGLE_TASKS_MCP_TOKEN": "REPLACE_ME_SECRET"
      }
    }
  }
}
```

## Available Tools

### Task List Management

#### `create_task_list`

Create a new task list for organizing related tasks.

```
Input: title (string)
Returns: Created task list details
```

#### `list_task_lists`

List all task lists with pagination support.

```
Input:
- max_results (1-50, default: 20)
- page_token (optional)
- response_format (json/markdown/concise/detailed)
Returns: List of task lists
```

#### `update_task_list`

Rename an existing task list.

```
Input:
- tasklist_id (string)
- title (string)
Returns: Updated task list
```

#### `delete_task_list`

⚠️ Permanently delete a task list and all its tasks.

```
Input: tasklist_id (string)
Returns: Confirmation
```

### Task Operations

#### `create_task`

Create a new task with optional details.

```
Input:
- title (string, required)
- notes (string, optional)
- due_date (ISO format YYYY-MM-DD, optional)
- tasklist_id (default: "@default")
- parent_task_id (optional, for subtasks)
Returns: Created task details
```

#### `list_tasks`

List tasks with comprehensive filtering options.

```
Input:
- tasklist_id (default: "@default")
- max_results (1-100, default: 30)
- show_completed (boolean, default: false)
- show_deleted (boolean, default: false)
- due_min/due_max (ISO dates for filtering)
- completed_min/completed_max (ISO dates)
- page_token (for pagination)
- response_format (json/markdown/concise/detailed)
Returns: Filtered task list
```

#### `update_task`

Modify task properties.

```
Input:
- task_id (string, required)
- tasklist_id (default: "@default")
- title (optional)
- notes (optional)
- status (needsAction/completed, optional)
- due_date (ISO format or "clear", optional)
Returns: Updated task
```

#### `delete_task`

⚠️ Permanently delete a task.

```
Input:
- task_id (string)
- tasklist_id (default: "@default")
Returns: Confirmation
```

#### `move_task`

Reorganize task position or hierarchy.

```
Input:
- task_id (string)
- tasklist_id (default: "@default")
- parent_task_id (optional)
- previous_task_id (optional)
Returns: Moved task details
```

#### `clear_completed_tasks`

⚠️ Remove all completed tasks from a list.

```
Input:
- tasklist_id (default: "@default")
Returns: Confirmation
```

### Workflow Tools

#### `quick_add_task`

Create tasks using natural language.

```
Input:
- text (string, e.g., "Buy milk tomorrow")
- tasklist_id (default: "@default")
Returns: Created task
```

Examples:

- "Meeting with John tomorrow"
- "Urgent: Fix login bug"
- "Submit report next week"

#### `bulk_create_tasks`

Create multiple tasks at once.

```
Input:
- tasks (list of strings, 1-50 items)
- tasklist_id (default: "@default")
- due_date (optional, applies to all)
Returns: Creation summary
```

#### `search_tasks`

Find tasks across all task lists.

```
Input:
- query (string)
- include_completed (boolean, default: false)
- max_results (1-50, default: 20)
- response_format (json/markdown/concise/detailed)
Returns: Matching tasks from all lists
```

#### `get_task_summary`

Get organized task overview by time range.

```
Input:
- time_range (today/tomorrow/week/overdue/all)
- include_completed (boolean, default: false)
- response_format (concise/markdown/detailed)
Returns: Task summary for time period
```

## Usage Examples

### Daily Planning Workflow

1. "Get my task summary for today"
2. "Show me overdue tasks"
3. "Create task 'Review quarterly report' due tomorrow"
4. "Mark task [ID] as completed"

### Project Setup Workflow

1. "Create a task list called 'Website Redesign'"
2. "Bulk create tasks: ['Design mockups', 'Get client feedback', 'Implement changes', 'Testing', 'Deploy']"
3. "Set due date 2024-02-15 for all tasks"

### Task Search Workflow

1. "Search for tasks containing 'meeting'"
2. "Find all tasks with 'urgent' in the title"
3. "Show completed tasks from last week"

## Response Formats

The server supports multiple response formats:

- **JSON**: Raw API response for processing
- **Markdown**: Formatted for readability
- **Concise**: Minimal information for quick viewing
- **Detailed**: Complete task information including IDs

## Error Handling

The server provides clear, actionable error messages:

- Authentication errors with setup instructions
- Invalid input with specific guidance
- API errors with suggested fixes
- Rate limiting information when applicable

## Security

- OAuth 2.0 tokens are stored locally in `~/.google_tasks_mcp/token.json`
- Credentials never leave your local machine
- Token refresh is handled automatically
- Scoped access only to Google Tasks

## Troubleshooting

### Authentication Issues

- Ensure credentials.json is in the correct location
- Delete token.json to re-authenticate
- Check that Tasks API is enabled in Google Cloud Console

### Permission Errors

- Verify the Google account has access to Google Tasks
- Check OAuth consent screen is configured
- Ensure correct scopes are authorized

### Connection Issues

- Verify internet connectivity
- Check firewall settings
- Ensure Google services are accessible

## Development

### Adding New Tools

1. Define Pydantic model for input validation
2. Implement tool function with @mcp.tool decorator
3. Add comprehensive docstring and error handling
4. Update README documentation

### Testing

Run the server in development mode:

```bash
python google_tasks_mcp.py --debug
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Support

For issues or questions:

1. Check the troubleshooting section
2. Review Google Tasks API documentation
3. Open an issue with detailed error information

## Acknowledgments

Built with:

- [FastMCP](https://github.com/jlowin/fastmcp) - MCP framework
- [Google Tasks API](https://developers.google.com/tasks) - Task management
- [Model Context Protocol](https://modelcontextprotocol.io) - LLM integration standard
