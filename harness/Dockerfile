FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
COPY src src
RUN pip install --no-cache-dir '.[databases]'
COPY harness/app.py /fixture/app.py
ENV PYTHONDONTWRITEBYTECODE=1
USER 1000:1000
CMD ["python", "/fixture/app.py"]
