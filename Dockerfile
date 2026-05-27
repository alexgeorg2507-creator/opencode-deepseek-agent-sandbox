FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/usr/local/bin:/home/agent/.local/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    jq \
    less \
    nano \
    bash \
    python3 \
    python3-pip \
    nodejs \
    npm \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g opencode-ai

ARG USERNAME=agent
ARG USER_UID=1001
ARG USER_GID=1001

RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m -s /bin/bash ${USERNAME}

USER ${USERNAME}
WORKDIR /workspace

CMD ["/bin/bash"]
