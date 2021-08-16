from io import StringIO
import http
from time import sleep

from concurrent.futures import ThreadPoolExecutor, wait
import threading

import requests

import namespace as ns
from config import ConfigurationError


# Thread-local storage for requests session objects
tls = threading.local()


def convert(config:ns.Namespace, items:list, threads:int = 1):
    """ Converts a list of items from UDL to XML """

    if threads > 1:
        _convert_parallel(config, items, threads)
        return
    
    for item in items:
        _convert_to_xml(config, item)
    
    return


def _convert_parallel(config:ns.Namespace, items:list, threads:int):
    """ Converts items from UDL to XML in parallel """

    # Get data needed to initialize the requests sessions in the
    # threads to start, passed to the initializer function
    cookie_data = "#LWP-Cookies-2.0\n" + tls.session.cookies.as_lwp_str()
    args = (tls.session.auth, cookie_data)

    futures = []
    with ThreadPoolExecutor(max_workers=threads, 
            initializer=_init_thread, initargs=args) as executor:
        
        # Convert the items, and wait for all of them
        for item in items:
            futures.append(executor.submit(_convert_to_xml, config, item))
        wait(futures)
        
        # Make exceptions raised in a thread reraise here
        for future in futures:
            future.result()
        
        # Call cleanup code to release requests sessions
        futures.clear()
        for _ in range(threads):
            futures.append(executor.submit(_cleanup_thread))
        wait(futures)


def _convert_to_xml(config, item):
    """ Convert an IRIS source item from UDL to XML format """

    data = item.data.encode('UTF-8')

    svr = config.Server
    url = f"http://{svr.host}:{svr.port}/api/atelier/v1/{svr.namespace}/cvt/doc/xml"
    
    # Get and convert from JSON
    rsp = tls.session.post(url, data=data, headers={'Content-Type': 'text/plain; charset=utf-8'})
    data = rsp.json()
    
    # Errors are returned here, not in data['status']['errors']
    status = data['result']['status']
    if status:
        raise ValueError(f'Error converting {item.name} to XML: {status}.')
    content = data['result']['content']

    # Content has \r\n as line ending, but we want the 'internal' \n.
    content = content.replace('\r', '')
    item.xml = content
    

# -----

def setup_session(config:ns.Namespace):
    """ Setup requests session for XML->UDL conversion
    
    The session is needed to honour IRIS session cookies and HTTP
    keep-alive. To initialize the cookies, a single request is done
    as part of the initialization.
    """
    
    global tls

    svr = config.Server
    session = requests.Session()
    session.auth = (svr.user, svr.password)
    cookiefile = f"cookies;{svr['host']};{svr['port']}.txt"
    session.cookies = http.cookiejar.LWPCookieJar(cookiefile) # type: ignore
    url = f"http://{svr.host}:{svr.port}/api/atelier/"
    try:
        session.get(url)
    except requests.RequestException as e:
        msg = f"Error connecting to server for converting UDL to XML:\n{e}."
        raise ConfigurationError(msg) from None
    
    tls.session = session


def cleanup():
    """ Closes the main requests session """
    
    if hasattr(tls, "session"):
        tls.session.close()


# -----

def _init_thread(auth, cookie_data):
    """ Initializes the requests session object for a new thread """
    tls.session = requests.Session()
    if auth:
        tls.session.auth = auth
    if cookie_data:
        jar = http.cookiejar.LWPCookieJar()
        datastream = StringIO(cookie_data)
        jar._really_load(datastream, "<copy>", ignore_discard=True, ignore_expires=False)
        tls.session.cookies = jar


def _cleanup_thread():
    """ Closes the requests session before thread termination """

    if hasattr(tls, "session"):
        tls.session.close()
        # Slight delay so other threads get assigned a cleanup task as well
        sleep(0.005)


