from prefect_flows.flows import scheduled_pipeline_run, db_maintenance_flow


def register_deployments():
    scheduled_pipeline_run.serve(
        name="daily-pipeline-run",
        cron="0 8 * * *",
        parameters={"query": "Summarise the latest developments in large language models"},
        tags=["scheduled", "pipeline"],
    )

    db_maintenance_flow.serve(
        name="nightly-db-maintenance",
        cron="0 2 * * *",
        parameters={"purge_days": 30},
        tags=["maintenance", "database"],
    )


if __name__ == "__main__":
    register_deployments()
