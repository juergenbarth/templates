This command will stop and remove all docker containers on the host:

```
docker stop $(docker ps -aq) && docker rm $(docker ps -aq)
```
