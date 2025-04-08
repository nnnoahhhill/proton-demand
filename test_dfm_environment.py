#!/usr/bin/env python3
"""
Test script to verify the DFM environment setup
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
logger = logging.getLogger('DFM-Environment-Test')

def check_executable(path):
    """Check if a file exists and is executable"""
    if not path:
        return False
    
    file_path = Path(path)
    if not file_path.exists():
        logger.error(f"Path does not exist: {path}")
        return False
    
    if not os.access(path, os.X_OK):
        logger.error(f"File is not executable: {path}")
        return False
    
    return True

def test_prusa_slicer():
    """Test PrusaSlicer installation and configuration"""
    logger.info("Testing PrusaSlicer configuration...")
    
    # Load environment variables
    load_dotenv()
    env_path = os.environ.get('PRUSA_SLICER_PATH')
    
    if env_path:
        logger.info(f"Found PrusaSlicer path in environment: {env_path}")
        if check_executable(env_path):
            logger.info("✅ PrusaSlicer path from environment is valid and executable")
            
            # Try to run PrusaSlicer with --help to verify it works
            try:
                result = subprocess.run([env_path, "--help"], 
                                       stdout=subprocess.PIPE, 
                                       stderr=subprocess.PIPE,
                                       timeout=5)
                if result.returncode == 0:
                    logger.info("✅ Successfully executed PrusaSlicer with --help")
                    return env_path
                else:
                    logger.error(f"❌ PrusaSlicer execution failed with return code {result.returncode}")
                    logger.error(f"Error output: {result.stderr.decode('utf-8')}")
            except subprocess.TimeoutExpired:
                logger.error("❌ PrusaSlicer execution timed out")
            except Exception as e:
                logger.error(f"❌ Error executing PrusaSlicer: {str(e)}")
        else:
            logger.error(f"❌ PrusaSlicer path from environment is not valid or not executable: {env_path}")
    else:
        logger.warning("No PrusaSlicer path found in environment variables")
    
    # Try to find PrusaSlicer in common locations
    logger.info("Searching for PrusaSlicer in common locations...")
    
    # Check if it's in PATH
    path_slicer = shutil.which("prusa-slicer") or shutil.which("prusaslicer")
    if path_slicer:
        logger.info(f"Found PrusaSlicer in PATH: {path_slicer}")
        if check_executable(path_slicer):
            logger.info("✅ PrusaSlicer from PATH is valid and executable")
            return path_slicer
    
    # Check common macOS locations
    mac_paths = [
        "/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer",
        "/Applications/Original Prusa Drivers/PrusaSlicer.app/Contents/MacOS/PrusaSlicer",
        "/usr/local/bin/prusa-slicer"
    ]
    
    for path in mac_paths:
        if check_executable(path):
            logger.info(f"✅ Found valid PrusaSlicer at: {path}")
            return path
    
    logger.error("❌ Could not find a valid PrusaSlicer installation")
    return None

def fix_prusa_slicer_permissions():
    """Fix permissions for PrusaSlicer if needed"""
    env_path = os.environ.get('PRUSA_SLICER_PATH')
    
    if env_path and os.path.exists(env_path):
        logger.info(f"Fixing permissions for PrusaSlicer at: {env_path}")
        try:
            # Make the file executable
            os.chmod(env_path, 0o755)
            logger.info("✅ Successfully updated permissions")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update permissions: {str(e)}")
    
    return False

def update_env_file(prusa_path):
    """Update the .env file with the correct PrusaSlicer path"""
    if not prusa_path:
        return False
    
    env_file = Path('.env')
    if not env_file.exists():
        logger.error("❌ .env file not found")
        return False
    
    logger.info(f"Updating .env file with PrusaSlicer path: {prusa_path}")
    
    # Read the current content
    content = env_file.read_text()
    
    # Check if PRUSA_SLICER_PATH is already in the file
    if 'PRUSA_SLICER_PATH=' in content:
        # Replace the existing path
        lines = content.splitlines()
        updated_lines = []
        for line in lines:
            if line.startswith('PRUSA_SLICER_PATH='):
                updated_lines.append(f'PRUSA_SLICER_PATH={prusa_path}')
            else:
                updated_lines.append(line)
        
        # Write the updated content
        env_file.write_text('\n'.join(updated_lines))
    else:
        # Append the path to the file
        with env_file.open('a') as f:
            f.write(f'\n# DFM Analyzer settings\nPRUSA_SLICER_PATH={prusa_path}\n')
    
    logger.info("✅ Successfully updated .env file")
    return True

def test_dfm_analyzer():
    """Test the DFM analyzer module"""
    logger.info("Testing DFM analyzer module...")
    
    try:
        # Try to import the module directly
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Use importlib to handle module names with dashes
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "3d_print_dfm_analyzer", 
            os.path.join("dfm", "3d-print-dfm-analyzer.py")
        )
        
        if spec is None:
            logger.error("❌ Could not find 3d-print-dfm-analyzer.py")
            return False
        
        dfm_analyzer_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dfm_analyzer_module)
        
        # Check if the module has the required classes and functions
        if hasattr(dfm_analyzer_module, 'DFMAnalyzer'):
            logger.info("✅ Successfully imported DFMAnalyzer class")
            
            # Create an instance of the analyzer
            analyzer = dfm_analyzer_module.DFMAnalyzer()
            
            # Check if the analyzer has the required methods
            if hasattr(analyzer, 'find_slicer_path'):
                logger.info("✅ DFMAnalyzer has find_slicer_path method")
                
                # Try to find the slicer path
                slicer_path = analyzer.find_slicer_path()
                if slicer_path:
                    logger.info(f"✅ DFMAnalyzer found slicer at: {slicer_path}")
                    return True
                else:
                    logger.error("❌ DFMAnalyzer could not find slicer path")
            else:
                logger.error("❌ DFMAnalyzer does not have find_slicer_path method")
        else:
            logger.error("❌ Module does not have DFMAnalyzer class")
    
    except Exception as e:
        logger.error(f"❌ Error testing DFM analyzer: {str(e)}")
    
    return False

def main():
    """Main function to test the environment"""
    logger.info("=== DFM Environment Test ===")
    
    # Test PrusaSlicer
    prusa_path = test_prusa_slicer()
    
    if not prusa_path:
        logger.info("Attempting to fix PrusaSlicer permissions...")
        if fix_prusa_slicer_permissions():
            # Try again after fixing permissions
            prusa_path = test_prusa_slicer()
    
    if prusa_path:
        # Update the .env file with the correct path
        update_env_file(prusa_path)
    
    # Test the DFM analyzer
    test_dfm_analyzer()
    
    logger.info("=== Environment Test Complete ===")

if __name__ == "__main__":
    main()
