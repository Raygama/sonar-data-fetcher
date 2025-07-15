import os, requests
from flask import Flask, jsonify, request

app = Flask(__name__)
SONAR_TOKEN = os.getenv("SONAR_TOKEN")
BASE = "https://sonarcloud.io/api"
HEADERS = {"Authorization": f"Bearer {SONAR_TOKEN}"}

def sonarc_get(endpoint, params):
    r = requests.get(f"{BASE}/{endpoint}", headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()

@app.route("/get-sonar-pr-issues", methods=["GET"])
def get_issues():
    pr = request.args.get("prNumber")
    proj = request.args.get("projectKey")
    if not pr or not proj:
        return jsonify(error="Missing params"),400

    issues = sonarc_get("issues/search", {"componentKeys": proj, "pullRequest": pr}).get("issues", [])
    out = []
    for iss in issues:
        line = iss.get("line")
        comp = iss.get("component")
        if line and comp:
            start = max(1, line - 25)
            end = line + 25
            snippet = sonarc_get("sources/show", {"key": comp, "from": start, "to": end, "branch": f"refs/pull/{pr}/head"})
            lines = snippet.get("sources", [{}])[0].get("lines", [])
            iss["sourceCode"] = "\n".join(f"{l['line']:4d}: {l['code']}" for l in lines)
        else:
            iss["sourceCode"] = ""
        out.append(iss)
    return jsonify(project=proj, pr=pr, issues=out)

if __name__=="__main__":
    app.run()
