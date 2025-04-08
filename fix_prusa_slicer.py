#!/usr/bin/env python3
"""
Script to fix PrusaSlicer permissions and configuration
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Configure basic logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('PrusaSlicer-Fix')

def find_prusa_slicer():
    """Find PrusaSlicer executable in common locations"""
    # Load environment variables
    load_dotenv()
    env_path = os.environ.get('PRUSA_SLICER_PATH')
    
    if env_path and os.path.exists(env_path):
        logger.info(f"Found PrusaSlicer in environment: {env_path}")
        return env_path
    
    # Check if it's in PATH
    path_slicer = shutil.which("prusa-slicer") or shutil.which("prusaslicer")
    if path_slicer:
        logger.info(f"Found PrusaSlicer in PATH: {path_slicer}")
        return path_slicer
    
    # Check common macOS locations
    mac_paths = [
        "/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer",
        "/Applications/Original Prusa Drivers/PrusaSlicer.app/Contents/MacOS/PrusaSlicer",
        "/usr/local/bin/prusa-slicer"
    ]
    
    for path in mac_paths:
        if os.path.exists(path):
            logger.info(f"Found PrusaSlicer at: {path}")
            return path
    
    logger.error("Could not find PrusaSlicer executable")
    return None

def fix_permissions(path):
    """Fix permissions for PrusaSlicer executable"""
    if not path:
        return False
    
    logger.info(f"Fixing permissions for: {path}")
    try:
        # Make the file executable
        os.chmod(path, 0o755)
        logger.info("Successfully updated permissions")
        
        # Verify the permissions
        if os.access(path, os.X_OK):
            logger.info("File is now executable")
            return True
        else:
            logger.error("File is still not executable after permission change")
            return False
    except Exception as e:
        logger.error(f"Error fixing permissions: {str(e)}")
        return False

def update_env_file(path):
    """Update the .env file with the correct PrusaSlicer path"""
    if not path:
        return False
    
    env_file = Path('.env')
    if not env_file.exists():
        logger.error(".env file not found")
        return False
    
    logger.info(f"Updating .env file with PrusaSlicer path: {path}")
    
    # Read the current content
    content = env_file.read_text()
    
    # Check if PRUSA_SLICER_PATH is already in the file
    if 'PRUSA_SLICER_PATH=' in content:
        # Replace the existing path
        lines = content.splitlines()
        updated_lines = []
        for line in lines:
            if line.startswith('PRUSA_SLICER_PATH='):
                updated_lines.append(f'PRUSA_SLICER_PATH={path}')
            else:
                updated_lines.append(line)
        
        # Write the updated content
        env_file.write_text('\n'.join(updated_lines))
    else:
        # Append the path to the file
        with env_file.open('a') as f:
            f.write(f'\n# DFM Analyzer settings\nPRUSA_SLICER_PATH={path}\n')
    
    logger.info("Successfully updated .env file")
    return True

def test_prusa_slicer(path):
    """Test if PrusaSlicer is working correctly"""
    if not path:
        return False
    
    logger.info(f"Testing PrusaSlicer at: {path}")
    try:
        # Try to run PrusaSlicer with --help
        result = subprocess.run([path, "--help"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               timeout=5)
        
        if result.returncode == 0:
            logger.info("PrusaSlicer is working correctly")
            return True
        else:
            logger.error(f"PrusaSlicer execution failed with return code {result.returncode}")
            logger.error(f"Error output: {result.stderr.decode('utf-8')}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("PrusaSlicer execution timed out")
        return False
    except Exception as e:
        logger.error(f"Error executing PrusaSlicer: {str(e)}")
        return False

def create_symlink(path):
    """Create a symlink to PrusaSlicer in a directory that's in PATH"""
    if not path:
        return False
    
    # Create a symlink in /usr/local/bin
    symlink_path = "/usr/local/bin/prusa-slicer"
    
    logger.info(f"Creating symlink from {path} to {symlink_path}")
    try:
        # Remove existing symlink if it exists
        if os.path.exists(symlink_path):
            os.remove(symlink_path)
        
        # Create the symlink
        os.symlink(path, symlink_path)
        logger.info("Successfully created symlink")
        
        # Verify the symlink
        if os.path.exists(symlink_path) and os.access(symlink_path, os.X_OK):
            logger.info("Symlink is valid and executable")
            return True
        else:
            logger.error("Symlink is not valid or not executable")
            return False
    except Exception as e:
        logger.error(f"Error creating symlink: {str(e)}")
        return False

def main():
    """Main function to fix PrusaSlicer configuration"""
    logger.info("=== PrusaSlicer Fix ===")
    
    # Find PrusaSlicer
    prusa_path = find_prusa_slicer()
    
    if not prusa_path:
        logger.error("Could not find PrusaSlicer. Please install it first.")
        return
    
    # Fix permissions
    fix_permissions(prusa_path)
    
    # Update .env file
    update_env_file(prusa_path)
    
    # Test PrusaSlicer
    if test_prusa_slicer(prusa_path):
        logger.info("PrusaSlicer is configured correctly")
    else:
        logger.error("PrusaSlicer is not working correctly")
        
        # Try creating a symlink as a last resort
        logger.info("Attempting to create a symlink...")
        if create_symlink(prusa_path):
            logger.info("Created symlink to PrusaSlicer")
            
            # Update .env file with the symlink path
            update_env_file("/usr/local/bin/prusa-slicer")
            
            # Test the symlink
            if test_prusa_slicer("/usr/local/bin/prusa-slicer"):
                logger.info("PrusaSlicer symlink is working correctly")
            else:
                logger.error("PrusaSlicer symlink is not working correctly")
    
    logger.info("=== PrusaSlicer Fix Complete ===")

if __name__ == "__main__":
    main()
