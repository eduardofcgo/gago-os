from score.execute.local import run_command


def count_errors(work_dir):
    command = f"/src/score/exercises/scripting1/error_log.sh {work_dir} | wc -l"

    return int(run_command(command))


max_number_errors = 12


def score(user):
    work_dir = f"/home/{user}/scripting1"
    error_count = count_errors(work_dir)

    if error_count > max_number_errors:
        raise ValueError(f"Found {work_dir} errors, than expected {max_number_errors}")

    return int(100 * (1 - error_count / max_number_errors))
