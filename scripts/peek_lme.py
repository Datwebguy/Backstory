import json
import sys

data = json.load(open(r"data/lme/longmemeval_oracle.json", encoding="utf-8"))
wanted = sys.argv[1:] or ["e47becba", "6a1eabeb", "8a2466db", "gpt4_70e84552_abs"]
index = {item["question_id"]: item for item in data}
for qid in wanted:
    item = index[qid]
    print("=" * 60)
    print(item["question_type"], item["question_id"])
    print("Q:", item["question"])
    print("A:", str(item["answer"])[:250])
    print("qdate", item["question_date"])
    for sid, dt, sess in zip(
        item["haystack_session_ids"], item["haystack_dates"], item["haystack_sessions"]
    ):
        print("-- sess", sid, dt, "turns", len(sess))
        for turn in sess:
            flag = " *" if turn.get("has_answer") else ""
            text = turn["content"][:220].replace("\n", " ")
            print(f"  {turn['role']}{flag}: {text}")
