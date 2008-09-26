import xmlrpclib
import socket
import time

try:
    from robot.errors import RemoteError
except ImportError:
    RemoteError = None


class Remote:
    
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self, uri='http://localhost:8270'):
        if '://' not in uri:
            uri = 'http://' + uri
        self._library = xmlrpclib.Server(uri)

    def get_keyword_names(self, attempts=5):
        for i in range(attempts):
            try:
                return self._library.get_keyword_names()
            except socket.error, (errno, err):
                time.sleep(1)
            except xmlrpclib.Error, err:
                err = err.faultString
                break
        raise RuntimeError('Connecting remote server failed: %s' % err)

    def get_keyword_arguments(self, name):
        try:
            return self._library.get_keyword_arguments(name)
        except (xmlrpclib.Error, socket.error):
            return ['*args']

    def get_keyword_documentation(self, name):
        try:
            return self._library.get_keyword_documentation(name)
        except (xmlrpclib.Error, socket.error):
            return ''

    def run_keyword(self, name, args):
        result = _Result(self._run_keyword(name, args))
        print result.output
        if result.status != 'PASS':
            self._raise_failed(result.error, result.traceback)
        return result.return_

    def _run_keyword(self, name, args):
        args = [ self._handle_argument(arg) for arg in args ]
        try:
            return self._library.run_keyword(name, args)
        except xmlrpclib.Error, err:
            raise RuntimeError(err.faultString)
        except socket.error, (errno, err):
            raise RuntimeError('Connection to remote server broken: %s' % err)

    def _handle_argument(self, arg):
        if isinstance(arg, (basestring, int, long, float, bool)):
            return arg
        if isinstance(arg, (tuple, list)):
            return [ self._handle_argument(item) for item in arg ]
        if isinstance(arg, dict):
            return dict([ (self._str(key), self._handle_argument(value))
                          for key, value in arg.items() ])
        return self._str(arg)

    def _str(self, item):
        if item is None:
            return ''
        return str(item)

    def _raise_failed(self, message, traceback):
        if RemoteError is not None:
            raise RemoteError(message, traceback)
        # Support for Robot Framework 2.0.2 and earlier.
        print '*INFO*', traceback
        raise AssertionError(message)


class _Result:

    def __init__(self, result):
        try:
            self.status = result['status']
            self.output = result.get('output', '')
            self.return_ = result.get('return', '')
            self.error = result.get('error', '')
            self.traceback = result.get('traceback', '')
        except (KeyError, AttributeError):
            raise RuntimeError('Invalid result dictionary: %s' % result)
