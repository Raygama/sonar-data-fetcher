import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

SONAR_TOKEN = os.getenv("SONAR_TOKEN")
SONAR_API_BASE_URL = "https://sonarcloud.io/api"

class SonarClient:
    def __init__(self, token):
        if not token:
            raise ValueError("SONAR_TOKEN is not set")
        self.token = token
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def call(self, endpoint, params=None):
        resp = requests.get(f"{SONAR_API_BASE_URL}/{endpoint}", headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_issues_for_pr(self, project_key, pr_number):
        return self.call("issues/search", {
            "componentKeys": project_key,
            "pullRequest": pr_number,
            "ps": 500
        })

    def get_source_for_component(self, component_key):
        return self.call("sources/show", {"key": component_key})

# Initialize once globally
try:
    sonar = SonarClient(SONAR_TOKEN)
except ValueError as e:
    print(f"Initialization error: {e}")
    sonar = None

@app.route('/get-sonar-pr-issues', methods=['GET'])
def get_sonar_pr_issues():
    if sonar is None:
        return jsonify({"error": "Server misconfigured: SONAR_TOKEN missing"}), 500

    project_key = request.args.get('projectKey')
    pr_number   = request.args.get('prNumber')
    if not project_key or not pr_number:
        return jsonify({"error": "Missing projectKey or prNumber"}), 400

    try:
        issues_data = sonar.get_issues_for_pr(project_key, pr_number)
    except requests.HTTPError as e:
        return jsonify({
            "error": "SonarCloud API request failed",
            "status": e.response.status_code,
            "details": e.response.text
        }), e.response.status_code

    issues = issues_data.get("issues", [])
    if not issues:
        return jsonify({"error": f"No issues found for PR {pr_number}"}), 404

    enriched = []
    for issue in issues:
        comp = issue.get("component")
        src = None
        try:
            src = sonar.get_source_for_component(comp)
        except requests.HTTPError:
            pass
        code = None
        if src and src.get("sources"):
            code = "\n".join(line["code"] for line in src["sources"][0].get("lines", []))
        enriched.append({
            **issue,
            "sourceCode": code or "Source unavailable"
        })

    return jsonify({
        "projectKey": project_key,
        "pullRequest": pr_number,
        "issues": enriched
    })

@app.route('/')
def index():
    return jsonify({"status": "running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
