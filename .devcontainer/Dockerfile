FROM python:3.14-slim

# Install basic system packages and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create or update non-root user matching host UID/GID.
# Guard against negative values caused by some local host environments.
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=1000

RUN if [ "$USER_UID" -lt 1 ] || [ "$USER_GID" -lt 1 ]; then \
        USER_UID=1000; \
        USER_GID=1000; \
    fi; \
    test "$USER_UID" -gt 0 && test "$USER_GID" -gt 0 || { echo "USER_UID and USER_GID must be positive integers. If host user IDs are unavailable, set them explicitly or disable updateRemoteUserUID."; exit 1; } \
    && if getent group $USER_GID > /dev/null 2>&1; then \
        EXISTING_GROUP=$(getent group $USER_GID | cut -d: -f1); \
        if [ "$EXISTING_GROUP" != "$USERNAME" ]; then \
            groupmod -n $USERNAME $EXISTING_GROUP; \
        fi; \
    else \
        groupadd --gid $USER_GID $USERNAME; \
    fi \
    && if getent passwd $USER_UID > /dev/null 2>&1; then \
        EXISTING_USER=$(getent passwd $USER_UID | cut -d: -f1); \
        if [ "$EXISTING_USER" != "$USERNAME" ]; then \
            usermod -l $USERNAME -g $USER_GID -d /home/$USERNAME -m $EXISTING_USER; \
        fi; \
    else \
        useradd --uid $USER_UID --gid $USER_GID -m $USERNAME; \
    fi \
    && apt-get update && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && rm -rf /var/lib/apt/lists/* \
    && chsh -s /bin/bash $USERNAME

USER $USERNAME
WORKDIR /workspace
