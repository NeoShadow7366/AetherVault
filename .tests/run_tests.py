import sys
import os
import subprocess
import argparse

if __name__ == '__main__':
    # Ensure current directory is accessible
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    parser = argparse.ArgumentParser(description="Run QA Guardian Tests")
    parser.add_argument("--e2e", action="store_true", help="Run full Playwright E2E tests (requires playwright installed)")
    args, unknown = parser.parse_known_args()
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pytest_args = [sys.executable, "-m", "pytest", os.path.join(base_dir, ".tests")]
    
    if args.e2e:
        print("Running Full QA Suite including E2E Playwright tests...")
    else:
        print("Running Fast QA Suite (skipping E2E)...")
        pytest_args.extend(["-m", "not e2e"])
        
    pytest_args.extend(unknown)
    
    result = subprocess.run(pytest_args, cwd=base_dir)
    sys.exit(result.returncode)
