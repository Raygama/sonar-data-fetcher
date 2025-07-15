import os
import requests
from flask import Flask, jsonify, request

# Initialize the Flask web application
app = Flask(__name__)

# Get API tokens from the environment variables
SONAR_TOKEN = os.environ.get('SONAR_TOKEN')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN') # You will need to add this to Render secrets

SONAR_API_BASE_URL = "https://sonarcloud.io/api"
GITHUB_API_BASE_URL = "https://api.github.com"

def make_api_call(url, headers={}):
    """A helper function to make authenticated API calls."""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling API: {e}")
        return None

@app.route('/get-sonar-pr-issues')
def sonar_pr_issues():
    """
    This endpoint fetches SonarQube issues for a specific pull request
    and enriches them with their corresponding source code from GitHub.
    """
    project_key = request.args.get('projectKey')
    pr_number = request.args.get('prNumber')
    owner = request.args.get('owner')
    repo = request.args.get('repo')
    branch = request.args.get('branch') # We will get this from the GitHub Action

    if not all([project_key, pr_number, owner, repo, branch]):
        return jsonify({"error": "Missing required parameters"}), 400

    if not SONAR_TOKEN or not GITHUB_TOKEN:
        return jsonify({"error": "API tokens are not configured in the environment."}), 500

    # 1. Fetch the list of issues from SonarCloud
    sonar_headers = {"Authorization": f"Bearer {SONAR_TOKEN}"}
    issue_params = {"componentKeys": project_key, "pullRequest": pr_number}
    issue_data = make_api_call(f"{SONAR_API_BASE_URL}/issues/search?{requests.compat.urlencode(issue_params)}", headers=sonar_headers)
    
    if issue_data is None or "issues" not in issue_data:
        return jsonify({"error": "Failed to fetch issues from SonarCloud."}), 500

    out = []
    github_headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

    # 2. For each issue, fetch the full source code from GitHub
    for issue in issue_data["issues"]:
        # The component key is like 'ProjectKey:path/to/file.java'
        # We need to extract just the file path.
        file_path = issue.get('component', '').split(':', 1)[-1]
        
        if file_path:
            try:
                # Construct the GitHub API URL for the file content
                content_url = f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
                file_content_data = make_api_call(content_url, headers=github_headers)
                
                if file_content_data and 'content' in file_content_data:
                    # The content is base64 encoded, so we need to decode it
                    import base64
                    decoded_content = base64.b64decode(file_content_data['content']).decode('utf-8')
                    issue['sourceCode'] = decoded_content
                else:
                    issue['sourceCode'] = f"[Could not fetch content for {file_path}]"
            except Exception as e:
                issue['sourceCode'] = f"[Error fetching source from GitHub: {e}]"
        else:
            issue['sourceCode'] = "[No file path in issue]"
            
        out.append(issue)
        
    return jsonify({"project": project_key, "pr": pr_number, "issues": out})

@app.route('/')
def index():
    """A simple index route to confirm the app is running."""
    return "Sonar Data Fetcher is running!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
