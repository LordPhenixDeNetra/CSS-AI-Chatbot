import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_logging():
    return logger


# Métriques Prometheus
query_counter = Counter('rag_queries_total', 'Total queries processed', ['provider', 'status'])
response_time_histogram = Histogram('rag_response_time_seconds', 'Response time distribution')
accuracy_gauge = Gauge('rag_accuracy_score', 'Current accuracy score')
cache_hit_counter = Counter('rag_cache_hits_total', 'Total cache hits', ['cache_type'])
