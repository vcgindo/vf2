# Codebase Documentation for Vector Flow UI

## Project structure

```bash
Vector-FLow/
    ├── .dockerignore
    ├── .env
    ├── .env.development
    ├── .eslintrc.json
    ├── .gitignore
    ├── .gitlab-ci.yml
    ├── .prettierrc.json
    ├── docker-compose.yml
    ├── Dockerfile
    ├── package-lock.json
    ├── package.json
    ├── public/
    │   ├── ...
    │   ├── assets/
    │   │   ├── ...
    │   │   ├── img/
    │   │   │   ├── ...
    │   │   │   ├── availability/
    │   │   │   │   └── ...
    │   │   │   ├── check/
    │   │   │   │   └── ...
    │   │   │   ├── forced/
    │   │   │   │   └── ...
    │   │   │   ├── header/
    │   │   │   │   └── ...
    │   │   │   ├── ist/
    │   │   │   │   └── ...
    │   │   │   ├── manual/
    │   │   │   │   └── ...
    │   │   │   ├── nav/
    │   │   │   │   └── ...
    │   │   │   ├── profile/
    │   │   │   │   └── ...
    │   │   │   ├── status/
    │   │   │   │   └── ...
    │   │   └── VectorFlow32.ico
    │   ├── base.css
    │   ├── index.html
    │   ├── manifest.json
    │   └── robots.txt
    ├── README.md
    ├── src/
    │   ├── app-routes.tsx
    │   ├── App.css
    │   ├── App.test.tsx
    │   ├── App.tsx
    │   ├── components/
    │   │   ├── commons/
    │   │   │   ├── ArrowList/
    │   │   │   │   └── index.tsx
    │   │   │   ├── ButtonCheck/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.css
    │   │   │   ├── ButtonFloat/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── style.ts
    │   │   │   ├── ButtonNormal/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── style.ts
    │   │   │   ├── ButtonOutline/
    │   │   │   │   ├── button.tsx
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.ts
    │   │   │   ├── ButtonOutlineCheck/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.ts
    │   │   │   ├── ButtonOutlineIcon/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── style.ts
    │   │   │   ├── Checkbox/
    │   │   │   │   ├── CheckboxAvailability.tsx
    │   │   │   │   ├── CheckboxPendingRequest.tsx
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── style.css
    │   │   │   ├── ContentLogin/
    │   │   │   │   └── index.tsx
    │   │   │   ├── DataLoading/
    │   │   │   │   └── index.tsx
    │   │   │   ├── Errors/
    │   │   │   │   └── index.tsx
    │   │   │   ├── InputSearchList/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.ts
    │   │   │   ├── LazyLoad/
    │   │   │   │   └── index.tsx
    │   │   │   ├── ListItemInput/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.ts
    │   │   │   ├── LoadingSpinner/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.css
    │   │   │   ├── LoginHead/
    │   │   │   │   └── index.tsx
    │   │   │   ├── Modal/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.css
    │   │   │   ├── ModalAdvanedPermissions/
    │   │   │   │   ├── index.tsx
    │   │   │   │   ├── LocationPermission.tsx
    │   │   │   │   ├── ProductPermission.tsx
    │   │   │   │   └── styles.css
    │   │   │   ├── ModalAvailabilityComparison/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.css
    │   │   │   ├── ModalContact/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.css
    │   │   │   ├── ModalForced/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.css
    │   │   │   ├── ModalManageUsers/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.css
    │   │   │   ├── NotFound/
    │   │   │   │   └── index.tsx
    │   │   │   ├── Pagination/
    │   │   │   │   ├── index.tsx
    │   │   │   │   ├── style.ts
    │   │   │   │   └── styles.css
    │   │   │   ├── SearchInput/
    │   │   │   │   └── index.tsx
    │   │   │   ├── SearchInputMultiple/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── style.ts
    │   │   │   ├── SelectInput/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.ts
    │   │   │   ├── SelectSearch/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.css
    │   │   │   ├── SelectSearchMultiple/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── style.ts
    │   │   │   ├── SelectSearchResetFilter/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.css
    │   │   │   ├── Spinner/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.css
    │   │   │   ├── SwitchButton/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.css
    │   │   │   ├── SwitchButtonAvailability/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.css
    │   │   │   ├── SwitchButtonStoreStatus/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.css
    │   │   │   ├── TabAvailabilityComparison/
    │   │   │   │   ├── AvailabilityActiveTab.tsx
    │   │   │   │   └── styles.ts
    │   │   │   ├── Table/
    │   │   │   │   ├── index.tsx
    │   │   │   │   ├── style.ts
    │   │   │   │   └── tableItem.tsx
    │   │   │   ├── TableForced/
    │   │   │   │   ├── index.tsx
    │   │   │   │   ├── style.ts
    │   │   │   │   └── tableItem.tsx
    │   │   │   ├── TableStore/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── style.ts
    │   │   │   ├── TableUserManagement/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── style.ts
    │   │   │   ├── Tooltip/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.css
    │   │   │   └── VerticalPartitions/
    │   │   │       ├── index.tsx
    │   │   │       └── style.ts
    │   │   ├── index.ts
    │   │   └── layouts/
    │   │       ├── AppLayout/
    │   │       │   ├── AuthenticationTemplate.tsx
    │   │       │   └── index.tsx
    │   │       ├── Footer/
    │   │       │   └── index.tsx
    │   │       ├── Header/
    │   │       │   ├── index.tsx
    │   │       │   └── style.ts
    │   │       ├── LocationFilter/
    │   │       │   ├── common-filter.tsx
    │   │       │   ├── index.tsx
    │   │       │   └── styles.ts
    │   │       ├── ModuleLayout/
    │   │       │   └── index.tsx
    │   │       ├── Navbar/
    │   │       │   ├── index.tsx
    │   │       │   ├── listMenu.tsx
    │   │       │   ├── particulars.tsx
    │   │       │   └── styles.ts
    │   │       ├── NavigationTab/
    │   │       │   ├── index.tsx
    │   │       │   └── styles.ts
    │   │       └── ProductFilter/
    │   │           ├── common-filter.tsx
    │   │           ├── index.tsx
    │   │           └── styles.ts
    │   ├── config/
    │   │   ├── axios-config.tsx
    │   │   └── react-query-config.ts
    │   ├── context/
    │   │   ├── index.ts
    │   │   ├── ISTStatusContext.ts
    │   │   └── UserDataContext.ts
    │   ├── helpers/
    │   │   ├── constants.ts
    │   │   ├── format.ts
    │   │   ├── notify.ts
    │   │   └── utils.ts
    │   ├── hooks/
    │   │   ├── index.ts
    │   │   ├── useDebouncedSearch.ts
    │   │   └── useSearchParameters.ts
    │   ├── i18n/
    │   │   ├── config.js
    │   │   └── locales/
    │   │       ├── en/
    │   │       │   └── translations.json
    │   │       ├── es/
    │   │       │   └── translations.json
    │   │       └── ja/
    │   │           └── translations.json
    │   ├── index.css
    │   ├── index.tsx
    │   ├── logo.svg
    │   ├── module-main/
    │   │   ├── app-routes-main.tsx
    │   │   ├── constants.ts
    │   │   ├── pages/
    │   │   │   ├── change-password/
    │   │   │   │   └── index.tsx
    │   │   │   ├── forgot-password/
    │   │   │   │   └── index.tsx
    │   │   │   ├── home/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.ts
    │   │   │   ├── login/
    │   │   │   │   ├── index.tsx
    │   │   │   │   ├── login.css
    │   │   │   │   └── style.ts
    │   │   │   ├── profile/
    │   │   │   │   └── index.tsx
    │   │   │   └── register/
    │   │   │       ├── index.tsx
    │   │   │       └── styles.ts
    │   │   ├── services/
    │   │   │   ├── api.ts
    │   │   │   └── index.ts
    │   │   └── types/
    │   │       ├── index.ts
    │   │       └── User.ts
    │   ├── module-store-transfer/
    │   │   ├── app-routes-store-transfer.tsx
    │   │   ├── constants.ts
    │   │   ├── pages/
    │   │   │   ├── availability-comparison/
    │   │   │   │   ├── index.tsx
    │   │   │   │   ├── location-filter.tsx
    │   │   │   │   ├── product-filter.tsx
    │   │   │   │   └── styles.ts
    │   │   │   ├── forbidden/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.ts
    │   │   │   ├── ist-forced/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styes.ts
    │   │   │   ├── ist-status/
    │   │   │   │   ├── index.tsx
    │   │   │   │   ├── style.css
    │   │   │   │   ├── styles.ts
    │   │   │   │   └── views.tsx
    │   │   │   ├── manage-users/
    │   │   │   │   ├── index.tsx
    │   │   │   │   ├── listRoles.tsx
    │   │   │   │   └── styles.ts
    │   │   │   ├── manual-upload/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.ts
    │   │   │   ├── notFound/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.ts
    │   │   │   ├── overview/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.ts
    │   │   │   ├── permissions/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.ts
    │   │   │   ├── profile/
    │   │   │   │   ├── index.tsx
    │   │   │   │   └── styles.ts
    │   │   │   └── store-status/
    │   │   │       ├── index.tsx
    │   │   │       ├── location-filter.tsx
    │   │   │       └── styles.ts
    │   │   ├── services/
    │   │   │   ├── AvailabilityComparison/
    │   │   │   │   └── api.ts
    │   │   │   ├── IstStatus/
    │   │   │   │   └── api.ts
    │   │   │   ├── ManualUpload/
    │   │   │   │   ├── api.ts
    │   │   │   │   └── index.ts
    │   │   │   └── PendingISTRequests/
    │   │   │       ├── api.ts
    │   │   │       └── index.ts
    │   │   └── types/
    │   │       ├── index.ts
    │   │       └── ManualUpload.ts
    │   ├── react-app-env.d.ts
    │   ├── reportWebVitals.ts
    │   ├── services/
    │   │   ├── forced/
    │   │   │   ├── api.ts
    │   │   │   └── index.ts
    │   │   ├── ist/
    │   │   │   ├── api.ts
    │   │   │   └── index.ts
    │   │   ├── profile/
    │   │   │   ├── api.ts
    │   │   │   └── index.ts
    │   │   └── store-status/
    │   │       ├── api.ts
    │   │       └── index.ts
    │   ├── setupTests.ts
    │   ├── styles/
    │   │   ├── global.ts
    │   │   └── gridSystem.ts
    │   └── types/
    │       ├── forced.ts
    │       ├── index.ts
    │       ├── ist.ts
    │       ├── profile.ts
    │       ├── store.ts
    │       └── TError.ts
    ├── tsconfig.json
    ├── tsconfig.paths.json
    └── yarn.lock
```

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.<br>
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

