from dotenv import dotenv_values
from pyforgejo import PyforgejoApi

config = dotenv_values(".env")

if not "API_TOKEN" in config:
    print("Cannot find API_TOKEN in .env file. Check if it exists and has correct token. Aborting...")
    exit(1)
client = PyforgejoApi(base_url="https://codeberg.org/api/v1", api_key=config["API_TOKEN"])

repo = client.repository.repo_get(owner="harabat", repo="pyforgejo")


print(f"Название: {repo.name}")
print(f"Описание: {repo.description}")
