from time import sleep

from src.services.translation_cache import TranslationCache


def test_add_get_and_hit_rate():
    cache = TranslationCache(max_size=10, ttl_seconds=60)
    assert cache.get("hello", "en", "ru") is None
    cache.add("hello", "привет", "en", "ru")
    assert cache.get("hello", "en", "ru") == "привет"
    stats = cache.get_stats()
    assert stats["hits"] == 1 and stats["misses"] == 1
    assert stats["size"] == 1


def test_ttl_expiration():
    cache = TranslationCache(max_size=10, ttl_seconds=1)
    cache.add("bye", "пока", "en", "ru")
    assert cache.get("bye", "en", "ru") == "пока"
    sleep(1.1)
    assert cache.get("bye", "en", "ru") is None


def test_eviction_lru():
    cache = TranslationCache(max_size=2, ttl_seconds=60)
    cache.add("a", "A", "en", "ru")
    cache.add("b", "B", "en", "ru")
    # touch 'a' to make 'b' LRU
    assert cache.get("a", "en", "ru") == "A"
    # adding 'c' should evict 'b'
    cache.add("c", "C", "en", "ru")
    assert cache.get("b", "en", "ru") is None
    assert cache.get("a", "en", "ru") == "A"
    assert cache.get("c", "en", "ru") == "C"


def test_save_and_load(tmp_path):
    cache = TranslationCache(max_size=10, ttl_seconds=60)
    cache.add("x", "X", "en", "ru")
    file = tmp_path / "cache.json"
    cache.save_to_file(str(file))

    cache2 = TranslationCache(max_size=10, ttl_seconds=60)
    loaded = cache2.load_from_file(str(file))
    assert loaded == 1
    assert cache2.get("x", "en", "ru") == "X"


