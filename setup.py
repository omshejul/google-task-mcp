#!/usr/bin/env python3
"""
Setup script for Google Tasks MCP Server

This script helps you set up the Google Tasks MCP server by:
1. Installing required dependencies
2. Checking for credentials
3. Testing the authentication
4. Generating configuration for Claude Desktop
"""

import os
import sys
import json
import subprocess
import platform
from pathlib import Path

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    print_header("Checking Python Version")
    
    if sys.version_info < (3, 8):
        print_error(f"Python 3.8 or higher is required. You have {sys.version}")
        return False
    
    print_success(f"Python {sys.version.split()[0]} detected")
    return True

def install_dependencies():
    """Install required Python packages"""
    print_header("Installing Dependencies")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print_success("All dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print_error("Failed to install dependencies")
        print_info("Try running: pip install -r requirements.txt")
        return False

def check_credentials():
    """Check if Google OAuth credentials are configured"""
    print_header("Checking Google OAuth Credentials")
    
    creds_dir = Path.home() / ".google_tasks_mcp"
    creds_file = creds_dir / "credentials.json"
    
    if not creds_dir.exists():
        print_info(f"Creating configuration directory: {creds_dir}")
        creds_dir.mkdir(parents=True, exist_ok=True)
    
    if not creds_file.exists():
        print_warning("Google OAuth credentials not found!")
        print("\nTo set up credentials:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing")
        print("3. Enable the Google Tasks API")
        print("4. Go to 'APIs & Services' > 'Credentials'")
        print("5. Click 'Create Credentials' > 'OAuth client ID'")
        print("6. Choose 'Desktop app' as application type")
        print("7. Download the credentials JSON file")
        print(f"8. Save it as: {creds_file}")
        print("\nPress Enter once you've completed these steps...")
        input()
        
        if not creds_file.exists():
            print_error("Credentials file still not found")
            return False
    
    print_success(f"Credentials found at: {creds_file}")
    return True

def test_authentication():
    """Test if authentication works"""
    print_header("Testing Authentication")
    
    print_info("Attempting to authenticate with Google Tasks...")
    print_warning("A browser window may open for authorization")
    
    try:
        # Try importing and initializing the client
        from google_tasks_mcp import GoogleTasksAuth, GoogleTasksClient
        
        creds = GoogleTasksAuth.get_credentials()
        if creds and creds.valid:
            print_success("Authentication successful!")
            return True
        else:
            print_warning("Authentication may be required on first run")
            print_info("Run 'python google_tasks_mcp.py' to complete authentication")
            return True
    except Exception as e:
        print_error(f"Authentication test failed: {e}")
        print_info("You may need to authenticate when running the server")
        return True  # Don't block setup for this

def get_claude_config_path():
    """Get the Claude Desktop configuration file path"""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        return Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
    elif system == "Linux":
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    else:
        return None

def setup_claude_desktop():
    """Generate configuration for Claude Desktop"""
    print_header("Claude Desktop Configuration")
    
    config_path = get_claude_config_path()
    
    if not config_path:
        print_warning("Could not determine Claude Desktop config path for your system")
        print_info("Please manually add the configuration to Claude Desktop")
        return
    
    print_info(f"Claude config path: {config_path}")
    
    # Get the current script directory
    server_path = Path.cwd() / "google_tasks_mcp.py"
    
    config = {
        "google-tasks": {
            "command": sys.executable,
            "args": [str(server_path)],
            "env": {}
        }
    }
    
    print("\nAdd this to your Claude Desktop configuration:")
    print(Colors.OKCYAN + json.dumps(config, indent=2) + Colors.ENDC)
    
    if config_path.exists():
        print_warning(f"\nConfiguration file exists at: {config_path}")
        print_info("Please manually add the above configuration to the 'mcpServers' section")
    else:
        print_info("\nWould you like to create a new configuration file? (y/n): ", end="")
        if input().lower() == 'y':
            config_path.parent.mkdir(parents=True, exist_ok=True)
            full_config = {"mcpServers": config}
            with open(config_path, 'w') as f:
                json.dump(full_config, f, indent=2)
            print_success(f"Configuration saved to: {config_path}")

def main():
    """Main setup function"""
    print_header("Google Tasks MCP Server Setup")
    print("This script will help you set up the Google Tasks MCP Server\n")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print_warning("Continuing despite dependency installation issues...")
    
    # Check credentials
    if not check_credentials():
        print_error("\nSetup incomplete: Missing credentials")
        print_info("Please follow the instructions above and run setup again")
        sys.exit(1)
    
    # Test authentication
    test_authentication()
    
    # Setup Claude Desktop
    setup_claude_desktop()
    
    # Final instructions
    print_header("Setup Complete!")
    
    print("Next steps:")
    print("1. Run 'python google_tasks_mcp.py' to start the server")
    print("2. If using Claude Desktop, restart the app after adding configuration")
    print("3. In Claude, you can now use commands like:")
    print("   - 'List my tasks for today'")
    print("   - 'Create a new task: Buy groceries'")
    print("   - 'Show me all my task lists'")
    print("\nFor more information, see README.md")
    
    print_success("\nSetup completed successfully! 🎉")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        sys.exit(1)
