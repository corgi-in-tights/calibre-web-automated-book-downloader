def cached_lookup(cache, lock, key, loader):
    with lock:
        if key in cache:
            return cache[key]
    result = loader()
    with lock:
        cache[key] = result
    return result
