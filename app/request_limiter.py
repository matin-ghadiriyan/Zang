#--- import the necessary modules ---
import time

#--- rate limit dictionary ---
dict_rate_limit = {}

def rate_limit(
    limit:int=120,
    ip:str=None,
    limit_time:int=120
)->bool:
    ''' rate limit function '''
    # --- get the current time ---
    now = time.time()

    # --- check if the ip is in the dict ---
    if ip not in dict_rate_limit:
        dict_rate_limit[ip] = {'count': 0, 'late_time': now}

    # --- get the count and late_time ---
    count , late_time = dict_rate_limit[ip]['count'] , dict_rate_limit[ip]['late_time']

    # --- check if the count is less than the limit ---
    if now - late_time >= limit_time:
        dict_rate_limit[ip] = {'count': 1, 'late_time': now}
        return True

    # --- check if the count is less than the limit ---
    elif count < limit:
        dict_rate_limit[ip] = {'count': count + 1, 'late_time': now}
        return True

    # --- return false ---
    return False