import time
import threading

from django.conf import settings

_LOCK = threading.Lock() # Глобальная блокировка для потокобезопасности
_LAST_MS = 0
_SEQ = 0

WORKER_ID = int(getattr(settings, "WORKER_ID", 0)) & 0x3FF  # 1024 вариантов

# Генерация Snowflake ID
def snowflake_id() -> int: 
    """
    Генерация уникального идентификатора в формате Snowflake.
    :return: Уникальный 64-битный целочисленный идентификатор.
    """
    """64-bit: [timestamp_ms << 22] | [worker_id << 12] | [sequence]"""
    global _LAST_MS, _SEQ # Используем глобальные переменные для состояния
    with _LOCK: # Обеспечиваем потокобезопасность
        ms = int(time.time() * 1000) # Текущее время в миллисекундах
        if ms == _LAST_MS: # Если в ту же миллисекунду
            _SEQ = (_SEQ + 1) & 0xFFF  # 12 бит, 0..4095
            if _SEQ == 0: # Если последовательность переполнилась,
                # ждём следующую миллисекунду
                while ms <= _LAST_MS: # Ждём следующую миллисекунду
                    ms = int(time.time() * 1000) # Обновляем текущее время
        else: # Новая миллисекунда
            _SEQ = 0 # Сбрасываем последовательность
            _LAST_MS = ms # Обновляем последнюю миллисекунду
        return (ms << 22) | (WORKER_ID << 12) | _SEQ # Формируем ID


if __name__ == "__main__":
    print(snowflake_id())