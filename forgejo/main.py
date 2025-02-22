from pyforgejo import PyforgejoApi

with open('token') as file:
    API_KEY = file.read()
if not API_KEY:
    print("API_KEY not found")
    exit(1)

client = PyforgejoApi(base_url="https://codeberg.org/api/v1", api_key=API_KEY)

repo = client.repository.repo_get(owner="harabat", repo="pyforgejo")


print(f"Название: {repo.name}")
print(f"Описание: {repo.description}")