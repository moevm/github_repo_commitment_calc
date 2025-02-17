## Docker build
```
docker build -t upload_commit_stats .
```

## Docker run
```
REPO_PATH=""
GOOGLE_SECRET=""
TABLE_ID=""

docker run \
  -v $REPO_PATH:/repos \
  -v $GOOGLE_SECRET:/secret.json \
  upload_commit_stats \
  python3 upload_commit_stats.py \
  --data-dir /repos \
  --table-id $TABLE_ID \
  --oauth-file /secret.json
```
