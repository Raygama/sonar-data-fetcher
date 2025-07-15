import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
SONAR_TOKEN = os.environ.get("SONAR_TOKEN")
BASE = "https://sonarcloud.io/api"

class SonarClient:
    def __init__(self, token):
        self.auth = (token, "")

    def get_issues(self, project_key, pr):
        return requests.get(f"{BASE}/issues/search",
            auth=self.auth,
            params={"componentKeys": project_key, "pullRequest": pr}
        ).json()

    def get_raw_source(self, component, line, before=3, after=3):
        params = {"key": component, "from": max(1, line-before), "to": line+after}
        return requests.get(f"{BASE}/sources/raw", auth=self.auth, params=params).text

@app.route("/get-sonar-pr-issues", methods=["GET"])
def sonar_pr_issues():
    project = request.args.get("projectKey")
    pr = request.args.get("prNumber")
    if not project or not pr:
        return jsonify({"error": "projectKey and prNumber required"}), 400

    client = SonarClient(SONAR_TOKEN)
    issues_data = client.get_issues(project, pr)
    out = []
    for issue in issues_data.get("issues", []):
        comp = issue["component"]
        line = issue.get("line")
        snippet = "[no source]" if not line else client.get_raw_source(comp, line)
        out.append({**issue, "codeSnippet": snippet.splitlines()})
    return jsonify({"project": project, "pr": pr, "issues": out})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
