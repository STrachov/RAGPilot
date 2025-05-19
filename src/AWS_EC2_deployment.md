# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install docker.io -y
sudo systemctl start docker
sudo systemctl enable docker

# Install Docker Compose
sudo apt install docker-compose -y

# Check installation
docker --version
docker-compose --version


git clone https://github.com/STrachov/ml-template-deploy.git
cd ml-template-deploy/src

docker-compose up --build

