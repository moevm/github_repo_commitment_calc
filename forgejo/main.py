from dotenv import dotenv_values
from pyforgejo import PyforgejoApi


def require_env_arg(config, name):
    if not name in config:
        print("Cannot find " + name + " in .env file. Aborting...")
        exit(1)


config = dotenv_values(".env")
require_env_arg(config, "API_TOKEN")
require_env_arg(config, "BASE_URL")
require_env_arg(config, "REPO_OWNER")
require_env_arg(config, "REPO_NAME")

client = PyforgejoApi(base_url=config["BASE_URL"], api_key=config["API_TOKEN"])

repo = client.repository.repo_get(owner=config["REPO_OWNER"], repo=config["REPO_NAME"])


print(f"Название: {repo.name}")
print(f"Описание: {repo.description}")
