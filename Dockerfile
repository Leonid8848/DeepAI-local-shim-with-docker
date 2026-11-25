FROM python:3.12-slim
WORKDIR /app
COPY deepai-shim.py /app/deepai-shim.py
ENV DEEPAI_SHIM_BIND=0.0.0.0
EXPOSE 9100
CMD ["python", "/app/deepai-shim.py", "9100"]
