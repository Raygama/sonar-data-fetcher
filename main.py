import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

SONAR_TOKEN = os.getenv("SONAR_TOKEN")
BASE_URL = "https://sonarcloud.io/api"

class SonarClient:
    def __init__(self, token):
        self.headers = {"Authorization": f"Bearer {token}"}

    def get(self, endpoint, params):
        url = f"{BASE_URL}/{endpoint}"
        resp = requests.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_pr_issues(self, project_key, pr_number):
        return self.get("issues/search", {
            "componentKeys": project_key,
            "pullRequest": pr_number,
            "ps": 100
        })

    def get_source_lines(self, component, issue_line, context=25):
        start = max(issue_line - context, 1)
        end = issue_line + context
        params = {"key": component, "from": start, "to": end}
        resp = requests.get(f"{BASE_URL}/sources/lines", headers=self.headers, params=params)
        resp.raise_for_status()
        # expecting list of { 'line': int, 'code': str }
        return resp.json()

sonar = SonarClient(SONAR_TOKEN)

@app.route('/get-sonar-pr-issues', methods=['GET'])
def get_sonar_pr_issues():
    project = request.args.get("projectKey")
    pr = request.args.get("prNumber")
    if not project or not pr:
        return jsonify({"error": "Missing projectKey or prNumber"}), 400

    issues_resp = sonar.get_pr_issues(project, pr)
    issues = issues_resp.get("issues", [])

    enriched = []
    for issue in issues:
        comp = issue.get("component")
        if comp and "line" in issue:
            try:
                source_lines = sonar.get_source_lines(comp, issue["line"], context=25)
                issue["sourceCode"] = "\n".join(f"{ln['line']:5d}: {ln['code']}"
                                               for ln in source_lines)
            except Exception:
                issue["sourceCode"] = "[error fetching source]"
        enriched.append(issue)

    return jsonify({"project": project, "pr": pr, "issues": enriched})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)), debug=True)
