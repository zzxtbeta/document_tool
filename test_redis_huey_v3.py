"""
测试 Redis 和 Huey 连接 - 版本 3
只提交任务，不消费
"""

import os
import redis
from huey import RedisExpireHuey
import time

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
    
except Exception as e:
    print(f"❌ Redis 连接失败: {e}")
    exit(1)

# 2. 创建 Huey 实例
print("\n" + "=" * 60)
print("2. 创建 Huey 实例（immediate=False）")
print("=" * 60)

huey = RedisExpireHuey(
    name='pdf-tasks-test',
    url=redis_url,
    immediate=False,
    results=True,
    store_none=False,
    expire_time=3600,
)
print(f"✅ Huey 实例创建成功")

# 3. 定义任务
print("\n" + "=" * 60)
print("3. 定义任务")
print("=" * 60)

@huey.task()
def test_task(message):
    """测试任务"""
    return f"完成: {message}"

print(f"✅ 任务定义成功")

# 4. 提交多个任务
print("\n" + "=" * 60)
print("4. 提交任务到 Redis 队列")
print("=" * 60)

task_ids = []
for i in range(5):
    result = test_task(f"Task {i+1}")
    task_ids.append(result.id)
    print(f"  ✅ 提交任务 {i+1}: {result.id}")

# 5. 检查 Redis 中的数据
print("\n" + "=" * 60)
print("5. 检查 Redis 中的数据")
print("=" * 60)

r = redis.from_url(redis_url, decode_responses=True)

# 查看所有 key
all_keys = r.keys('*')
print(f"\n📊 Redis 中所有 Key ({len(all_keys)} 个):")
for key in all_keys:
    key_type = r.type(key)
    ttl = r.ttl(key)
    print(f"  - {key} (type: {key_type}, TTL: {ttl}s)")

# 查看队列内容
queue_name = 'huey.redis.pdftaskstest'
queue_length = r.llen(queue_name)
print(f"\n📋 队列 '{queue_name}' 长度: {queue_length}")

if queue_length > 0:
    print(f"✅ 任务已入队到 Redis！")
    print(f"\n队列内容（前 3 个）:")
    items = r.lrange(queue_name, 0, 2)
    for i, item in enumerate(items):
        print(f"  [{i}] {item[:100]}...")
else:
    print(f"❌ 队列为空")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
