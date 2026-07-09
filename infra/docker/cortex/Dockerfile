FROM thehiveproject/cortex:3.2.0-1

# Install Python dependencies for Cortex analyzers
RUN rm -f /etc/apt/sources.list.d/corretto.list && \
    apt-get update && \
    apt-get install -y python3 python3-distutils curl && \
    curl -sS https://bootstrap.pypa.io/pip/3.9/get-pip.py | python3 && \
    pip3 install cortexutils && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
