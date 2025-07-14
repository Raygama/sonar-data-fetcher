import os
import requests
from flask import Flask, jsonify, request

# Initialize the Flask web application
app = Flask(__name__)

# Get the SonarCloud token from Replit's secure secrets
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

@app.route('/get-sonar-data', methods=['GET'])
def get_sonar_data():
    """
    This endpoint fetches SonarQube issues for a specific pull request
    and enriches them with their corresponding source code.
    """
    # Get parameters from the request URL (sent by Flowise)
    project_key = request.args.get('projectKey')
    pr_number = request.args.get('prNumber')

    if not project_key or not pr_number:
        return jsonify({"error": "Missing required parameters: projectKey and prNumber"}), 400

    if not SONAR_TOKEN:
        return jsonify({"error": "SONAR_TOKEN is not configured in Replit secrets."}), 500

    # 1. Fetch the list of issues for the pull request
    issue_params = {
        "componentKeys": project_key,
        "pullRequest": pr_number
    }
    issue_data = make_api_call("issues/search", params=issue_params)

    if issue_data is None or "issues" not in issue_data:
        return jsonify({"error": "Failed to fetch issues from SonarCloud."}), 500

    processed_issues = []

    # 2. For each issue, fetch its source code
    for issue in issue_data["issues"]:
        source_params = {
            "key": issue["component"]
        }
        source_data = make_api_call("sources/show", params=source_params)

        if source_data and "sources" in source_data:
            # Extract the code lines and join them into a single string
            source_code_lines = [line['code'] for line in source_data['sources'][0]['lines']]
            source_code = "\n".join(source_code_lines)
            
            # Add the source code to the issue object
            issue['sourceCode'] = source_code
        else:
            issue['sourceCode'] = "Could not retrieve source code."

        processed_issues.append(issue)

    # 3. Return the final, enriched list of issues
    return jsonify(processed_issues)

@app.route('/')
def index():
    """A simple index route to confirm the app is running."""
    return "Sonar Data Fetcher is running!"

if __name__ == '__main__':
    # Runs the app on host 0.0.0.0, which is required for Replit
    app.run(host='0.0.0.0', port=81)
