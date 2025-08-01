FROM --platform=linux/amd64 public.ecr.aws/docker/library/python:3.12-slim
EXPOSE 8501
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip3 install --upgrade pip && pip3 install -r requirements.txt
COPY . .
CMD streamlit run app.py