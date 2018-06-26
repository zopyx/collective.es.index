from celery.utils.log import get_task_logger
from collective.es.index.utils import get_ingest_client
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from Testing.makerequest import makerequest
from ZODB.POSException import ConflictError
from celery import Celery, Task
from elasticsearch.exceptions import NotFoundError
from kombu.utils import uuid as kombu_uuid
from transaction.interfaces import ISynchronizer
from zope.app.publication.interfaces import BeforeTraverseEvent
from zope.component.hooks import setSite
from zope.event import notify
from zope.interface import implementer
from zope.globalrequest import getRequest
import os
import sys
import transaction
import Zope2

logger = get_task_logger(__name__)
BROKER_URL = os.environ.get('CELERY_BROKER', 'redis://localhost//')
ZOPE_CONFIG = os.environ.get('ZOPE_CONFIG', 'parts/client1/etc/zope.conf')
celery = Celery('collective.es.index.tasks',
                broker=BROKER_URL, backend=BROKER_URL)


@implementer(ISynchronizer)
class CelerySynchronizer(object):
    """Handles communication with celery at transaction boundaries.
    We previously used after-commit hooks, but the transaction package
    swallows exceptions in commit hooks.
    """

    def beforeCompletion(self, txn):
        pass

    def afterCompletion(self, txn):
        """Called after commit or abort
        """
        # Skip if running tests
        import collective.es.index
        if collective.es.index.TESTING:
            return False
        if txn.status == transaction._transaction.Status.COMMITTED:
            tasks = getattr(txn, '_celery_tasks', [])
            for task, args, kw in tasks:
                Task.apply_async(task, *args, **kw)

    def newTransaction(self, txn):
        txn._celery_tasks = []

# It's important that we assign the synchronizer to a variable,
# because the transaction manager stores it using a weak reference.
celery_synch = CelerySynchronizer()


def queue_task_after_commit(task, args, kw):
    transaction.manager.registerSynch(celery_synch)

    txn = transaction.get()
    if not hasattr(txn, '_celery_tasks'):
        txn._celery_tasks = []
    txn._celery_tasks.append((task, args, kw))


class AfterCommitTask(Task):
    """Base for tasks that queue themselves after commit.
    This is intended for tasks scheduled from inside Zope.
    """
    abstract = True
    executing = False

    # Override apply_async to register an after-commit hook
    # instead of queueing the task right away.
    def apply_async(self, *args, **kw):
        # This flag is to make sure we queue retries immediately.
        if self.executing:
            return super(AfterCommitTask, self).apply_async(*args, **kw)

        task_id = kombu_uuid()
        request = getRequest()
        kw['task_id'] = task_id
        queue_override = getattr(request, '_celery_queue', None)
        if queue_override:
            kw['queue'] = queue_override

        queue_task_after_commit(self, args, kw)
        return celery.AsyncResult(task_id)


def zope_task(**task_kw):
    """Decorator of celery tasks that should be run in a Zope context.
    The decorator function takes a path as a first argument,
    and will take care of traversing to it and passing it
    (presumably a portal) as the first argument to the decorated function.
    Also takes care of initializing the Zope environment,
    running the task within a transaction, and retrying on
    ZODB conflict errors.
    """

    def wrap(func):
        def new_func(self, *args, **kw):
            self.executing = True
            site_path = kw.get('site_path', 'Plone')
            site_path = site_path.strip().strip('/')

            sys.argv = ['']
            from Zope2.Startup.run import configure
            startup = configure(ZOPE_CONFIG)
            es_servers = [s for s in startup.cfg.servers
                          if 'ElasticSearchIngressConf' in str(s)]
            if es_servers:
                es_servers[0].create()
            app = makerequest(Zope2.app())

            transaction.begin()

            try:
                try:
                    # find site
                    site = app.unrestrictedTraverse(site_path)
                    # fire traversal event so various things get set up
                    notify(BeforeTraverseEvent(site, site.REQUEST))

                    # set up admin user
                    user = app.acl_users.getUserById('admin')
                    newSecurityManager(None, user)

                    # run the task
                    result = func(site, *args, **kw)

                    # commit transaction
                    transaction.commit()
                except ConflictError as e:
                    # On ZODB conflicts, retry using celery's mechanism
                    transaction.abort()
                    raise self.retry(exc=e)
                except:
                    transaction.abort()
                    raise
            finally:
                noSecurityManager()
                setSite(None)
                app._p_jar.close()

            return result
        new_func.__name__ = func.__name__
        task_kw['bind'] = True
        return celery.task(**task_kw)(new_func)
    return wrap


@zope_task(base=AfterCommitTask)
def index_content(portal, url, data):
    logger.warning('Indexing {}'.format(url))
    es = get_ingest_client()
    if es is None:
        logger.warning('Elasticsearch client not found for indexing.')
        return
    try:
        es.index(**data)
    except Exception:
        logger.exception(
            'indexing of {0} failed.'.format(
                url,
            ),
        )
    logger.warning('Finished indexing {}'.format(url))


@zope_task(base=AfterCommitTask)
def unindex_content(portal, index, doc_type, uid, timeout):
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
    logger.warning('Finished unindexing {}'.format(uid))
