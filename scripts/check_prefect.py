from prefect import flow, task


@task
def say_ready() -> str:
    return "Prefect is ready to run data pipelines!"


@flow
def phase1_smoke_flow():
    result = say_ready()
    print(f"Result: {result}")


if __name__ == "__main__":
    phase1_smoke_flow()
