import dramatiq
from dramatiq.brokers.redis import RedisBroker

from forgesight_api.worker.worker import process_inference_job

redis_broker = RedisBroker()
dramatiq.set_broker(redis_broker)


@dramatiq.actor
def run_inference(job_id: str):
    process_inference_job(job_id)