The page will reload if you make edits.<br>
You will also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.<br>

### `npm run build`

Builds the app for production to the `build` folder.<br>
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.<br>
Your app is ready to be deployed!

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can’t go back!**

If you aren’t satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (Webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you’re on your own.

You don’t have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn’t feel obligated to use this feature. However we understand that this tool wouldn’t be useful if you couldn’t customize it when you are ready for it.

## Dependencies

### 1. Clone project

```bash
  git clone https://git.tinhvan.com/vector-flow/ist-portal.git
```

### 2. Run from local dev

##### Config `.env` file and change REACT_APP_API_HOST to your local API host in `.env` file

```bash
  cp .env.example .env
```

##### Install dependencies

```bash
  npm install
```

##### Run project

```bash
  npm start
```

##### View project at: http://localhost:3000

### 3. Run from production with docker

##### Config `docker-compose.yml` file and change REACT_APP_API_HOST to your API host in `docker-compose.yml` file

```bash
  cp docker-compose.yml.example docker-compose.yml
```

##### Run project

```bash
  docker-compose up -d --build
```

### 4. Config nginx and SSL for production

##### Install nginx

```bash
  sudo apt-get install nginx
```

##### Copy SSL certificate to server

please copy your SSL certificate to `/usr/local/ssl/certificate` folder

##### Create file nginx config

```bash
  sudo nano /etc/nginx/sites-available/vector-portal
```

##### Paste config below to file nginx config

```bash
server {
  listen 80;
  server_name vector.tinhvan.com; # change to your domain
  return 301 https://$host$request_uri; # redirect all http requests to https
}

server {
      listen 443 ssl http2;
      listen [::]:443 ssl http2;

      root http://localhost:3000;

      # Add index.php to the list if you are using PHP
      index index.html index.htm index.nginx-debian.html;

      server_name vector.tinhvan.com; # change to your domain

      ssl_certificate /usr/local/ssl/certificate/certificate.crt; # change to your SSL certificate
      ssl_certificate_key /usr/local/ssl/certificate/certificate.key; # change to your SSL certificate key

      error_page 502 /502.html;
      location /502.html {
              root /var/www/html;
      }

      location /public/email_image/ {
              alias /home/gitlab-runner/data/vector-dev/email_image/;
              try_files $uri $uri/ =404;
      }

      location /public/issue/images/ {
              alias /home/gitlab-runner/data/vector-dev/issue/images/;
              try_files $uri $uri/ =404;
      }

      location / {
              # First attempt to serve request as file, then
              # as directory, then fall back to displaying a 404.
              try_files $uri $uri @backend;
      }
      location @backend {
              proxy_pass http://localhost:3000;
              proxy_set_header X-Real-IP $remote_addr;
              proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
              proxy_set_header Host $http_host;
              proxy_http_version 1.1;
              proxy_set_header X-NginX-Proxy true;
              proxy_set_header Upgrade $http_upgrade;
              proxy_set_header Connection "upgrade";
              proxy_cache_bypass $http_upgrade;
              proxy_redirect off;
              proxy_set_header X-Forwarded-Proto $scheme;
      }
}
```

##### Create symlink

```bash
  sudo ln -s /etc/nginx/sites-available/vector-portal /etc/nginx/sites-enabled/default
```

##### Restart nginx

```bash
  sudo systemctl restart nginx
```

##### View project at: http://{your_domain}
