def get_cors_headers(origin='*', methods=None, headers_list=None):
    if methods is None:
        methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    if headers_list is None:
        headers_list = ['Content-Type', 'Authorization']
    return {
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Methods': ', '.join(methods),
        'Access-Control-Allow-Headers': ', '.join(headers_list)
    }
