import random

def generate_contest_problems(all_problems, solved_keys, rating_min, rating_max,
                                topics, num_questions):
    
    topics_lower = set(t.strip().lower() for t in topics) if topics else None

    eligible = []
    for p in all_problems:
        key = f"{p['contestId']}{p['index']}"
        if key in solved_keys:
            continue
        if p["rating"] < rating_min or p["rating"] > rating_max:
            continue
        if topics_lower:
            problem_tags = set(t.lower() for t in p.get("tags", []))
            if not problem_tags.intersection(topics_lower):
                continue
        eligible.append(p)

    if len(eligible) < num_questions:
        raise ValueError(
            f"Only {len(eligible)} eligible problems found, but {num_questions} "
            f"were requested. Try widening the rating range or topics."
        )

    random.shuffle(eligible)
    chosen = eligible[:num_questions]
    chosen.sort(key=lambda p: p["rating"])
    return chosen
