#!/usr/bin/env python3
"""
Google Tasks MCP Server

A comprehensive MCP server for Google Tasks that enables LLMs to manage
tasks and task lists through well-designed, workflow-oriented tools.

This server uses OAuth 2.0 for authentication and provides tools optimized
for agent workflows rather than simple API wrappers.
"""

import os
import json
import asyncio
import logging
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from fastmcp import FastMCP

# Google API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ==========================================
# CONFIGURATION
# ==========================================

# OAuth 2.0 scopes for Google Tasks
SCOPES = ['https://www.googleapis.com/auth/tasks']

# Character limits for responses
CHARACTER_LIMIT = 25000
MAX_TASKS_PER_RESPONSE = 100
MAX_LISTS_PER_RESPONSE = 50

# Token storage path
TOKEN_PATH = os.path.expanduser('~/.google_tasks_mcp/token.json')
CREDENTIALS_PATH = os.path.expanduser('~/.google_tasks_mcp/credentials.json')

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==========================================
# PYDANTIC MODELS
# ==========================================

class ResponseFormat(str, Enum):
    """Response format options"""
    JSON = "json"
    MARKDOWN = "markdown"
    CONCISE = "concise"
    DETAILED = "detailed"

class TaskStatus(str, Enum):
    """Task status options"""
    NEEDS_ACTION = "needsAction"
    COMPLETED = "completed"

