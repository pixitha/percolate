from percolate.models.timed_process import TimedProcess


def test_timed_process_clamps_elapsed_time_before_start() -> None:
    process = TimedProcess(started_at=100.0, duration=60.0)

    assert process.elapsed(40.0) == 0.0
    assert process.progress(40.0) == 0.0
    assert not process.is_ready(40.0)


def test_timed_process_becomes_ready_at_exact_duration() -> None:
    process = TimedProcess(started_at=100.0, duration=60.0)

    assert process.elapsed(130.0) == 30.0
    assert process.progress(160.0) == 1.0
    assert process.is_ready(160.0)


def test_zero_duration_process_is_immediately_complete() -> None:
    process = TimedProcess(started_at=100.0, duration=0.0)

    assert process.progress(100.0) == 1.0
    assert process.is_ready(100.0)


def test_timed_process_round_trips_through_dict() -> None:
    process = TimedProcess(started_at=123.5, duration=45.0)

    restored = TimedProcess.from_dict(process.to_dict())

    assert restored == process
