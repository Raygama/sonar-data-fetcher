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


@app.route('/get-sonar-pr-issues', methods=['GET'])
def get_sonar_pr_issues():
    project_key = request.args.get('projectKey')
    pr_number = request.args.get('prNumber')
    if not project_key or not pr_number:
        return jsonify({"error": "Missing projectKey or prNumber"}), 400
    try:
        issues_data = sonar.get_issues_for_pr(project_key, pr_number)
    except requests.HTTPError as e:
        return jsonify({"error": str(e), "details": e.response.text}), e.response.status_code

    if not issues_data.get("issues"):
        return jsonify({"error": f"No issues found for PR {pr_number}"}), 404

    enriched = []
    for issue in issues_data["issues"]:
        comp = issue.get("component")
        src = sonar.get_source_for_component(comp)
        issue["sourceCode"] = (
            "\n".join([l["code"] for l in src["sources"][0]["lines"]])
            if src and src.get("sources") else None
        )
        enriched.append(issue)

    return jsonify({
        "projectKey": project_key,
        "pullRequest": pr_number,
        "issues": enriched
    })


if __name__ == '__main__':
    sonar = SonarClient(SONAR_TOKEN)
    app.run(host='0.0.0.0', port=81)
