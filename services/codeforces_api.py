import requests

CF_API_BASE = "https://codeforces.com/api"


def fetch_all_problems():
    
    url = f"{CF_API_BASE}/problemset.problems"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "OK":
        raise Exception("Codeforces API error: " + str(data.get("comment")))

    problems = data["result"]["problems"]
    cleaned = []
    for p in problems:
        if "rating" not in p:
            continue
        cleaned.append({
            "contestId": p.get("contestId"),
            "index": p.get("index"),
            "name": p.get("name"),
            "rating": p.get("rating"),
            "tags": p.get("tags", []),
        })
    return cleaned


def fetch_user_solved_problems(handle):
    url = f"{CF_API_BASE}/user.status"
    params = {"handle": handle, "from": 1, "count": 10000}
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "OK":
        raise Exception("Invalid Codeforces handle or API error: " + str(data.get("comment")))

    submissions = data["result"]
    solved = {}
    for sub in submissions:
        if sub.get("verdict") == "OK":
            problem = sub.get("problem", {})
            contest_id = problem.get("contestId")
            index = problem.get("index")
            if contest_id is None or index is None:
                continue
            key = f"{contest_id}{index}"
            if key not in solved:
                solved[key] = {
                    "problem_key": key,
                    "contestId": contest_id,
                    "index": index,
                    "name": problem.get("name"),
                }

    return list(solved.values())


def fetch_user_info(handle):
    url = f"{CF_API_BASE}/user.info"
    params = {"handles": handle}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "OK":
        raise Exception("Invalid Codeforces handle: " + handle)

    result = data["result"][0]
    return {
        "handle": result.get("handle"),
        "rating": result.get("rating", 0),
    }
