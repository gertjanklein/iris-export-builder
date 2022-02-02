# The IRIS image to use
ARG IMAGE=store/intersystems/iris-community:2021.2.0.649.0

FROM $IMAGE

# Copy script that loads the files
COPY iris.script iris.script

# Run it
RUN iris start IRIS \
  && iris session IRIS < iris.script \
  && iris stop IRIS quietly
