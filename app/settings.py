# Point to local Kitsu instance
PROD_DATABASE = {
    'reporting': {
        # 'host': '172.16.16.165',
        # 'host': '172.16.16.79',
        #'host': '172.16.16.124', ## RoadRunner
        'host': '127.0.0.1', ## Coyote
        'port': 5432,
        'database': 'swingdata',
        'user': 'postgres',
        'password': 'postgres'
    }
}
