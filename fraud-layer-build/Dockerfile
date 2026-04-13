FROM public.ecr.aws/lambda/python:3.11

WORKDIR /var/task

# Install zip utility
RUN yum install -y zip

# Install only numpy
RUN pip install numpy==1.26.4 -t python/

# Package the layer
RUN zip -r fraud-layer.zip python