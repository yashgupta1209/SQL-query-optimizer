# feedback.py
#
# Command-line interface for the feedback loop (objective 7).
#
#   python feedback.py show     - summary of recorded feedback
#   python feedback.py collect  - execute the whole workload and
#                                 record the results as feedback
#   python feedback.py retrain  - merge feedback into the dataset
#                                 and retrain all four models
#
# The demo also records feedback automatically after every candidate
# execution, so running demo.py contributes to this loop too.

import sys

from optimizer import feedback


def show():
    stats = feedback.feedback_summary()

    print("=" * 70)
    print("              FEEDBACK STATUS")
    print("=" * 70)
    print()

    if stats["rows"] == 0:
        print("No feedback recorded yet.")
        print()
        print("Run the demo (python demo.py) or")
        print("python feedback.py collect")
        print("to start recording feedback.")
        return

    print(
        f"Feedback rows          : {stats['rows']}"
    )
    print(
        f"Unique queries         : {stats['queries']}"
    )
    print(
        f"Candidates observed    : {stats['candidates']}"
    )
    print(
        f"Mean actual runtime    : "
        f"{stats['mean_actual_runtime_ms']:.3f} ms"
    )
    print(
        f"Mean prediction error  : "
        f"{stats['mean_prediction_error_ms']:.3f} ms"
    )
    print()
    print(
        "Feedback is stored in the PostgreSQL 'feedback' table."
    )


def collect():
    print("=" * 70)
    print("          FEEDBACK COLLECTION")
    print("=" * 70)
    print()
    print(
        "Executing every candidate of every workload query "
        "and recording the observed runtime..."
    )
    print()

    written = feedback.collect_feedback(repetitions=1)

    print()
    print(f"Recorded {written} feedback observations.")
    print()

    show()


def retrain():
    feedback.retrain()


def main():
    command = (
        sys.argv[1] if len(sys.argv) > 1 else "show"
    )

    commands = {
        "show": show,
        "collect": collect,
        "retrain": retrain,
    }

    if command not in commands:
        print(
            "Usage: python feedback.py [show|collect|retrain]"
        )
        return

    commands[command]()


if __name__ == "__main__":
    main()
