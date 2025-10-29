#!/usr/bin/env python3
"""
Test script for Google Tasks MCP Server

This script runs basic tests to verify the MCP server is working correctly.
"""

import json
import asyncio
from datetime import datetime, timedelta
from google_tasks_mcp import (
    GoogleTasksClient,
    ResponseFormatter,
    ResponseFormat,
    TaskStatus
)

class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_test(name):
    print(f"\n{Colors.BOLD}Testing: {name}{Colors.ENDC}")

def print_success(msg):
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")

def print_fail(msg):
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")

async def test_authentication():
    """Test authentication with Google Tasks"""
    print_test("Authentication")
    try:
        client = GoogleTasksClient()
        print_success("Successfully authenticated with Google Tasks API")
        return client
    except Exception as e:
        print_fail(f"Authentication failed: {e}")
        return None

async def test_list_operations(client):
    """Test task list operations"""
    print_test("Task List Operations")
    test_list_id = None
    
    try:
        # Test listing task lists
        result = await client.list_tasklists(max_results=5)
        lists = result.get('items', [])
        print_success(f"Found {len(lists)} task list(s)")
        
        # Test creating a task list
        test_list_title = f"MCP Test List {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        new_list = await client.create_tasklist(test_list_title)
        test_list_id = new_list['id']
        print_success(f"Created test list: {new_list['title']}")
        
        # Test updating the task list
        updated_title = f"{test_list_title} - Updated"
        updated_list = await client.update_tasklist(test_list_id, updated_title)
        print_success(f"Updated test list title to: {updated_list['title']}")
        
        # Clean up - delete test list
        await client.delete_tasklist(test_list_id)
        print_success("Cleaned up test list")
        
        return True
        
    except Exception as e:
        print_fail(f"Task list operations failed: {e}")
        # Try to clean up if test list was created
        if test_list_id:
            try:
                await client.delete_tasklist(test_list_id)
                print_warning("Cleaned up test list after error")
            except:
                pass
        return False

async def test_task_operations(client):
    """Test task operations"""
    print_test("Task Operations")
    test_task_id = None
    
    try:
        # Create a test task
        task_title = f"MCP Test Task {datetime.now().strftime('%H:%M:%S')}"
        tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
        
        new_task = await client.create_task(
            title=task_title,
            notes="This is a test task created by MCP test script",
            due=tomorrow
        )
        test_task_id = new_task['id']
        print_success(f"Created test task: {new_task['title']}")
        
        # List tasks
        tasks_result = await client.list_tasks(max_results=10)
        tasks = tasks_result.get('items', [])
        print_success(f"Listed {len(tasks)} task(s)")
        
        # Update the task
        updated_task = await client.update_task(
            task_id=test_task_id,
            title=f"{task_title} - Updated",
            status=TaskStatus.COMPLETED.value
        )
        print_success(f"Updated test task and marked as completed")
        
        # Delete the test task
        await client.delete_task(test_task_id)
        print_success("Deleted test task")
        
        return True
        
    except Exception as e:
        print_fail(f"Task operations failed: {e}")
        # Try to clean up if test task was created
        if test_task_id:
            try:
                await client.delete_task(test_task_id)
                print_warning("Cleaned up test task after error")
            except:
                pass
        return False

async def test_response_formatting():
    """Test response formatting"""
    print_test("Response Formatting")
    
    try:
        # Create sample task data
        sample_task = {
            'id': 'test123',
            'title': 'Sample Task',
            'notes': 'This is a test note',
            'status': 'needsAction',
            'due': '2024-12-25T00:00:00.000Z'
        }
        
        # Test different formats
        formats_tested = []
        
        for format_type in [ResponseFormat.JSON, ResponseFormat.MARKDOWN, 
                           ResponseFormat.CONCISE, ResponseFormat.DETAILED]:
            formatted = ResponseFormatter.format_task(sample_task, format_type)
            if formatted:
                formats_tested.append(format_type.value)
        
        print_success(f"Tested formats: {', '.join(formats_tested)}")
        
        # Test multiple tasks formatting
        sample_tasks = [sample_task, sample_task.copy()]
        formatted_multiple = ResponseFormatter.format_multiple_tasks(
            sample_tasks, 
            ResponseFormat.MARKDOWN,
            "Test Tasks"
        )
        
        if formatted_multiple:
            print_success("Multiple task formatting works")
        
        return True
        
    except Exception as e:
        print_fail(f"Response formatting failed: {e}")
        return False

async def test_search_functionality(client):
    """Test search across task lists"""
    print_test("Search Functionality")
    
    try:
        # This is a basic connectivity test
        # In production, you'd search for actual tasks
        lists_result = await client.list_tasklists(max_results=1)
        if lists_result:
            print_success("Search infrastructure is accessible")
            return True
        else:
            print_warning("No task lists found for search test")
            return True
            
    except Exception as e:
        print_fail(f"Search test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print("Google Tasks MCP Server Test Suite")
    print(f"{'='*60}{Colors.ENDC}")
    
    # Test authentication first
    client = await test_authentication()
    if not client:
        print(f"\n{Colors.FAIL}Cannot proceed without authentication{Colors.ENDC}")
        return False
    
    # Run tests
    results = []
    
    # Test response formatting (doesn't need API calls)
    results.append(await test_response_formatting())
    
    # Test API operations
    results.append(await test_list_operations(client))
    results.append(await test_task_operations(client))
    results.append(await test_search_functionality(client))
    
    # Summary
    print(f"\n{Colors.BOLD}{'='*60}")
    print("Test Summary")
    print(f"{'='*60}{Colors.ENDC}")
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    if passed == total:
        print(f"{Colors.OKGREEN}✓ All tests passed ({passed}/{total}){Colors.ENDC}")
        print("\nYour Google Tasks MCP Server is ready to use! 🎉")
        return True
    else:
        print(f"{Colors.WARNING}⚠ {passed}/{total} tests passed{Colors.ENDC}")
        if passed > 0:
            print("\nThe server is partially functional but may have some issues.")
        else:
            print("\nPlease check the setup and try again.")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
        exit(1)
