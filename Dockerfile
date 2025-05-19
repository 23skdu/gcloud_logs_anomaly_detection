FROM python:3.13.3-slim
LABEL author=23skdu@users.noreply.github.com
RUN apt update && apt -y upgrade && apt clean
RUN pip3 install --no-cache-dir tzdata pandas scikit-learn google-cloud-logging seaborn 
CMD ["python","-c", "print('works')"]
