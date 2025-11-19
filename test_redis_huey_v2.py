"""
测试 Redis 和 Huey 连接 - 版本 2
直接创建 Huey 实例，不依赖环境变量
"""

import os
import redis
from huey import RedisExpireHuey

# 1. 测试 Redis 连接
print("=" * 60)
print("1. 测试 Redis 连接")
print("=" * 60)

redis_url = 'redis://:200105@172.26.18.38:6379'
print(f"Redis URL: {redis_url}")

try:
    r = redis.from_url(redis_url, decode_responses=True)
    ping_result = r.ping()
    print(f"✅ Redis 连接成功: {ping_result}")
    
    # 查看所有 key
    all_keys = r.keys('*')
    print(f"\n📊 Redis 中所有 Key ({len(all_keys)} 个):")
    if all_keys:
        for key in all_keys:
            key_type = r.type(key)
            ttl = r.ttl(key)
            print(f"  - {key} (type: {key_type}, TTL: {ttl}s)")
    else:
        print("  (空)")
    
except Exception as e:
    print(f"❌ Redis 连接失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# 2. 创建 Huey 实例（immediate=False）
print("\n" + "=" * 60)
print("2. 创建 Huey 实例（immediate=False）")
print("=" * 60)

try:
    huey = RedisExpireHuey(
        name='pdf-tasks-test',
        url=redis_url,
        immediate=False,  # 关键：必须是 False
        results=True,
        store_none=False,
        expire_time=3600,
    )
    print(f"✅ Huey 实例创建成功")
    print(f"  名称: {huey.name}")
    print(f"  存储类型: {type(huey.storage).__name__}")
    print(f"  Immediate: {huey.immediate}")
    
except Exception as e:
    print(f"❌ Huey 实例创建失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# 3. 定义并提交任务
print("\n" + "=" * 60)
print("3. 定义并提交任务")
print("=" * 60)

@huey.task()
def test_task(message):
    """测试任务"""
    return f"完成: {message}"

try:
    # 提交任务
    result = test_task("Hello Huey!")
    print(f"✅ 任务提交成功")
    print(f"  Task ID: {result.id}")
    
except Exception as e:
    print(f"❌ 任务提交失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# 4. 检查 Redis 中的数据
print("\n" + "=" * 60)
print("4. 检查 Redis 中的数据")
print("=" * 60)

try:
    r = redis.from_url(redis_url, decode_responses=True)
    
    # 查看所有 key
    all_keys = r.keys('*')
    print(f"📊 Redis 中所有 Key ({len(all_keys)} 个):")
    for key in all_keys:
        key_type = r.type(key)
        ttl = r.ttl(key)
        print(f"  - {key} (type: {key_type}, TTL: {ttl}s)")
    
    # 查看队列
    queue_name = 'pdf-tasks-test'
    queue_length = r.llen(queue_name)
    print(f"\n📋 队列 '{queue_name}' 长度: {queue_length}")
    
    if queue_length > 0:
        print(f"✅ 任务已入队到 Redis！")
    else:
        print(f"❌ 队列为空，任务没有入队")
    
except Exception as e:
    print(f"❌ 检查失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
