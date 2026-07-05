# Pinned offline image: Python 3.11 + R + JDK + duckdb + the OHDSI R stack.
# Everything trcompile/trcheck/gates need runs inside here — no network at run time.
FROM rocker/r-ver:4.4.1

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 python3.11-venv python3-pip \
        openjdk-17-jdk-headless \
        libcurl4-openssl-dev libssl-dev libxml2-dev git \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# OHDSI R stack, pinned (see scripts/install_ohdsi.R).
COPY scripts/install_ohdsi.R /tmp/install_ohdsi.R
RUN Rscript /tmp/install_ohdsi.R

# Python deps.
COPY pyproject.toml /tmp/pyproject.toml
RUN python3.11 -m pip install --no-cache-dir \
        duckdb==1.1.3 pyyaml==6.0.2 jsonschema==4.23.0 pytest==8.3.3 ruff==0.6.9

WORKDIR /workspace
