"""Wait for W18c, then execute the already declared private padding study."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, freeze, write_json

OUT = ROOT / 'output/climate_followups_20261127'
PADDING = ROOT / 'output/padding_sensitivity_20261126'
CAMPAIGN = ROOT / 'output/ppe_20261127/W18c/campaign_status.json'
DEPENDENCIES = [
    'scripts/run_climate_followups.py', 'scripts/padding_sensitivity.py',
    'scripts/review_padding_sensitivity.py', 'scripts/local_benchmark_protocol.py',
    'calibration/padding_sensitivity_20261126/plan.json',
    'output/padding_sensitivity_20261126/protocol.json',
    'output/padding_sensitivity_20261126/preparation.json',
    'output/padding_sensitivity_20261126/preparation_review.json',
    'output/padding_sensitivity_20261126/reviewer_readiness.json',
    'calibration/ppe_20261123/plan_W18c.json',
    'calibration/ppe_20261123/W18c_runtime_amendment.json',
]
STOPPED = {'campaign_needs_recovery', 'interrupted_padding_needs_review',
           'review_without_results_needs_review', 'dependency_changed_needs_review',
           'padding_command_failed', 'review_command_failed'}


def next_action(stage, *, campaign_live, benchmark_live, padding_live,
                study_complete, review_complete, interrupted_attempt):
    if padding_live:
        return 'wait_for_padding'
    if interrupted_attempt:
        return 'interrupted_padding_needs_review'
    if review_complete and not study_complete:
        return 'review_without_results_needs_review'
    if study_complete:
        return 'finished_for_agent_review' if review_complete else 'review_padding'
    terminal = stage.startswith('closed_') or stage == 'all_gates_passed_ready_for_review'
    if terminal and not campaign_live and not benchmark_live:
        return 'run_padding'
    if not campaign_live and not benchmark_live:
        return 'campaign_needs_recovery'
    return 'wait_for_campaign'


def live_scripts(proc=Path('/proc')):
    names = set()
    for directory in proc.iterdir():
        if not directory.name.isdigit():
            continue
        try:
            status = (directory / 'stat').read_text().rsplit(') ', 1)[1].split()[0]
            args = (directory / 'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError):
            continue
        if status == 'Z':
            continue
        for arg in args:
            if arg:
                names.add(Path(os.fsdecode(arg)).name)
    return names


def observe():
    campaign = json.loads(CAMPAIGN.read_text())
    live = live_scripts()
    interrupted = any(not (p.parent / 'result.json').exists() for p in PADDING.glob('*/pad_*/attempt.json'))
    action = next_action(campaign['stage'], campaign_live='run_w18c_campaign.py' in live,
        benchmark_live='benchmark_local.py' in live, padding_live='padding_sensitivity.py' in live,
        study_complete=(PADDING / 'results.json').exists(), review_complete=(PADDING / 'review.json').exists(),
        interrupted_attempt=interrupted)
    return action, campaign


def record(stage, campaign, **more):
    value = dict(stage=stage, pid=os.getpid(), updated_utc=datetime.now(timezone.utc).isoformat(),
        campaign_stage=campaign.get('stage'), campaign_completed=campaign.get('completed'),
        campaign_candidate=campaign.get('candidate'), **more)
    write_json(OUT / 'status.json', value)
    return value


def check_dependencies(protocol):
    for name, digest in protocol['sources_sha256'].items():
        if not (ROOT / name).is_file() or file_hash(ROOT / name) != digest:
            raise ValueError('Queued dependency changed: ' + name)


def execute_once(action, campaign, run=subprocess.run):
    """A nonzero child exit stops the queue; never retry scientific failures."""
    if action == 'run_padding':
        script, arguments, log_name = 'scripts/padding_sensitivity.py', ['--run'], 'padding.log'
        failed = 'padding_command_failed'
    elif action == 'review_padding':
        script, arguments, log_name = 'scripts/review_padding_sensitivity.py', [], 'review.log'
        failed = 'review_command_failed'
    else:
        raise ValueError(action)
    record(action, campaign)
    with (OUT / log_name).open('ab') as log:
        result = run(['nice', '-n', '10', str(ROOT / '.venv/bin/python'), '-u', '-I', str(ROOT / script), *arguments],
                     cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        record(failed, campaign, returncode=result.returncode, log=log_name)
        return False
    expected = PADDING / ('results.json' if action == 'run_padding' else 'review.json')
    if not expected.exists():
        record(failed, campaign, returncode=0, log=log_name, error='Child exited without its required output')
        return False
    return True


def verify_finished_review():
    review = json.loads((PADDING / 'review.json').read_text())
    assert review['result_sha256'] == file_hash(PADDING / 'results.json')
    assert review['reviewer_sha256'] == file_hash(ROOT / 'scripts/review_padding_sensitivity.py')
    assert review['aggregate_score'] is None and review['climate_adopted'] is False
    for name, digest in review['files_sha256'].items():
        assert file_hash(PADDING / name) == digest, name
    assert review['figure_sha256'] == file_hash(PADDING / 'padding_changes.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true', help='Report next action; never start children or create queue state')
    parser.add_argument('--poll-seconds', type=float, default=30.)
    args = parser.parse_args()
    if not 1 <= args.poll_seconds <= 60:
        raise SystemExit('Poll interval must be between 1 and 60 seconds')
    if args.check_only:
        action, campaign = observe()
        print(json.dumps(dict(next_action=action, campaign_stage=campaign['stage'],
                              completed=campaign.get('completed'), no_children_started=True)))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / '.gitignore').write_text('.lock\nstatus.json\npadding.log\nreview.log\n')
    lock = (OUT / '.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    protocol = dict(status='operational_queue_no_new_scientific_plan',
        sources_sha256={name:file_hash(ROOT / name) for name in DEPENDENCIES},
        maximum_padding_integrations=9, physical_source_changes=False, auto_adoption=False, auto_git_publication=False)
    freeze(OUT / 'protocol.json', protocol)
    marker = OUT / 'status.json'
    if marker.exists() and json.loads(marker.read_text())['stage'] in STOPPED:
        raise SystemExit('Previous queue failure needs recorded agent review; preserve status.json before resuming')
    previous = None
    while True:
        action, campaign = observe()
        try:
            check_dependencies(protocol)
            assert campaign['plan_sha256'] == protocol['sources_sha256']['calibration/ppe_20261123/plan_W18c.json']
            assert campaign['runtime_amendment_sha256'] == protocol['sources_sha256']['calibration/ppe_20261123/W18c_runtime_amendment.json']
        except (AssertionError, ValueError) as error:
            record('dependency_changed_needs_review', campaign, error=repr(error))
            raise
        row = record(action, campaign)
        summary = (action, campaign.get('completed'), campaign.get('candidate'))
        if summary != previous:
            print(json.dumps(row), flush=True)
            previous = summary
        if action in STOPPED:
            raise SystemExit('Queue paused for agent review: ' + action)
        if action == 'finished_for_agent_review':
            verify_finished_review()
            record(action, campaign, figure_inspection_pending=True, adoption_review_pending=True)
            return
        if action in {'run_padding', 'review_padding'}:
            if not execute_once(action, campaign):
                raise SystemExit('Child failed; queue will not retry automatically')
            continue
        time.sleep(args.poll_seconds)


if __name__ == '__main__':
    main()
