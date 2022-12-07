# Dev setup
## Cluster problems
**summary**: After reboot, kind exhibits some weird problems and existing pods may not respond which can be seen in timeouts for the ingress controller or unexpected behavior when recycling pods
### possible solution
Doing the following might fix the issues 

**restart docker containers to refresh kind cluster**
``` 
docker stop topiaas-worker && docker stop topiaas-control-plane
docker start topiaas-worker && docker start topiaas-control-plane
```

## Database init and migrations
**summary**: The database tables need initializing at least once to avoid raised exceptions in the routes 

### possible solution
**manually initialize the database**

obtain a shell into the portal pod and execute the following to create the tables
```
python manage.py setup_dev
```
To run the migrations you should do it manually as well in a similar fashion through the `manage.py` script