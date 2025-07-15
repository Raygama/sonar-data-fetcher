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
    issues = make_api_call("issues/search", {"componentKeys": project, "pullRequest": pr}).get("issues", [])
    out = []
    for issue in issues:
        lr = issue.get('textRange', {})
        line = lr.get('startLine')
        if line:
            start = max(1, line - 25)
            end = line + 25
            try:
                # The API expects the parameter 'key', not 'component'.
                snippet_data = make_api_call("sources/lines", {
                    "key": issue['component'],
                    "from": start, "to": end
                })
                # The response is a direct list of line objects.
                # We iterate over the list itself, not a 'lines' property.
                if snippet_data:
                    snippet_text = "\n".join(obj.get("code","") for obj in snippet_data)
                else:
                    snippet_text = "[Could not parse snippet data]"
            except Exception as e:
                snippet_text = f"[error fetching source: {e}]"
        else:
            snippet_text = "[no line info]"

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
