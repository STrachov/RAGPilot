127214165550.dkr.ecr.eu-north-1.amazonaws.com/api_template/v1:latest
aws configure  # Set AWS credentials
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 127214165550.dkr.ecr.eu-north-1.amazonaws.com
aws ecr create-repository --repository-name fastapi-backend
aws ecr create-repository --repository-name nginx-frontend
 
# AWS credentials should be stored securely, not in version control
# Use environment variables or AWS credential manager instead

docker build -t fastapi-backend ./backend
docker tag fastapi-backend:latest 127214165550.dkr.ecr.eu-north-1.amazonaws.com/fastapi-backend:latest
docker push 127214165550.dkr.ecr.eu-north-1.amazonaws.com/fastapi-backend:latest

aws ecr create-repository --repository-name nginx-frontend
docker build -t nginx-frontend ./frontend
docker tag nginx-frontend:latest 127214165550.dkr.ecr.eu-north-1.amazonaws.com/nginx-frontend:latest
docker push 127214165550.dkr.ecr.eu-north-1.amazonaws.com/nginx-frontend:latest
