FROM thehiveproject/cortex:3.1.4-1

# Use Debian archive repositories for Buster
RUN sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    sed -i '/buster-updates/d' /etc/apt/sources.list

# Install Python dependencies for Cortex analyzers
RUN apt-get update && \
    apt-get install -y python3 python3-pip python2 python-pip && \
    pip3 install cortexutils && \
    pip install cortexutils || true && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
