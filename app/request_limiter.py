#--- import the necessary modules ---
import time

from flask import request

#--- rate limit dictionary ---
dict_rate_limit = {}


def _client_ip() -> str:
    '''دریافت آی‌پی کاربر با در نظر گرفتن پروکسی'''
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def _cleanup(now: float, limit_time: int) -> None:
    '''پاک‌سازی رکوردهای منقضی برای جلوگیری از رشد حافظه'''
    if len(dict_rate_limit) < 1000:
        return
    expired = [
        key for key, value in dict_rate_limit.items()
        if now - value['late_time'] >= limit_time
    ]
    for key in expired:
        dict_rate_limit.pop(key, None)


def rate_limit(
    limit: int = 120,
    ip: str = None,
    limit_time: int = 120
) -> bool:
    ''' بررسی محدودیت درخواست '''
    # --- get the current time ---
    now = time.time()

    # --- resolve the ip ---
    if ip is None:
        ip = _client_ip()

    # --- cleanup expired records ---
    _cleanup(now, limit_time)

    # --- check if the ip is in the dict ---
    if ip not in dict_rate_limit:
        dict_rate_limit[ip] = {'count': 1, 'late_time': now}
        return True

    # --- get the count and late_time ---
    count, late_time = (
        dict_rate_limit[ip]['count'],
        dict_rate_limit[ip]['late_time']
    )

    # --- window expired, reset ---
    if now - late_time >= limit_time:
        dict_rate_limit[ip] = {'count': 1, 'late_time': now}
        return True

    # --- still under the limit ---
    if count < limit:
        dict_rate_limit[ip] = {'count': count + 1, 'late_time': now}
        return True

    # --- return false ---
    return False