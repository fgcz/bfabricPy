import argparse


def app() -> None:
    """CLI interface for slurm submitter."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-j", type=int)
    args = parser.parse_args()
    _ = args
    print("TODO")


if __name__ == "__main__":
    app()
