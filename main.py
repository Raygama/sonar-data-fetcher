import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
SONAR_TOKEN = os.getenv("SONAR_TOKEN")
SONAR_BASE = "https://sonarcloud.io/api"

HEADERS = {"Authorization": f"Bearer {SONAR_TOKEN}"}

def sonar_get(endpoint, params):
    r = requests.get(f"{SONAR_BASE}/{endpoint}", headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()

@app.route("/get-sonar-pr-issues", methods=["GET"])
def get_sonar_pr_issues():
    project = request.args.get("projectKey")
    pr = request.args.get("prNumber")
    if not project or not pr:
        return jsonify({"error": "projectKey and prNumber required"}), 400
    
    issues = sonar_get("issues/search", {
        "componentKeys": project,
        "pullRequest": pr,
        "ps": 50,
    }).get("issues", [])
    results = []

    for issue in issues:
        comp = issue["component"]
        line_no = issue.get("line")
        if comp and line_no:
            # fetch raw file
            raw = requests.get(
                f"{SONAR_BASE}/sources/raw",
                headers=HEADERS,
                params={"key": comp}
            )
            if raw.status_code == 200:
                lines = raw.text.splitlines()
                # safe index access
                if 1 <= line_no <= len(lines):
                    issue["sourceCode"] = lines[line_no - 1].strip()
                else:
                    issue["sourceCode"] = "[line out of range]"
            else:
                issue["sourceCode"] = "[source unavailable]"
        else:
            issue["sourceCode"] = "[no line/component]"
        results.append(issue)

    return jsonify({"project": project, "pr": pr, "issues": results})
