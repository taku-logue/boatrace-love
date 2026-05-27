import mlflow

# MLflowサーバーの向き先を設定
mlflow.set_tracking_uri("http://127.0.0.1:5000")

# 実験の名前を設定
mlflow.set_experiment("phase1_smoke_test")

# ダミーの学習記録を送信
with mlflow.start_run():
    mlflow.log_param("phase", 1)
    mlflow.log_metric("smoke_test", 1.0)
    print("MLflow dummy run successfully registered!")