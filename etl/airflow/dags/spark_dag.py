from datetime import datetime
import os

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount


PROJECT_DIR = os.environ["PROJECT_DIR"]

with DAG(
    dag_id="minimal_pyspark_dag",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
) as dag:

    run_pyspark = DockerOperator(
        task_id="run_pyspark_job",
        image="apache/spark:latest",
        command="/opt/spark/bin/spark-submit /workspace/jobs/sample_pyspark.py",
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
        auto_remove="success",
        mount_tmp_dir=False,
        mounts=[
            Mount(
                source=PROJECT_DIR,
                target="/workspace",
                type="bind",
            )
        ],
    )