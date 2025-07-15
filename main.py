import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

SONAR_TOKEN = os.environ.get("SONAR_TOKEN")
SONAR_API = "https://sonarcloud.io/api"

def sonar_call(path, params):
    headers = {"Authorization": f"Bearer {SONAR_TOKEN}"}
    resp = requests.get(f"{SONAR_API}/{path}", headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()

@app.route('/get-sonar-pr-issues')
def sonar_pr_issues():
    project = request.args['projectKey']
    pr = request.args['prNumber']
    issues = sonar_call("issues/search", {"componentKeys": project, "pullRequest": pr}).get("issues", [])
    out = []
    for issue in issues:
        lr = issue.get('textRange', {})
        line = lr.get('startLine')
        if line:
            start = max(1, line - 25)
            end = line + 25
            try:
                snippet = sonar_call("sources/lines", {
                    "component": issue['component'], 
                    "from": start, "to": end
                })
                # API returns list of {"line":#, "code":...}
                snippet_text = "\n".join(obj.get("code","") for obj in snippet)
            except Exception as e:
                snippet_text = f"[error fetching source: {e}]"
        else:
            snippet_text = "[no line info]"

        issue['sourceSnippet'] = snippet_text
        out.append(issue)
    return jsonify({"project": project, "pr": pr, "issues": out})

if __name__ == '__main__':
    app.run()
