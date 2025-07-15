import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

SONAR_TOKEN = os.getenv("SONAR_TOKEN")
SONAR_API_BASE = "https://sonarcloud.io/api"
sonar_headers = {"Authorization": f"Bearer {SONAR_TOKEN}"}

def call_sonar(endpoint, params=None):
    resp = requests.get(f"{SONAR_API_BASE}/{endpoint}", headers=sonar_headers, params=params)
    resp.raise_for_status()
    return resp.json()

@app.route("/get-sonar-pr-issues", methods=["GET"])
def get_sonar_pr_issues():
    project = request.args.get("projectKey")
    pr = request.args.get("prNumber")
    if not project or not pr:
        return jsonify({"error": "Missing projectKey or prNumber"}), 400
    try:
        # fetch issues specific to PR
        issues = call_sonar("issues/search", {"componentKeys": project, "pullRequest": pr})
        enriched = []
        for issue in issues.get("issues", []):
            comp = issue.get("component")
            if comp:
                try:
                    sd = call_sonar("sources/raw", {"key": comp, "pullRequest": pr})
                    issue["sourceCode"] = sd.get("source", "").splitlines()
                except:
                    issue["sourceCode"] = []
            enriched.append(issue)
        return jsonify({"project": project, "pr": pr, "issues": enriched})
    except requests.HTTPError as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return "Sonar PR fetcher up!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=81)
