# File/folder structure of the project
src
├───docker-compose.yml
├───nginx.conf
├───ssl
│   ├───cert.pem
│   ├───csr.pem
│   └───key.pem
├───backend
│   ├───app
│   │   ├───main.py
│   │   └───...
│   ├───Dockerfile
│   └───...
└───frontend
    ├───bootstrap
    │   └───v1
    │       ├───dist
    │       │    └...
    │       ├───index.html
    │       ├───login.html
    │       └...
    ├───nginx.conf
    └───Dockerfile
