from dataclasses import asdict, dataclass
from time import sleep
from typing import Generator

from constants import TIMEDELTA
from interface_wrapper import IRepositoryAPI, Repository
from utils import logger


@dataclass(kw_only=True, frozen=True)
class WorkflowRunData:
    repository_name: str = ''
    display_title: str = ''
    event: str = ''
    head_branch: str = ''
    head_sha: str = ''
    name: str = ''
    path: str = ''
    started_at: str = ''
    total_duration: float = 0.0
    conclusion: str = ''
    status: str = ''
    url: str = ''


def log_repository_workflow_runs(
    client: IRepositoryAPI, repository: Repository, csv_name: str
):
    workflow_runs = client.get_workflow_runs(repository)

    for run in workflow_runs:
        total_duration = (run.updated_at - run.created_at).total_seconds()

        workflow_run_data = WorkflowRunData(
            repository_name=repository.name,
            display_title=run.display_title,
            event=run.event,
            head_branch=run.head_branch,
            head_sha=run.head_sha,
            name=run.name,
            path=run.path,
            started_at=run.run_started_at,
            total_duration=total_duration,
            conclusion=run.conclusion,
            status=run.status,
            url=run.url,
        )

        info_dict = asdict(workflow_run_data)

        logger.log_to_csv(csv_name, list(info_dict.keys()), info_dict)
        logger.log_to_stdout(info_dict)

        sleep(TIMEDELTA)


def log_workflow_runs(
    binded_repos: Generator[tuple[IRepositoryAPI, Repository, str], None, None],
    csv_name: str,
    fork_flag: bool,
):
    info = asdict(WorkflowRunData())
    logger.log_to_csv(csv_name, list(info.keys()))

    for client, repo, token in binded_repos:
        try:
            logger.log_title(repo.name)
            log_repository_workflow_runs(client, repo, csv_name)

            if fork_flag:
                for forked_repo in client.get_forks(repo):
                    logger.log_title(f"FORKED: {forked_repo.name}")
                    log_repository_workflow_runs(client, forked_repo, csv_name)
                    sleep(TIMEDELTA)

        except Exception as e:
            print(e)
            exit(1)
