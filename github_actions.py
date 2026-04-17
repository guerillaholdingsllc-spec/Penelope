from github import Github
import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")

def get_repo():
    g = Github(GITHUB_TOKEN)
    return g.get_repo(f"{GITHUB_OWNER}/{GITHUB_REPO}")

def create_test_file():
    repo = get_repo()
    
    content = "Penelope GitHub test successful."
    
    repo.create_file(
        path="penelope_test.txt",
        message="Penelope test commit",
        content=content,
        branch="main"
    )
    
    print("✅ File created on GitHub")

def create_issue():
    repo = get_repo()
    
    issue = repo.create_issue(
        title="Penelope Test Issue",
        body="Penelope GitHub integration is working."
    )
    
    print(f"✅ Issue created: {issue.html_url}")
