import os
import requests
from flask import Flask, jsonify, request

# Initialize the Flask web application
app = Flask(__name__)

# Get the SonarCloud token from the environment variables
SONAR_TOKEN = os.environ.get('SONAR_TOKEN')
SONAR_API_BASE_URL = "https://sonarcloud.io/api"

def make_api_call(endpoint, params={}):
    """A helper function to make authenticated API calls to SonarCloud."""
    headers = {
        "Authorization": f"Bearer {SONAR_TOKEN}"
    }
    try:
        response = requests.get(f"{SONAR_API_BASE_URL}/{endpoint}", headers=headers, params=params)
        response.raise_for_status()  # Raises an exception for bad status codes (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling SonarCloud API: {e}")
        return None

@app.route('/get-sonar-pr-issues')
def sonar_pr_issues():
    """
    This endpoint fetches SonarQube issues for a specific pull request
    and enriches them with their corresponding source code snippet.
    """
    project = request.args.get('projectKey')
    pr = request.args.get('prNumber')
    
    if not project or not pr:
        return jsonify({"error": "Missing required parameters: projectKey and prNumber"}), 400

    if not SONAR_TOKEN:
        return jsonify({"error": "SONAR_TOKEN is not configured in the environment."}), 500
        
    issues_data = make_api_call("issues/search", {"componentKeys": project, "pullRequest": pr})
    
    if issues_data is None or "issues" not in issues_data:
        return jsonify({"error": "Failed to fetch issues from SonarCloud."}), 500

    out = []
    for issue in issues_data.get("issues", []):
        lr = issue.get('textRange', {})
        line = lr.get('startLine')
        
        if line:
            start = max(1, line - 25)
            end = line + 25
            try:
                # The API for fetching lines requires the 'key' parameter
                snippet_data = make_api_call("sources/lines", {
                    "key": issue['component'], 
                    "from": start, 
                    "to": end
                })
                
                # The response from this endpoint is a JSON object with a 'lines' key
                if snippet_data and 'lines' in snippet_data:
                    snippet_text = "\n".join(line_obj.get("code", "") for line_obj in snippet_data['lines'])
                else:
                    snippet_text = "[Could not parse snippet data from API response]"
            except Exception as e:
                snippet_text = f"[Error fetching source snippet: {e}]"
        else:
            snippet_text = "[No line info available for this issue]"

        issue['sourceSnippet'] = snippet_text
        out.append(issue)
        
    return jsonify({"project": project, "pr": pr, "issues": out})

@app.route('/')
def index():
    """A simple index route to confirm the app is running."""
    return "Sonar Data Fetcher is running!"

# This part is updated for production deployment.
# It uses the PORT environment variable provided by Render.
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
