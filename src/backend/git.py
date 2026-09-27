# Generate a news feed section by fetching commit messages from the repository and displaying them in a list format.

from asyncio import subprocess
import subprocess

def get_recent_commits(n=5):
    """
    Fetch the most recent n commit messages from the Git repository.
    """
    try:
        result = subprocess.run(
            ["git", "log", f"-n{n}", "--pretty=format:%s"],
            capture_output=True,
            text=True,
            check=True
        )
        commits = result.stdout.split("\n")
        return commits
    except subprocess.CalledProcessError as e:
        print(f"Error fetching commits: {e}")
        return []
    
print("Fetching recent commits...")
recent_commits = get_recent_commits(5)
for commit in recent_commits:
    print(f"- {commit}")