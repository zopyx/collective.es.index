from ZODB.POSException import POSKeyError
from celery.utils.log import get_task_logger
from collective.celery import task
from collective.es.index.utils import get_ingest_client
from elasticsearch.exceptions import NotFoundError
from zope.component import queryUtility
from zope.component.hooks import getSite

try:
    from Products.CMFCore.interfaces import IIndexQueueProcessor
except ImportError:
    from collective.indexing.interfaces import IIndexQueueProcessor


logger = get_task_logger(__name__)


def extra_config(startup):
    es_servers = [s for s in startup.cfg.servers
                  if 'ElasticSearchIngressConf' in str(s)]
    if es_servers:
        logger.warning('Found Elasticsearch server for indexing.')
        es_servers[0].create()


@task(name='indexer', autoretry_for=(POSKeyError,), retry_backoff=5)
def index_content(path):
    logger.warning('Indexing {}'.format(path))
    es = get_ingest_client()
    if es is None:
        logger.warning('Elasticsearch client not found for indexing.')
        return
    site = getSite()
    obj = site.unrestrictedTraverse(path)
    indexer = queryUtility(IIndexQueueProcessor, name='collective.es.index')
    data = indexer.get_payload(obj)
    try:
        es.index(**data)
    except Exception:
        logger.exception(
            'indexing of {0} failed.'.format(
                path,
            ),
        )


@task(name='unindexer')
def unindex_content(index, doc_type, uid, timeout):
    logger.warning('Unindexing {}'.format(uid))
    es = get_ingest_client()
    if es is None:
        logger.warning('Elasticsearch client not found for indexing.')
        return
    try:
        es.delete(index=index,
                  doc_type=doc_type,
                  id=uid,
                  request_timeout=timeout)
    except NotFoundError:
        logger.warning('Content already unindexed.')
        pass
    except Exception:
        logger.exception(
            'unindexing of {0} failed.'.format(
                uid,
            ),
        )
