# The IRIS image to use
ARG IMAGE=containers.intersystems.com/intersystems/iris-community:2022.1.0.209.0

FROM $IMAGE

# Copy script that loads the files
COPY iris.script iris.script

# Run it
RUN iris start IRIS \
  && iris session IRIS < iris.script \
  && iris stop IRIS quietly
