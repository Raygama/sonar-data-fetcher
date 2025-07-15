import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
SONAR_TOKEN = os.environ.get("SONAR_TOKEN")
BASE = "https://sonarcloud.io/api"

def sonar_get(endpoint, params):
    headers = {"Authorization": f"Bearer {SONAR_TOKEN}"}
    r = requests.get(f"{BASE}/{endpoint}", headers=headers, params=params)
    r.raise_for_status()
    return r.json()

@app.route("/get-sonar-pr-issues", methods=["GET"])
def get_issues():
    project = request.args.get("projectKey")
    pr = request.args.get("prNumber")
    if not project or not pr:
        return jsonify({"error": "projectKey and prNumber required"}), 400
    try:
        # fetch PR issues
        iss = sonar_get("issues/search", {"componentKeys": project, "pullRequest": pr})
        enriched = []
        for i in iss.get("issues", []):
            line = i.get("line")
            if line:
                start = max(line - 25, 1)
                end = line + 25
                src = sonar_get("sources/lines", {
                    "componentKey": i["component"], "from": start, "to": end
                })
                snippet = "\n".join(
                    f"{l['line']}| {l['code']}" for l in src.get("lines", [])
                ) if src.get("lines") else "[no source]"
            else:
                snippet = "[no line number]"
            i["sourceCode"] = snippet
            enriched.append(i)
        return jsonify({"project": project, "pr": pr, "issues": enriched})
    except requests.HTTPError as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000)
