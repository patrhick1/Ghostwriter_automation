import subprocess
import sys

packages = ['pyairtable', 'openai', 'anthropic', 'python-dotenv', 'flask', 'APScheduler']

def get_package_version(package_name):
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'show', package_name], 
                                capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if line.startswith('Version:'):
                return line.split(': ')[1].strip()
    except Exception as e:
        print(f"Error getting version for {package_name}: {e}")
    return None

with open('requirements.txt', 'w') as f:
    for package in packages:
        version = get_package_version(package)
        if version:
            f.write(f"{package}=={version}\n")
            print(f"Added {package}=={version} to requirements.txt")
        else:
            print(f"Could not find version for {package}")

# Display the contents of requirements.txt
with open('requirements.txt', 'r') as f:
    print("\nContents of requirements.txt:")
    print(f.read())