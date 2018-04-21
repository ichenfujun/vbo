#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
A WSGI app for dev.
'''

from wsgiref.simple_server import make_server

import os, logging,sys
logging.basicConfig(level=logging.INFO)
curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
from transwarp import web, db

def create_app():
    return web.WSGIApplication(('urls',), document_root=os.path.dirname(os.path.abspath(__file__)), template_engine='jinja2', DEBUG=True)

if __name__=='__main__':
    logging.info('application will start...')
    server = make_server('123.56.232.149', 80, create_app())
    server.serve_forever()
