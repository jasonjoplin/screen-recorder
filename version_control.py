import requests
import json
import os
import sys
import subprocess
from packaging import version

CURRENT_VERSION = "1.0.0"
GITHUB_REPO = "jasonjoplin/screen-recorder"  # Updated with your actual GitHub repository
VERSION_CHECK_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

class VersionControl:
    def __init__(self):
        self.current_version = CURRENT_VERSION
        self.latest_version = None
        self.update_available = False
        
    def check_for_updates(self):
        """Check if a new version is available."""
        try:
            response = requests.get(VERSION_CHECK_URL)
            if response.status_code == 200:
                latest_release = response.json()
                self.latest_version = latest_release['tag_name'].lstrip('v')
                self.update_available = version.parse(self.latest_version) > version.parse(self.current_version)
                return self.update_available
        except Exception as e:
            print(f"Failed to check for updates: {str(e)}")
            return False

    def get_update_info(self):
        """Get information about the latest update."""
        if not self.latest_version:
            self.check_for_updates()
        
        if self.update_available:
            return {
                'current_version': self.current_version,
                'latest_version': self.latest_version,
                'update_available': True
            }
        return {
            'current_version': self.current_version,
            'latest_version': self.current_version,
            'update_available': False
        }

    def download_update(self):
        """Download and install the latest update."""
        if not self.update_available:
            return False, "No updates available"

        try:
            # Download the latest release
            response = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/zipball/{self.latest_version}")
            if response.status_code == 200:
                # Save the update
                update_file = "update.zip"
                with open(update_file, 'wb') as f:
                    f.write(response.content)

                # Extract and install the update
                self._install_update(update_file)
                return True, "Update successful"
            return False, "Failed to download update"
        except Exception as e:
            return False, f"Update failed: {str(e)}"

    def _install_update(self, update_file):
        """Install the downloaded update."""
        # Implementation depends on your deployment method
        # This is a basic example
        try:
            # Create backup of current version
            os.system("git add .")
            os.system('git commit -m "Backup before update"')

            # Extract update
            import zipfile
            with zipfile.ZipFile(update_file, 'r') as zip_ref:
                zip_ref.extractall("temp_update")

            # Copy new files
            os.system("xcopy /E /Y temp_update\\* .")

            # Clean up
            os.remove(update_file)
            os.system("rmdir /S /Q temp_update")

            # Update version
            self.current_version = self.latest_version
            self.update_available = False

            # Restart application
            python = sys.executable
            os.execl(python, python, *sys.argv)

        except Exception as e:
            raise Exception(f"Failed to install update: {str(e)}")

def get_version():
    """Get the current version of the application."""
    return CURRENT_VERSION
