# MarkmentIO

Markment as a service


## developing

1. Install dependencies:

```console
curd install -r development.txt
```

2. Run the server

```console
make run
```

3. In another window, run the workers

```console
make workers
```

4. Go to your browser on [`http://localhost:5000`](http://localhost:5000) and log in

5. Now that you logged in and the workers are running from step 3, test a build:

```console
make workers
```


## deploying

Have your ssh keys exported to the server then....

```bash
make deploy
```

It will deploy the master branch to production
