from backstory.demo.load_demo import isolated_demo_key
from backstory.eval.lme_v2_adapter import states_to_turns, to_lme_like


def test_demo_keys_always_namespaced():
    assert isolated_demo_key("demo-user-ui") == "demo:demo-user-ui"
    assert isolated_demo_key("demo:alice") == "demo:alice"
    assert isolated_demo_key("someone") == "demo:someone"


def test_lme_v2_flattens_trajectory_text_and_drops_screenshots():
    traj = {
        "id": "t1",
        "goal": "reset the password",
        "states": [
            {
                "url": "https://example.com/login",
                "action": "click reset",
                "thought": "I should open the reset form.",
                "accessibility_tree": "button Reset password",
                "screenshot": "screenshots/t1/0.png",
            }
        ],
    }
    turns = states_to_turns(traj)
    blob = " ".join(t["content"] for t in turns)
    assert "reset the password" in blob
    assert "I should open the reset form." in blob
    assert "click reset" in blob
    assert "screenshots/t1/0.png" not in blob


def test_lme_v2_record_is_labelled_unofficial():
    rec = to_lme_like(
        {
            "id": "q1",
            "question_type": "static_state",
            "question": "What was the last URL?",
            "answer": "https://example.com",
        }
    )
    assert rec["question_id"] == "q1"
    assert "not official" in rec["note"]
