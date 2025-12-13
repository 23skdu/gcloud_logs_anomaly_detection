FROM python:3.13-slim
LABEL author=23skdu@users.noreply.github.com
RUN apt-get update && apt-get -y upgrade && apt-get clean
RUN pip3 install --no-cache-dir tzdata==2025.2 pandas==2.3.3 scikit-learn==1.8.0 google-cloud-logging==3.12.1 seaborn==0.13.2
CMD ["python","-c", "print('works')"]
