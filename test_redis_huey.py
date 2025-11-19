"""
测试 Redis 和 Huey 连接
"""

import os

# 确保 HUEY_IMMEDIATE 是 false
os.environ['HUEY_IMMEDIATE'] = 'false'

import redis
from pipelines.tasks import huey

# 1. 测试 Redis 连接
print("=" * 60)
print("1. 测试 Redis 连接")
print("=" * 60)

redis_url = os.getenv('HUEY_REDIS_URL', 'redis://:200105@localhost:6379')
print(f"Redis URL: {redis_url}")

try:
    # 解析 Redis URL
    r = redis.from_url(redis_url, decode_responses=True)
    ping_result = r.ping()
    print(f"✅ Redis 连接成功: {ping_result}")
    
    # 查看所有 key
    all_keys = r.keys('*')
    print(f"\n📊 Redis 中所有 Key ({len(all_keys)} 个):")
    for key in all_keys:
        key_type = r.type(key)
        ttl = r.ttl(key)
        print(f"  - {key} (type: {key_type}, TTL: {ttl}s)")
    
    # 查看 Huey 相关的 key
    huey_keys = r.keys('huey:*')
    print(f"\n🎯 Huey 相关 Key ({len(huey_keys)} 个):")
    for key in huey_keys:
        key_type = r.type(key)
        ttl = r.ttl(key)
        print(f"  - {key} (type: {key_type}, TTL: {ttl}s)")
    
    # 查看队列
    queue_name = os.getenv('HUEY_QUEUE_NAME', 'pdf-tasks')
    queue_length = r.llen(queue_name)
    print(f"\n📋 队列 '{queue_name}' 长度: {queue_length}")
    
except Exception as e:
    print(f"❌ Redis 连接失败: {e}")
    import traceback
    traceback.print_exc()

# 2. 测试 Huey 配置
print("\n" + "=" * 60)
print("2. 测试 Huey 配置")
print("=" * 60)

print(f"Huey 实例: {huey}")
print(f"Huey 名称: {huey.name}")
print(f"Huey 存储类型: {type(huey.storage).__name__}")
print(f"Huey 结果存储: {huey.results}")

# 3. 测试提交任务
print("\n" + "=" * 60)
print("3. 测试提交任务")
print("=" * 60)

@huey.task()
def test_task(message):
    """测试任务"""
    print(f"测试任务执行: {message}")
    return f"完成: {message}"

try:
    # 提交任务
    result = test_task("Hello Huey!")
    print(f"✅ 任务提交成功")
    print(f"  Task ID: {result.id}")
    print(f"  Task: {result}")
    
    # 再次查看 Redis
    print(f"\n再次检查 Redis...")
    r = redis.from_url(redis_url, decode_responses=True)
    all_keys = r.keys('*')
    print(f"📊 Redis 中所有 Key ({len(all_keys)} 个):")
    for key in all_keys:
        key_type = r.type(key)
        ttl = r.ttl(key)
        print(f"  - {key} (type: {key_type}, TTL: {ttl}s)")
    
except Exception as e:
    print(f"❌ 任务提交失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
