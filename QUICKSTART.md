# 🚀 Google Tasks MCP - Quick Start Guide

Get your Google Tasks MCP server running in 5 minutes!

## 📋 What You'll Get

A powerful MCP server that lets Claude (or any LLM) manage your Google Tasks:

- Create, update, delete tasks and task lists
- Natural language task creation ("Buy milk tomorrow")
- Bulk operations and smart search
- Time-based task summaries (today, overdue, this week)

## ⚡ Quick Setup (3 Steps)

### Step 1: Get Google Credentials (2 minutes)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a Project" → "New Project" → Name it "Tasks MCP" → Create
3. In the search bar, type "Tasks API" → Click on it → **ENABLE**
4. Go to menu → "APIs & Services" → "Credentials"
5. Click "+ CREATE CREDENTIALS" → "OAuth client ID"
6. If prompted, configure consent screen:
   - Choose "External" → Create
   - Fill in App name: "Tasks MCP"
   - Add your email → Save and Continue (skip optional fields)
7. Back to Create OAuth client:
   - Application type: **Desktop app**
   - Name: "Tasks MCP Client"
   - Click CREATE
8. **DOWNLOAD JSON** → Save the file

### Step 2: Create Python Environment (1 minute)

```bash
# Create a virtual environment (recommended)
python3 -m venv venv

source venv/bin/activate

```

### Step 3: Install & Configure (1 minute)

```bash
# Install dependencies
pip install -r requirements.txt

# Create config directory
mkdir -p ~/.google_tasks_mcp

# Move your downloaded credentials
mv ~/Downloads/client_secret_*.json ~/.google_tasks_mcp/credentials.json

# Run setup (optional but recommended)
python setup.py
```

### Step 3: Test & Run (2 minutes)

```bash
# First run - will open browser for authorization
python google_tasks_mcp.py

# Authorize in browser, then press Ctrl+C to stop

# Test everything works
python test_server.py

# You're ready! 🎉
```

## 🔧 Add to Claude Desktop

Add to your Claude config file:

**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "google-tasks": {
      "command": "/Users/omshejul/Desktop/files/venv/bin/python",
      "args": ["/Users/omshejul/Desktop/files/google_tasks_mcp.py"]
    }
  }
}
```

Restart Claude Desktop after adding.

## 💬 Example Commands in Claude

Once connected, try these in Claude:

```
"Show me my tasks for today"
"Create a task: Call dentist tomorrow at 2pm"
"Mark task XYZ as completed"
"Search for all tasks with 'meeting'"
"Create a new task list called 'Vacation Planning'"
"Show me overdue tasks"
"Bulk create tasks: Plan trip, Book flights, Reserve hotel, Pack luggage"
```

## 🔍 Troubleshooting

### "Authentication failed"

- Check credentials.json exists in `~/.google_tasks_mcp/`
- Ensure Tasks API is enabled in Google Cloud Console
- Delete `~/.google_tasks_mcp/token.json` and re-authenticate

### "No module named 'fastmcp'"

```bash
pip install fastmcp google-auth google-auth-oauthlib google-api-python-client
```

### "Server not responding in Claude"

- Check the path in claude_desktop_config.json is absolute
- Restart Claude Desktop
- Test server works: `python google_tasks_mcp.py`

## 📚 Available Tools

### Essential Tools

- `create_task` - Add a new task
- `list_tasks` - View your tasks
- `update_task` - Modify task details
- `delete_task` - Remove a task
- `search_tasks` - Find tasks across all lists

### Workflow Tools

- `quick_add_task` - Natural language task creation
- `bulk_create_tasks` - Create multiple tasks at once
- `get_task_summary` - View tasks by time range
- `clear_completed_tasks` - Bulk remove completed tasks

### List Management

- `create_task_list` - New task list
- `list_task_lists` - View all lists
- `update_task_list` - Rename a list
- `delete_task_list` - Remove a list

## 🎯 Pro Tips

1. **Natural Language**: Use `quick_add_task` with phrases like "Meeting tomorrow at 3pm"

2. **Bulk Operations**: Create project tasks all at once:

   ```
   Bulk create: "Design mockup, Get feedback, Implement changes, Test, Deploy"
   ```

3. **Smart Filtering**: List tasks with specific criteria:

   ```
   "Show tasks due this week but not completed"
   ```

4. **Task Hierarchies**: Create subtasks by specifying parent_task_id

5. **Time Management**: Use `get_task_summary` for daily planning:
   ```
   "What tasks are overdue?" or "Show today's tasks"
   ```

## 🆘 Need Help?

- Check the full [README.md](README.md) for detailed documentation
- Run `python test_server.py` to diagnose issues
- Verify setup with `python setup.py`

## 🎉 Success Checklist

- [ ] Google Cloud project created
- [ ] Tasks API enabled
- [ ] OAuth credentials downloaded
- [ ] Dependencies installed
- [ ] First authentication completed
- [ ] Test script passes
- [ ] Added to Claude Desktop
- [ ] Created your first task through Claude!

---

**Ready to boost your productivity?** Start managing your tasks with natural language! 🚀
