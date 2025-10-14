FROM locustio/locust AS locust
workdir /mnt/ib-api-perf
COPY . .
RUN pip install -r requirements.txt