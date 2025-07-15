import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

SONAR_TOKEN = os.environ.get("SONAR_TOKEN")
SONAR_API = "https://sonarcloud.io/api"

class SonarClient:
    def __init__(self, token):
        self.headers = {"Authorization": f"Bearer {token}"}

    def get(self, endpoint, params=None):
        r = requests.get(f"{SONAR_API}/{endpoint}", headers=self.headers, params=params)
        r.raise_for_status()
        return r.json()

    def issues_for_pr(self, project_key, pr_number):
        return self.get("issues/search", {
            "componentKeys": project_key,
            "pullRequest": pr_number,
            "ps": 100
        })

    def raw_source(self, component, hash_val, line):
        # fetch raw source including specific line context
        return self.get("sources/raw", {
            "key": component,
            "hash": hash_val,
            "from": max(1, line-3),
            "to": line+3
        })

@app.route("/get-sonar-pr-issues")
def get_sonar_pr_issues():
    project = request.args.get("projectKey")
    pr = request.args.get("prNumber")
    if not project or not pr:
        return jsonify({"error": "Missing projectKey or prNumber"}), 400
    if not SONAR_TOKEN:
        return jsonify({"error": "Missing SONAR_TOKEN"}), 500

    client = SonarClient(SONAR_TOKEN)
    try:
        data = client.issues_for_pr(project, pr)
    except requests.HTTPError as e:
        return jsonify({"error": f"Issue fetch failed: {e}"}), 500

    issues = []
    for it in data.get("issues", []):
        comp = it["component"]
        ln = it.get("line", it["textRange"]["startLine"])
        snippet = ""
        try:
            src = client.raw_source(comp, it["hash"], ln)
            snippet = src.get("source", "")
        except Exception:
            snippet = "[source unavailable]"
        it["sourceCode"] = snippet.splitlines()
        issues.append(it)

    return jsonify({"project": project, "pr": pr, "issues": issues})


@app.route("/")
def index():
    return "Sonar PR issue fetcher running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 81)))
