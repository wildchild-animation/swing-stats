# -*- coding: utf-8 -*-

# Utility function to connect to Treehouse / Kitsu Database
import sys
import psycopg2
import traceback

import logging
log = logging.getLogger(__name__)

from settings import PROD_DATABASE

def connect():
    connection = None
    try:
        connection = psycopg2.connect(
            host = PROD_DATABASE['reporting']['host'],
            port = PROD_DATABASE['reporting']['port'],
            database = PROD_DATABASE['reporting']['database'],
            user = PROD_DATABASE['reporting']['user'],
            password = PROD_DATABASE['reporting']['password']
        )
        return connection, connection.cursor()

    except Exception:
        log.error("Error connecting to reporting database")
        traceback.print_exc(file=sys.stdout)
        return None


def close(connection):
    if connection:
        connection.close()
        log.info("Connection closed")
    else:
        log.error("Connection is already closed")
    return None

def project_data(cursor):
    cursor.execute('select id, name, start_date, end_date from project')
    return cursor.fetchall()
