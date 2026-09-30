### Global requirements:

- NodeJS 18 or higher

### Deploy Frontend in Ubuntu 20.04

##### 1. Clone project:

```bash
git clone https://git.tinhvan.com/vector-flow/ist-portal.git frontend-refactor && cd frontend-refactor
```

##### 2. Install packages

```bash
npm install
```

##### 3. Clone .env.development to .env and change the value of variables in .env file

```bash
cp .env.development .env
```

> Note: don't forget to change the value of variables in .env file

##### 4. Build project

```bash
npm run build
```

##### 5. Install pm2 to run the project in background

```bash
npm install pm2 -g
```

> Note: if you don't have npm, please install it first and this command run only once time

##### 6. Run project

```bash
pm2 start "serve -l <port> -s build" --name "frontend-refactor"
```

> Note: change <port> to the port you want to run the project

##### 7. Check status of project

```bash
pm2 logs
```
