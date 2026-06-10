FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml .
COPY main.py cli.py mirror_sync.py update_pat.py ./

ENTRYPOINT ["python", "main.py"]
CMD ["sync"]
