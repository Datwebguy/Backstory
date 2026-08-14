from backstory.tools.smoke_hydradb import main


def test_hydradb_capability_matrix():
    assert main(["--skip-wait"]) == 0
