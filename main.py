import os, requests
from flask import Flask, jsonify, request

app = Flask(__name__)
SONAR_TOKEN = os.getenv("SONAR_TOKEN")
BASE = "https://sonarcloud.io/api"

def sonar_get(path, params=None):
    headers = {"Authorization": f"Bearer {SONAR_TOKEN}"}
    resp = requests.get(f"{BASE}/{path}", headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()

@app.route('/get-sonar-pr-issues', methods=['GET'])
def get_sonar_pr_issues():
    project = request.args.get('projectKey')
    pr = request.args.get('prNumber')
    if not project or not pr:
        return {"error": "projectKey and prNumber required"}, 400

    issues = sonar_get("issues/search", {
        "componentKeys": project,
        "pullRequest": pr,
        "ps": 50
    }).get('issues', [])

    output = []
    for issue in issues:
        line = issue.get("line")
        comp = issue["component"]

        start = max(line - 25, 1)
        end = line + 25

        try:
            src = sonar_get("sources/lines", {
                "componentKey": comp,
                "from": start,
                "to": end
            })
            snippet = "\n".join(item['line'] for item in src.get('sources', []))
        except Exception as e:
            snippet = f"[error fetching source: {str(e)}]"

        issue_out = {
            **issue,
            "sourceSnippet": snippet
        }
        output.append(issue_out)

    return jsonify({"project": project, "pr": pr, "issues": output})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
