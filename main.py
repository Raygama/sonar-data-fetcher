import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

SONAR_TOKEN = os.environ.get("SONAR_TOKEN")
SONAR_API_BASE = "https://sonarcloud.io/api"

class SonarClient:
    def __init__(self, token):
        self.token = token
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def get(self, endpoint, params=None):
        r = requests.get(f"{SONAR_API_BASE}/{endpoint}", headers=self.headers, params=params)
        r.raise_for_status()
        return r.json()

    def get_pr_issues(self, project_key, pr_number):
        return self.get("issues/search", {"componentKeys": project_key, "pullRequest": pr_number})

    def get_lines(self, component, start, end):
        return self.get("sources/lines", {"componentKey": component, "from": start, "to": end})

sonar = SonarClient(SONAR_TOKEN)

@app.route("/get-sonar-pr-issues", methods=["GET"])
def get_pr_issues():
    project = request.args.get("projectKey")
    pr = request.args.get("prNumber")
    if not project or not pr:
        return jsonify({"error": "projectKey and prNumber required"}), 400

    try:
        issues = sonar.get_pr_issues(project, pr)["issues"]
    except requests.HTTPError as e:
        return jsonify({"error": str(e)}), 500

    enriched = []
    for issue in issues:
        comp = issue["component"]
        line = issue.get("line", issue.get("textRange", {}).get("startLine", 1))
        start = max(1, line - 25)
        end = line + 25

        try:
            src = sonar.get_lines(comp, start, end)
            snippet = src.get("lines", [])
            code_buf = "\n".join(f"{L['line']}| {L['text']}" for L in snippet)
        except Exception as e:
            code_buf = f"[error fetching source: {e}]"

        issue["sourceCode"] = code_buf
        enriched.append(issue)

    return jsonify({"project": project, "pr": pr, "issues": enriched})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 81)))
