"""
检查 Redis 中的所有数据，包括队列和结果
"""

import redis
import json

redis_url = 'redis://:200105@172.26.18.38:6379'

try:
    r = redis.from_url(redis_url, decode_responses=False)  # 不解码，保留原始数据
    
    print("=" * 70)
    print("Redis 数据检查")
    print("=" * 70)
    
    # 1. 查看所有 key
    all_keys = r.keys('*')
    print(f"\n📊 Redis 中所有 Key ({len(all_keys)} 个):")
    
    if not all_keys:
        print("  (空)")
    else:
        for key in all_keys:
            key_type = r.type(key)
            ttl = r.ttl(key)
            size = r.memory_usage(key)
            
            # 根据类型显示内容
            if key_type == b'list':
                length = r.llen(key)
                print(f"  📋 {key.decode()} (LIST, 长度: {length}, TTL: {ttl}s, 大小: {size}B)")
            elif key_type == b'string':
                try:
                    value = r.get(key)
                    if len(value) > 100:
                        print(f"  📝 {key.decode()} (STRING, TTL: {ttl}s, 大小: {size}B)")
                        print(f"     内容: {value[:100].decode('utf-8', errors='ignore')}...")
                    else:
                        print(f"  📝 {key.decode()} (STRING, TTL: {ttl}s, 大小: {size}B)")
                        print(f"     内容: {value.decode('utf-8', errors='ignore')}")
                except:
                    print(f"  📝 {key.decode()} (STRING, TTL: {ttl}s, 大小: {size}B)")
            elif key_type == b'hash':
                length = r.hlen(key)
                print(f"  🗂️  {key.decode()} (HASH, 字段数: {length}, TTL: {ttl}s, 大小: {size}B)")
            else:
                print(f"  ❓ {key.decode()} (type: {key_type.decode()}, TTL: {ttl}s, 大小: {size}B)")
    
    # 2. 查看队列内容
    print("\n" + "=" * 70)
    print("队列内容检查")
    print("=" * 70)
    
    queue_key = b'huey.redis.pdftasks'
    queue_length = r.llen(queue_key)
    print(f"\n队列 'huey.redis.pdftasks' 长度: {queue_length}")
    
    if queue_length > 0:
        print("队列中的任务:")
        for i in range(min(3, queue_length)):
            item = r.lindex(queue_key, i)
            print(f"  [{i}] {item[:100]}...")
    
    # 3. 查看 Huey 相关的 key
    print("\n" + "=" * 70)
    print("Huey 相关 Key")
    print("=" * 70)
    
    huey_keys = r.keys('huey*')
    print(f"\n找到 {len(huey_keys)} 个 Huey 相关的 key:")
    for key in huey_keys:
        key_type = r.type(key)
        ttl = r.ttl(key)
        print(f"  - {key.decode()} (type: {key_type.decode()}, TTL: {ttl}s)")
    
    # 4. 查看 Redis 统计信息
    print("\n" + "=" * 70)
    print("Redis 统计信息")
    print("=" * 70)
    
    info = r.info('stats')
    print(f"\n总键数: {info.get('total_commands_processed', 'N/A')}")
    print(f"内存使用: {r.info('memory').get('used_memory_human', 'N/A')}")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
