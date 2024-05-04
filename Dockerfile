FROM public.ecr.aws/lambda/python:3.8
RUN pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
# コードをコンテナ内にコピー
COPY app.py ./
# AWS Lambdaはハンドラ関数を指定するためにCMDを使用。
CMD ["app.lambda_handler"]