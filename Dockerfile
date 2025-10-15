FROM locustio/locust AS locust
# Changing the working directory to /mnt/ib-api-perf
WORKDIR /mnt/ib-api-perf
# Copying all the files from the current directory to /mnt/ib-api-perf in the container
COPY . .
# Installing the required Python packages from requirements.txt
RUN pip install -r requirements.txt