class TaskPriority(str, Enum):
    """Task priority levels for filtering"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ALL = "all"

# --- Task List Models ---

class CreateTaskListInput(BaseModel):
    """Input model for creating a task list"""
    title: str = Field(..., description="Title of the new task list", min_length=1, max_length=200)

class ListTaskListsInput(BaseModel):
    """Input model for listing task lists"""
    max_results: int = Field(default=20, description="Maximum number of task lists to return (1-50)", ge=1, le=MAX_LISTS_PER_RESPONSE)
    page_token: Optional[str] = Field(None, description="Token for pagination from previous response")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Response format")

class UpdateTaskListInput(BaseModel):
    """Input model for updating a task list"""
    tasklist_id: str = Field(..., description="ID of the task list to update")
    title: str = Field(..., description="New title for the task list", min_length=1, max_length=200)

class DeleteTaskListInput(BaseModel):
    """Input model for deleting a task list"""
    tasklist_id: str = Field(..., description="ID of the task list to delete")

# --- Task Models ---

class CreateTaskInput(BaseModel):
    """Input model for creating a task"""
    title: str = Field(..., description="Title of the task", min_length=1, max_length=500)
    notes: Optional[str] = Field(None, description="Additional notes/description for the task", max_length=8192)
    due_date: Optional[str] = Field(None, description="Due date in ISO format (YYYY-MM-DD)")
    tasklist_id: Optional[str] = Field(default="@default", description="ID of task list to add to (default: primary list)")
    parent_task_id: Optional[str] = Field(None, description="ID of parent task to create this as a subtask")
    
    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v: Optional[str]) -> Optional[str]:
        if v:
            try:
                datetime.fromisoformat(v)
            except ValueError:
                raise ValueError("Due date must be in ISO format (YYYY-MM-DD)")
        return v

class ListTasksInput(BaseModel):
    """Input model for listing tasks"""
    tasklist_id: Optional[str] = Field(default="@default", description="ID of task list (default: primary list)")
    max_results: int = Field(default=30, description="Maximum number of tasks to return (1-100)", ge=1, le=MAX_TASKS_PER_RESPONSE)
    show_completed: bool = Field(default=False, description="Include completed tasks in results")
    show_deleted: bool = Field(default=False, description="Include deleted tasks in results")
    show_hidden: bool = Field(default=False, description="Include hidden tasks in results")
    due_min: Optional[str] = Field(None, description="Minimum due date (ISO format) to filter tasks")
    due_max: Optional[str] = Field(None, description="Maximum due date (ISO format) to filter tasks")
    completed_min: Optional[str] = Field(None, description="Minimum completion date (ISO format)")
    completed_max: Optional[str] = Field(None, description="Maximum completion date (ISO format)")
    updated_min: Optional[str] = Field(None, description="Minimum last update date (ISO format)")
    page_token: Optional[str] = Field(None, description="Token for pagination from previous response")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Response format")

class UpdateTaskInput(BaseModel):
    """Input model for updating a task"""
    task_id: str = Field(..., description="ID of the task to update")
    tasklist_id: Optional[str] = Field(default="@default", description="ID of the task list containing the task")
    title: Optional[str] = Field(None, description="New title for the task", min_length=1, max_length=500)
    notes: Optional[str] = Field(None, description="New notes/description for the task", max_length=8192)
    status: Optional[TaskStatus] = Field(None, description="Task status (needsAction or completed)")
    due_date: Optional[str] = Field(None, description="New due date in ISO format (YYYY-MM-DD), or 'clear' to remove")

class DeleteTaskInput(BaseModel):
    """Input model for deleting a task"""
    task_id: str = Field(..., description="ID of the task to delete")
    tasklist_id: Optional[str] = Field(default="@default", description="ID of the task list containing the task")

class MoveTaskInput(BaseModel):
    """Input model for moving a task"""
    task_id: str = Field(..., description="ID of the task to move")
    tasklist_id: Optional[str] = Field(default="@default", description="ID of the task list containing the task")
    parent_task_id: Optional[str] = Field(None, description="ID of new parent task (null to move to root)")
    previous_task_id: Optional[str] = Field(None, description="ID of task to position after")

class ClearCompletedTasksInput(BaseModel):
    """Input model for clearing completed tasks"""
    tasklist_id: Optional[str] = Field(default="@default", description="ID of the task list to clear completed tasks from")

# --- Workflow Models ---

class QuickAddTaskInput(BaseModel):
    """Input model for quickly adding a task with smart parsing"""
    text: str = Field(..., description="Natural language task description (e.g., 'Buy milk tomorrow', 'Meeting with John at 3pm on Friday')")
    tasklist_id: Optional[str] = Field(default="@default", description="ID of task list to add to")

class BulkCreateTasksInput(BaseModel):
    """Input model for creating multiple tasks at once"""
    tasks: List[str] = Field(..., description="List of task titles to create", min_length=1, max_length=50)
    tasklist_id: Optional[str] = Field(default="@default", description="ID of task list to add tasks to")
    due_date: Optional[str] = Field(None, description="Common due date for all tasks (ISO format)")

class SearchTasksInput(BaseModel):
    """Input model for searching tasks across all lists"""
    query: str = Field(..., description="Search query to match against task titles and notes", min_length=1)
    include_completed: bool = Field(default=False, description="Include completed tasks in search")
    max_results: int = Field(default=20, description="Maximum results to return", ge=1, le=50)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Response format")

class GetTaskSummaryInput(BaseModel):
    """Input model for getting a summary of tasks"""
    time_range: Literal["today", "tomorrow", "week", "overdue", "all"] = Field(
        default="today",
        description="Time range for task summary"
    )
    include_completed: bool = Field(default=False, description="Include completed tasks in summary")
    response_format: ResponseFormat = Field(default=ResponseFormat.CONCISE, description="Response format")

# ==========================================
# AUTHENTICATION HELPER
# ==========================================

class GoogleTasksAuth:
    """Handle Google OAuth 2.0 authentication"""
    
    @staticmethod
    def get_credentials() -> Optional[Credentials]:
        """Get valid user credentials from storage or initiate OAuth flow"""
        creds = None
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        
        # Load existing token
        if os.path.exists(TOKEN_PATH):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            except Exception as e:
                logger.error(f"Error loading credentials: {e}")
                creds = None
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(CREDENTIALS_PATH):
                    raise FileNotFoundError(
                        f"Credentials file not found at {CREDENTIALS_PATH}. "
                        "Please download OAuth 2.0 credentials from Google Cloud Console "
                        "and save them to this location."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
        
        return creds

# ==========================================
# GOOGLE TASKS CLIENT
# ==========================================

class GoogleTasksClient:
    """Client for interacting with Google Tasks API"""
    
    def __init__(self):
        self.service = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the Google Tasks service"""
        try:
            creds = GoogleTasksAuth.get_credentials()
            if creds:
                self.service = build('tasks', 'v1', credentials=creds)
            else:
                raise Exception("Failed to obtain credentials")
        except Exception as e:
            logger.error(f"Failed to initialize Google Tasks client: {e}")
            raise
    
    # --- Task List Operations ---
    
    async def create_tasklist(self, title: str) -> Dict[str, Any]:
        """Create a new task list"""
        try:
            body = {'title': title}
            result = self.service.tasklists().insert(body=body).execute()
            return result
        except HttpError as e:
            logger.error(f"Error creating task list: {e}")
            raise
    
    async def list_tasklists(self, max_results: int = 20, page_token: Optional[str] = None) -> Dict[str, Any]:
        """List task lists"""
        try:
            result = self.service.tasklists().list(
                maxResults=max_results,
                pageToken=page_token
            ).execute()
            return result
        except HttpError as e:
            logger.error(f"Error listing task lists: {e}")
            raise
    
    async def update_tasklist(self, tasklist_id: str, title: str) -> Dict[str, Any]:
        """Update a task list"""
        try:
            tasklist = self.service.tasklists().get(tasklist=tasklist_id).execute()
            tasklist['title'] = title
            result = self.service.tasklists().update(
                tasklist=tasklist_id,
                body=tasklist
            ).execute()
            return result
        except HttpError as e:
            logger.error(f"Error updating task list: {e}")
            raise
    
    async def delete_tasklist(self, tasklist_id: str) -> bool:
        """Delete a task list"""
        try:
            self.service.tasklists().delete(tasklist=tasklist_id).execute()
            return True
        except HttpError as e:
            logger.error(f"Error deleting task list: {e}")
            raise
    
    # --- Task Operations ---
    
    async def create_task(
        self,
        title: str,
        tasklist_id: str = "@default",
        notes: Optional[str] = None,
        due: Optional[str] = None,
        parent: Optional[str] = None,
        previous: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new task"""
        try:
            body = {'title': title}
            if notes:
                body['notes'] = notes
            if due:
                # Convert date to RFC 3339 format
                body['due'] = f"{due}T00:00:00.000Z"
            
            result = self.service.tasks().insert(
                tasklist=tasklist_id,
                body=body,
                parent=parent,
                previous=previous
            ).execute()
            return result
        except HttpError as e:
            logger.error(f"Error creating task: {e}")
            raise
    
    async def list_tasks(
        self,
        tasklist_id: str = "@default",
        **kwargs
    ) -> Dict[str, Any]:
        """List tasks in a task list"""
        try:
            # Build query parameters
            params = {
                'tasklist': tasklist_id,
                'maxResults': kwargs.get('max_results', 30),
                'showCompleted': kwargs.get('show_completed', False),
                'showDeleted': kwargs.get('show_deleted', False),
                'showHidden': kwargs.get('show_hidden', False)
            }
            
            # Add optional date filters
            if kwargs.get('due_min'):
                params['dueMin'] = f"{kwargs['due_min']}T00:00:00.000Z"
            if kwargs.get('due_max'):
                params['dueMax'] = f"{kwargs['due_max']}T23:59:59.999Z"
            if kwargs.get('completed_min'):
                params['completedMin'] = f"{kwargs['completed_min']}T00:00:00.000Z"
            if kwargs.get('completed_max'):
                params['completedMax'] = f"{kwargs['completed_max']}T23:59:59.999Z"
            if kwargs.get('updated_min'):
                params['updatedMin'] = f"{kwargs['updated_min']}T00:00:00.000Z"
            if kwargs.get('page_token'):
                params['pageToken'] = kwargs['page_token']
            
            result = self.service.tasks().list(**params).execute()
            return result
        except HttpError as e:
            logger.error(f"Error listing tasks: {e}")
            raise
    
    async def update_task(
        self,
        task_id: str,
        tasklist_id: str = "@default",
        **updates
    ) -> Dict[str, Any]:
        """Update a task"""
        try:
            # Get current task
            task = self.service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
            
            # Apply updates
            if 'title' in updates and updates['title']:
                task['title'] = updates['title']
            if 'notes' in updates and updates['notes']:
                task['notes'] = updates['notes']
            if 'status' in updates and updates['status']:
                task['status'] = updates['status']
            if 'due_date' in updates:
                if updates['due_date'] == 'clear':
                    task.pop('due', None)
                elif updates['due_date']:
                    task['due'] = f"{updates['due_date']}T00:00:00.000Z"
            
            result = self.service.tasks().update(
                tasklist=tasklist_id,
                task=task_id,
                body=task
            ).execute()
            return result
        except HttpError as e:
            logger.error(f"Error updating task: {e}")
            raise
    
    async def delete_task(self, task_id: str, tasklist_id: str = "@default") -> bool:
        """Delete a task"""
        try:
            self.service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()
            return True
        except HttpError as e:
            logger.error(f"Error deleting task: {e}")
            raise
    
    async def move_task(
        self,
        task_id: str,
        tasklist_id: str = "@default",
        parent: Optional[str] = None,
        previous: Optional[str] = None
    ) -> Dict[str, Any]:
        """Move a task to a new position"""
        try:
            result = self.service.tasks().move(
                tasklist=tasklist_id,
                task=task_id,
                parent=parent,
                previous=previous
            ).execute()
            return result
        except HttpError as e:
            logger.error(f"Error moving task: {e}")
            raise
    
    async def clear_completed(self, tasklist_id: str = "@default") -> bool:
        """Clear all completed tasks from a list"""
        try:
            self.service.tasks().clear(tasklist=tasklist_id).execute()
            return True
        except HttpError as e:
            logger.error(f"Error clearing completed tasks: {e}")
            raise

# ==========================================
# RESPONSE FORMATTERS
# ==========================================

class ResponseFormatter:
    """Format API responses for different output types"""
    
    @staticmethod
    def format_task(task: Dict[str, Any], format_type: ResponseFormat) -> str:
        """Format a single task"""
        if format_type == ResponseFormat.JSON:
            return json.dumps(task, indent=2)
        
        # Extract key fields
        title = task.get('title', 'Untitled')
        notes = task.get('notes', '')
        status = task.get('status', 'needsAction')
        due = task.get('due', '')
        
        # Parse due date if present
        due_str = ""
        if due:
            try:
                due_date = datetime.fromisoformat(due.replace('Z', '+00:00'))
                due_str = due_date.strftime('%Y-%m-%d')
            except:
                due_str = due
        
        if format_type == ResponseFormat.CONCISE:
            status_emoji = "✅" if status == "completed" else "⏳"
            due_part = f" 📅 {due_str}" if due_str else ""
            return f"{status_emoji} {title}{due_part}"
        
        # Markdown format (default and detailed)
        status_emoji = "✅" if status == "completed" else "⏳"
        result = f"### {status_emoji} {title}\n"
        
        if format_type == ResponseFormat.DETAILED:
            if notes:
                result += f"**Notes:** {notes}\n"
            if due_str:
                result += f"**Due:** {due_str}\n"
            result += f"**Status:** {status}\n"
            result += f"**ID:** {task.get('id', 'N/A')}\n"
        else:  # Standard markdown
            if notes:
                result += f"> {notes}\n"
            if due_str:
                result += f"📅 **Due:** {due_str}\n"
        
        return result
    
    @staticmethod
    def format_task_list(tasklist: Dict[str, Any], format_type: ResponseFormat) -> str:
        """Format a task list"""
        if format_type == ResponseFormat.JSON:
            return json.dumps(tasklist, indent=2)
        
        title = tasklist.get('title', 'Untitled')
        list_id = tasklist.get('id', 'N/A')
        
        if format_type == ResponseFormat.CONCISE:
            return f"📋 {title}"
        
        # Markdown format
        result = f"## 📋 {title}\n"
        if format_type == ResponseFormat.DETAILED:
            result += f"**ID:** {list_id}\n"
            updated = tasklist.get('updated', '')
            if updated:
                result += f"**Updated:** {updated}\n"
        
        return result
    
    @staticmethod
    def format_multiple_tasks(tasks: List[Dict[str, Any]], format_type: ResponseFormat, title: str = "Tasks") -> str:
        """Format multiple tasks"""
        if not tasks:
            return "No tasks found."
        
        if format_type == ResponseFormat.JSON:
            return json.dumps(tasks, indent=2)
        
        result = f"# {title}\n\n"
        
        if format_type == ResponseFormat.CONCISE:
            for task in tasks:
                result += ResponseFormatter.format_task(task, ResponseFormat.CONCISE) + "\n"
        else:
            for i, task in enumerate(tasks, 1):
                if i > 1:
                    result += "\n---\n\n"
                result += ResponseFormatter.format_task(task, format_type)
        
        # Truncate if too long
        if len(result) > CHARACTER_LIMIT:
            result = result[:CHARACTER_LIMIT - 100] + "\n\n... (truncated due to length)"
        
        return result

# ==========================================
# MCP SERVER IMPLEMENTATION
# ==========================================

# Initialize MCP server
mcp = FastMCP("google-tasks-mcp", version="1.0.0")
mcp.description = "Comprehensive Google Tasks management with workflow-oriented tools"

# Initialize Google Tasks client
tasks_client = GoogleTasksClient()

# ==========================================
# TASK LIST TOOLS
# ==========================================

@mcp.tool(
    description="""Create a new task list in Google Tasks.
    
    Use this tool when you need to organize tasks into a new category or project.
    Task lists help group related tasks together for better organization.
    
    Returns: The created task list with its ID for future operations."""
)
async def create_task_list(input: CreateTaskListInput) -> str:
    """Create a new task list"""
    try:
        result = await tasks_client.create_tasklist(input.title)
        return ResponseFormatter.format_task_list(result, ResponseFormat.MARKDOWN)
    except Exception as e:
        return f"Error creating task list: {str(e)}. Please check your authentication and try again."

@mcp.tool(
    description="""List all task lists in the user's Google Tasks account.
    
    Retrieves task lists with pagination support. Use this to discover available
    task lists before performing operations on specific lists.
    
    Returns: List of task lists with their IDs and titles."""
)
async def list_task_lists(input: ListTaskListsInput) -> str:
    """List all task lists"""
    try:
        result = await tasks_client.list_tasklists(
            max_results=input.max_results,
            page_token=input.page_token
        )
        
        lists = result.get('items', [])
        if not lists:
            return "No task lists found."
        
        if input.response_format == ResponseFormat.JSON:
            return json.dumps(result, indent=2)
        
        output = "# Task Lists\n\n"
        for task_list in lists:
            output += ResponseFormatter.format_task_list(task_list, input.response_format)
            output += "\n"
        
        if result.get('nextPageToken'):
            output += f"\n**More results available.** Use page_token: `{result['nextPageToken']}` to get the next page."
        
        return output
    except Exception as e:
        return f"Error listing task lists: {str(e)}. Please check your authentication and try again."

@mcp.tool(
    description="""Update the title of an existing task list.
    
    Use this to rename a task list to better reflect its purpose or content.
    
    Returns: The updated task list information."""
)
async def update_task_list(input: UpdateTaskListInput) -> str:
    """Update a task list"""
    try:
        result = await tasks_client.update_tasklist(input.tasklist_id, input.title)
        return f"✅ Task list updated successfully!\n\n{ResponseFormatter.format_task_list(result, ResponseFormat.MARKDOWN)}"
    except Exception as e:
        return f"Error updating task list: {str(e)}. Please verify the task list ID and try again."

@mcp.tool(
    description="""Delete a task list permanently.
    
    ⚠️ WARNING: This will permanently delete the task list and all tasks within it.
    This action cannot be undone.
    
    Returns: Confirmation of deletion."""
)
async def delete_task_list(input: DeleteTaskListInput) -> str:
    """Delete a task list"""
    try:
        await tasks_client.delete_tasklist(input.tasklist_id)
        return f"✅ Task list '{input.tasklist_id}' has been permanently deleted."
    except Exception as e:
        return f"Error deleting task list: {str(e)}. Please verify the task list ID and try again."

# ==========================================
# TASK MANAGEMENT TOOLS
# ==========================================

@mcp.tool(
    description="""Create a new task in Google Tasks.
    
    Creates a task with optional notes, due date, and can be added as a subtask
    to an existing task. Tasks are added to the default list unless specified.
    
    Examples:
    - Simple task: "Buy groceries"
    - With due date: "Submit report" due on 2024-01-15
    - As subtask: Create under a parent task for hierarchical organization
    
    Returns: The created task with its ID for future operations."""
)
async def create_task(input: CreateTaskInput) -> str:
    """Create a new task"""
    try:
        result = await tasks_client.create_task(
            title=input.title,
            tasklist_id=input.tasklist_id,
            notes=input.notes,
            due=input.due_date,
            parent=input.parent_task_id
        )
        return f"✅ Task created successfully!\n\n{ResponseFormatter.format_task(result, ResponseFormat.DETAILED)}"
    except Exception as e:
        return f"Error creating task: {str(e)}. Please check your input and try again."

@mcp.tool(
    description="""List tasks from a specific task list with powerful filtering options.
    
    Retrieve tasks with various filters including:
    - Date ranges (due dates, completion dates, update dates)
    - Status filters (show/hide completed, deleted, hidden tasks)
    - Pagination for large task lists
    
    Use this to:
    - View upcoming tasks
    - Find overdue tasks
    - Review completed tasks
    - Search within a specific time range
    
    Returns: Filtered list of tasks matching your criteria."""
)
async def list_tasks(input: ListTasksInput) -> str:
    """List tasks with filtering options"""
    try:
        result = await tasks_client.list_tasks(
            tasklist_id=input.tasklist_id,
            max_results=input.max_results,
            show_completed=input.show_completed,
            show_deleted=input.show_deleted,
            show_hidden=input.show_hidden,
            due_min=input.due_min,
            due_max=input.due_max,
            completed_min=input.completed_min,
            completed_max=input.completed_max,
            updated_min=input.updated_min,
            page_token=input.page_token
        )
        
        tasks = result.get('items', [])
        if not tasks:
            return "No tasks found matching your criteria."
        
        title = f"Tasks from list '{input.tasklist_id}'"
        output = ResponseFormatter.format_multiple_tasks(tasks, input.response_format, title)
        
        if result.get('nextPageToken'):
            output += f"\n\n**More results available.** Use page_token: `{result['nextPageToken']}` to get the next page."
        
        return output
    except Exception as e:
        return f"Error listing tasks: {str(e)}. Please check your filters and try again."

@mcp.tool(
    description="""Update an existing task's properties.
    
    Modify task attributes including:
    - Title: Rename the task
    - Notes: Add or update description
    - Status: Mark as completed or needs action
    - Due date: Set, update, or clear the due date
    
    Returns: The updated task information."""
)
async def update_task(input: UpdateTaskInput) -> str:
    """Update a task"""
    try:
        updates = {}
        if input.title:
            updates['title'] = input.title
        if input.notes is not None:
            updates['notes'] = input.notes
        if input.status:
            updates['status'] = input.status.value
        if input.due_date:
            updates['due_date'] = input.due_date
        
        result = await tasks_client.update_task(
            task_id=input.task_id,
            tasklist_id=input.tasklist_id,
            **updates
        )
        
        status_msg = "✅ completed" if input.status == TaskStatus.COMPLETED else "updated"
        return f"Task {status_msg} successfully!\n\n{ResponseFormatter.format_task(result, ResponseFormat.DETAILED)}"
    except Exception as e:
        return f"Error updating task: {str(e)}. Please verify the task ID and try again."

@mcp.tool(
    description="""Delete a task permanently.
    
    ⚠️ WARNING: This permanently removes the task. This action cannot be undone.
    
    Returns: Confirmation of deletion."""
)
async def delete_task(input: DeleteTaskInput) -> str:
    """Delete a task"""
    try:
        await tasks_client.delete_task(input.task_id, input.tasklist_id)
        return f"✅ Task '{input.task_id}' has been permanently deleted."
    except Exception as e:
        return f"Error deleting task: {str(e)}. Please verify the task ID and try again."

@mcp.tool(
    description="""Move a task to a different position or parent.
    
    Reorganize tasks by:
    - Moving to a different parent (make it a subtask)
    - Changing position within the list
    - Moving from subtask to root level
    
    Returns: The moved task in its new position."""
)
async def move_task(input: MoveTaskInput) -> str:
    """Move a task to a new position"""
    try:
        result = await tasks_client.move_task(
            task_id=input.task_id,
            tasklist_id=input.tasklist_id,
            parent=input.parent_task_id,
            previous=input.previous_task_id
        )
        return f"✅ Task moved successfully!\n\n{ResponseFormatter.format_task(result, ResponseFormat.MARKDOWN)}"
    except Exception as e:
        return f"Error moving task: {str(e)}. Please verify the task IDs and try again."

@mcp.tool(
    description="""Clear all completed tasks from a task list.
    
    Bulk remove completed tasks to declutter your task list while preserving
    active tasks. This is useful for maintaining a clean, focused task list.
    
    ⚠️ WARNING: This permanently removes ALL completed tasks from the list.
    
    Returns: Confirmation of cleared tasks."""
)
async def clear_completed_tasks(input: ClearCompletedTasksInput) -> str:
    """Clear all completed tasks from a list"""
    try:
        await tasks_client.clear_completed(input.tasklist_id)
        return f"✅ All completed tasks have been cleared from task list '{input.tasklist_id}'."
    except Exception as e:
        return f"Error clearing completed tasks: {str(e)}. Please verify the task list ID and try again."

# ==========================================
# WORKFLOW TOOLS
# ==========================================

@mcp.tool(
    description="""Quickly add a task using natural language.
    
    Smart task creation that parses natural language for:
    - Task title
    - Due dates (tomorrow, next week, specific dates)
    - Priority indicators (urgent, important)
    
    Examples:
    - "Buy milk tomorrow"
    - "Meeting with John next Friday"
    - "Urgent: Fix bug in login system"
    
    Returns: The created task with parsed information."""
)
async def quick_add_task(input: QuickAddTaskInput) -> str:
    """Quickly add a task with smart parsing"""
    try:
        # Simple parsing logic (can be enhanced with NLP)
        text = input.text
        due_date = None
        
        # Check for common date indicators
        today = datetime.now().date()
        if "tomorrow" in text.lower():
            due_date = (today + timedelta(days=1)).isoformat()
            text = text.lower().replace("tomorrow", "").strip()
        elif "today" in text.lower():
            due_date = today.isoformat()
            text = text.lower().replace("today", "").strip()
        elif "next week" in text.lower():
            due_date = (today + timedelta(weeks=1)).isoformat()
            text = text.lower().replace("next week", "").strip()
        
        # Create the task
        result = await tasks_client.create_task(
            title=text.strip(),
            tasklist_id=input.tasklist_id,
            due=due_date
        )
        
        return f"✅ Task added via quick add!\n\n{ResponseFormatter.format_task(result, ResponseFormat.DETAILED)}"
    except Exception as e:
        return f"Error in quick add: {str(e)}"

@mcp.tool(
    description="""Create multiple tasks at once efficiently.
    
    Bulk task creation for:
    - Project task lists
    - Recurring task patterns
    - Checklist items
    
    All tasks can share a common due date if specified.
    
    Returns: Summary of created tasks."""
)
async def bulk_create_tasks(input: BulkCreateTasksInput) -> str:
    """Create multiple tasks in bulk"""
    try:
        created_tasks = []
        failed_tasks = []
        
        for task_title in input.tasks:
            try:
                result = await tasks_client.create_task(
                    title=task_title,
                    tasklist_id=input.tasklist_id,
                    due=input.due_date
                )
                created_tasks.append(task_title)
            except Exception as e:
                failed_tasks.append(f"{task_title}: {str(e)}")
        
        output = f"# Bulk Task Creation Results\n\n"
        output += f"✅ **Successfully created:** {len(created_tasks)} tasks\n"
        
        if created_tasks:
            output += "\n**Created tasks:**\n"
            for task in created_tasks[:10]:  # Show first 10
                output += f"- {task}\n"
            if len(created_tasks) > 10:
                output += f"... and {len(created_tasks) - 10} more\n"
        
        if failed_tasks:
            output += f"\n❌ **Failed:** {len(failed_tasks)} tasks\n"
            for failure in failed_tasks[:5]:  # Show first 5 failures
                output += f"- {failure}\n"
        
        return output
    except Exception as e:
        return f"Error in bulk creation: {str(e)}"

@mcp.tool(
    description="""Search for tasks across all task lists.
    
    Find tasks by searching through:
    - Task titles
    - Task notes/descriptions
    - All task lists in your account
    
    Useful for finding specific tasks when you don't remember which list they're in.
    
    Returns: Matching tasks from all lists."""
)
async def search_tasks(input: SearchTasksInput) -> str:
    """Search tasks across all lists"""
    try:
        # Get all task lists
        lists_result = await tasks_client.list_tasklists(max_results=50)
        task_lists = lists_result.get('items', [])
        
        matching_tasks = []
        query_lower = input.query.lower()
        
        # Search through each task list
        for task_list in task_lists:
            try:
                tasks_result = await tasks_client.list_tasks(
                    tasklist_id=task_list['id'],
                    max_results=100,
                    show_completed=input.include_completed
                )
                
                tasks = tasks_result.get('items', [])
                for task in tasks:
                    title = task.get('title', '').lower()
                    notes = task.get('notes', '').lower()
                    
                    if query_lower in title or query_lower in notes:
                        task['_list_title'] = task_list['title']
                        matching_tasks.append(task)
                        
                        if len(matching_tasks) >= input.max_results:
                            break
                
                if len(matching_tasks) >= input.max_results:
                    break
                    
            except Exception as e:
                logger.warning(f"Error searching in list {task_list['id']}: {e}")
                continue
        
        if not matching_tasks:
            return f"No tasks found matching '{input.query}'."
        
        # Format results
        if input.response_format == ResponseFormat.JSON:
            return json.dumps(matching_tasks, indent=2)
        
        output = f"# Search Results for '{input.query}'\n\n"
        output += f"Found {len(matching_tasks)} matching task(s)\n\n"
        
        for task in matching_tasks:
            list_title = task.pop('_list_title', 'Unknown List')
            output += f"**List:** {list_title}\n"
            output += ResponseFormatter.format_task(task, input.response_format)
            output += "\n---\n\n"
        
        return output
    except Exception as e:
        return f"Error searching tasks: {str(e)}"

@mcp.tool(
    description="""Get a summary of tasks for a specific time range.
    
    Provides an overview of:
    - Tasks due today
    - Tasks due tomorrow
    - Tasks for the week
    - Overdue tasks
    - All tasks
    
    Perfect for daily planning and task review.
    
    Returns: Organized summary of tasks by time range."""
)
async def get_task_summary(input: GetTaskSummaryInput) -> str:
    """Get a summary of tasks by time range"""
    try:
        today = datetime.now().date()
        filters = {}
        
        # Set date filters based on time range
        if input.time_range == "today":
            filters['due_min'] = today.isoformat()
            filters['due_max'] = today.isoformat()
            title = "Today's Tasks"
        elif input.time_range == "tomorrow":
            tomorrow = today + timedelta(days=1)
            filters['due_min'] = tomorrow.isoformat()
            filters['due_max'] = tomorrow.isoformat()
            title = "Tomorrow's Tasks"
        elif input.time_range == "week":
            week_end = today + timedelta(days=7)
            filters['due_min'] = today.isoformat()
            filters['due_max'] = week_end.isoformat()
            title = "This Week's Tasks"
        elif input.time_range == "overdue":
            filters['due_max'] = (today - timedelta(days=1)).isoformat()
            title = "Overdue Tasks"
        else:  # all
            title = "All Tasks"
        
        # Get tasks from default list (can be extended to all lists)
        result = await tasks_client.list_tasks(
            tasklist_id="@default",
            max_results=50,
            show_completed=input.include_completed,
            **filters
        )
        
        tasks = result.get('items', [])
        
        if not tasks:
            return f"No tasks found for {title.lower()}."
        
        # Organize tasks by status
        pending_tasks = [t for t in tasks if t.get('status') != 'completed']
        completed_tasks = [t for t in tasks if t.get('status') == 'completed']
        
        # Format output
        output = f"# {title}\n\n"
        output += f"**Summary:** {len(pending_tasks)} pending"
        if input.include_completed:
            output += f", {len(completed_tasks)} completed"
        output += "\n\n"
        
        if pending_tasks:
            output += "## ⏳ Pending Tasks\n\n"
            for task in pending_tasks[:20]:  # Limit to prevent huge responses
                output += ResponseFormatter.format_task(task, input.response_format) + "\n"
        
        if input.include_completed and completed_tasks:
            output += "\n## ✅ Completed Tasks\n\n"
            for task in completed_tasks[:10]:
                output += ResponseFormatter.format_task(task, input.response_format) + "\n"
        
        if result.get('nextPageToken'):
            output += f"\n**Note:** More tasks available. This is a summary of the first {len(tasks)} tasks."
        
        return output
    except Exception as e:
        return f"Error getting task summary: {str(e)}"

# ==========================================
# MAIN ENTRY POINT
# ==========================================

if __name__ == "__main__":
    # Run the MCP server
    import sys
    
    # Check for credentials file
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"""
Google Tasks MCP Server Setup Required:

1. Go to https://console.cloud.google.com/
2. Create a new project or select an existing one
3. Enable the Google Tasks API
4. Create OAuth 2.0 credentials (Desktop application type)
5. Download the credentials JSON file
6. Save it to: {CREDENTIALS_PATH}

Once complete, run this server again.
        """, file=sys.stderr)
        sys.exit(1)
    
    # Start the server
    mcp.run()
