import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

SONAR_TOKEN = os.environ.get("SONAR_TOKEN")
SONAR_API_BASE_URL = "https://sonarcloud.io/api"

class SonarClient:
    def __init__(self, token):
        self.token = token
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def call(self, endpoint, params=None):
        try:
            response = requests.get(f"{SONAR_API_BASE_URL}/{endpoint}", headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"[SonarClient] API Error on {endpoint}: {e}")
            return None

    def get_issues_for_pr(self, project_key, pr_number):
        return self.call("issues/search", {
            "componentKeys": project_key,
            "pullRequest": pr_number
        })
    

    def get_source_for_component(self, component_key):
        return self.call("sources/show", {
            "key": component_key
        })

    def get_latest_pr_number(self, project_key):
        pr_data = self.call("pull_requests/list", {
            "project": project_key,
            "ps": 1,  # page size = 1
            "sort": "UPDATE_DATE",
            "status": "OPEN"
        })
        if pr_data and "pullRequests" in pr_data and pr_data["pullRequests"]:
            return pr_data["pullRequests"][0]["branch"]  # PRs are tied to branches
        return None


sonar = SonarClient(SONAR_TOKEN)

def get_latest_pr_branch_from_issues(project_key):
    """
    Extracts the most recent PR branch name by inspecting recent issues.
    """
    issues_data = sonar.call("issues/search", {
        "componentKeys": project_key,
        "sort": "CREATION_DATE",
        "ps": 50  # get last 50 issues, increase if needed
    })

    if issues_data and "issues" in issues_data:
        for issue in issues_data["issues"]:
            if "pullRequest" in issue:
                return issue["pullRequest"]  # this is the branch name SonarCloud uses
    return None


@app.route('/get-latest-sonar-data', methods=['GET'])
def get_latest_sonar_data():
    project_key = request.args.get('projectKey')

    if not project_key:
        return jsonify({"error": "Missing required parameter: projectKey"}), 400

    if not SONAR_TOKEN:
        return jsonify({"error": "SONAR_TOKEN not configured."}), 500

    pr_number = sonar.get_latest_pr_number(project_key)
    if not pr_number:
        return jsonify({"error": "No pull requests found for this project."}), 404

    return fetch_issues_with_code(project_key, pr_number)


@app.route('/get-sonar-data', methods=['GET'])
def get_sonar_data():
    project_key = request.args.get('projectKey')
    pr_number = request.args.get('prNumber')  # Optional

    if not project_key:
        return jsonify({"error": "Missing required parameter: projectKey"}), 400

    if not SONAR_TOKEN:
        return jsonify({"error": "SONAR_TOKEN is not configured."}), 500

    # Auto fallback: try to detect the latest PR
    if not pr_number:
        pr_number = get_latest_pr_branch_from_issues(project_key)
        if not pr_number:
            return jsonify({"error": "No pull request analysis found in recent issues."}), 404

    return fetch_issues_with_code(project_key, pr_number)




def fetch_issues_with_code(project_key, pr_number):
    issues_response = sonar.get_issues_for_pr(project_key, pr_number)

    if not issues_response or "issues" not in issues_response:
        return jsonify({"error": "Failed to fetch issues from SonarCloud."}), 500

    enriched_issues = []

    for issue in issues_response["issues"]:
        component = issue.get("component")
        source_data = sonar.get_source_for_component(component)

        if source_data and "sources" in source_data:
            try:
                lines = source_data['sources'][0]['lines']
                code_snippet = "\n".join(line['code'] for line in lines)
                issue['sourceCode'] = code_snippet
            except Exception as e:
                print(f"Error extracting source lines: {e}")
                issue['sourceCode'] = "Failed to extract source code."
        else:
            issue['sourceCode'] = "Source not available."

        enriched_issues.append(issue)

    return jsonify({
        "projectKey": project_key,
        "pullRequest": pr_number,
        "issues": enriched_issues
    })


@app.route('/')
def index():
    return "Sonar Data Fetcher is running!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
