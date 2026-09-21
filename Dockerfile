ARG PYTHON_IMAGE
FROM ${PYTHON_IMAGE}

WORKDIR /app

COPY pyproject.toml .
COPY main.py cli.py config.py mirror_sync.py update_pat.py ./
RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "main.py"]
CMD ["sync"]
