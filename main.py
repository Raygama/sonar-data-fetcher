import os, requests
from flask import Flask, request, jsonify

app = Flask(__name__)
SONAR_TOKEN = os.environ["SONAR_TOKEN"]
BASE = "https://sonarcloud.io/api"

@app.route("/get-sonar-pr-issues")
def sonar_pr_issues():
    pk = request.args.get("projectKey")
    pr = request.args.get("prNumber")
    if not pk or not pr:
        return jsonify(error="Missing projectKey or prNumber"), 400

    h = {"Authorization": f"Bearer {SONAR_TOKEN}"}
    issues = requests.get(f"{BASE}/issues/search",
                          headers=h,
                          params={"componentKeys": pk, "pullRequest": pr}).json().get("issues", [])

    enriched = []
    for i in issues:
        comp = i["component"]
        line = i.get("line")
        snippet = "[no source]"

        if comp and line:
            lo = max(1, line-25)
            hi = line+25
            r = requests.get(f"{BASE}/sources/lines",
                             headers=h,
                             params={"key": comp, "from": lo, "to": hi})
            if r.ok:
                arr = r.json()
                snippet = "\n".join(x["code"] for x in arr)
            else:
                snippet = f"[error: {r.status_code} {r.reason}]"

        i["sourceSnippet"] = snippet
        enriched.append(i)

    return jsonify({"project": pk, "pr": pr, "issues": enriched})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
